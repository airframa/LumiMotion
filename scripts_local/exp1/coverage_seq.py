#
# Experiment 1 / Stage 1 -- per-Gaussian view coverage under deformation.
#
# Port of the coverage statistic defined by RadioGS
# `scripts_local/phase3b/observability.py:124-169` (branch audit-notes, ff1d1c5)
# onto LumiMotion. Ported, not reimplemented -- see `docs/exp1_stage0_findings.md`
# Q1 for the definition this is checked against, and the gate in
# `scripts_local/exp1/gate_coverage.py` for the numeric cross-check.
#
# THE STATISTIC (observability.py:160-161):
#     ok = (vis > thr) & infr & face          # (N, C) boolean
#     n  = ok.sum(1)                          # integer count of cameras
#
# ARMS (docs/exp1_prereg_amendment_2.md sec 4):
#     C_rigid  d_xyz = d_rotation = 0 exactly, all N frames  (reading (a), sec 6)
#     C_seq    deformation live at each frame's own fid
#     C_single not computed separately -- it is ok_seq[:, j] for any single frame j,
#              recoverable from the dumped per-camera mask. Nothing is aggregated
#              here (brief sec 6).
#
# PARAMETERS, declared in advance (amendment sec 7). LumiMotion's own values, not
# RadioGS's, per the model-actual doctrine (observability.py:11):
#     back_culling     False    no caller in LumiMotion ever passes it;
#                               gaussian_model.py:636 default, render_ir.py:503-505
#     light_t_min      0.1      arguments/__init__.py:92   (RadioGS uses 0.05)
#     alpha_min        1/100    scene/gaussian_model.py:106 (RadioGS uses 1/255)
#     transmittance_min 0.03    scene/gaussian_model.py:104 -- implied by the above,
#                               declared here because it bounds the trace
#     thr              0.5      observability.py:157, never overridden
#     t_scale          1.0, 3.0 both arms, per observability.py:320-322
#
# BVH: build on the first frame, update_bvh on every frame thereafter, per
# `scripts/train_stage2.py:155-159` and the four correct `scripts_local/`
# precedents. NOT copied from scripts/eval_nvs_dynamic.py or
# scripts/eval_relight_dynamic.py, which build once and never update -- a stale
# frame-0 BVH would drive C_seq onto C_rigid and read as a clean falsification
# (docs/exp1_stage0_findings.md Q2, brief sec 4).
#
#   python scripts_local/exp1/coverage_seq.py \
#       --model_path /data/fmb/lumimotion/outputs_test1/chapelday_goldenbay/jumpingjacks150_v5_spec32_r2_mlp \
#       --source_path $PWD/data/d-nerf-relight-spec32/jumpingjacks150_v5_spec32 \
#       --deform_type mlp --iteration 55000
#
# NB the -m/-s shorthands are commented out in this repo
# (arguments/__init__.py:31-36); use --model_path / --source_path.
#
import os, sys, json, argparse
import numpy as np
import torch

sys.path.insert(0, os.getcwd())
from scene import Scene, GaussianModel, DeformModel
from arguments import ModelParams, PipelineParams, get_combined_args
from utils.general_utils import safe_state

THR = 0.5
BACK_CULLING = False
T_SCALES = (1.0, 3.0)


class BVHGuard:
    """Assert the BVH was refit to the geometry actually handed to trace().

    The failure this exists to catch is silent: a stale BVH still returns
    plausible alphas, because traversal runs against frame-0 bounding volumes
    while shading evaluates frame-t surfels. It cannot be caught downstream.

    An unconditional "must update every frame" assertion would fire falsely in
    the C_rigid arm, where the geometry genuinely does not change (amendment
    sec 7). So the invariant checked is the one that actually matters -- the BVH
    arguments equal the trace arguments on this frame -- not the call pattern.
    """

    def __init__(self):
        self._d = None
        self._frames_built = 0

    def record(self, d_xyz, d_rotation, d_scaling):
        self._d = (d_xyz.detach().clone(),
                   d_rotation.detach().clone(),
                   d_scaling.detach().clone())
        self._frames_built += 1

    def check(self, d_xyz, d_rotation, d_scaling):
        assert self._d is not None, "trace() before any build_bvh/update_bvh"
        for got, want, name in zip((d_xyz, d_rotation, d_scaling), self._d,
                                   ("d_xyz", "d_rotation", "d_scaling")):
            assert torch.equal(got.detach(), want), (
                f"BVH is stale in {name}: the acceleration structure was last "
                f"refit to different geometry than the one passed to trace(). "
                f"This is the eval_nvs_dynamic.py:86-88 failure mode.")


def deformed_geometry(g, d_xyz, d_rotation, d_scaling):
    """Exactly what render_ir.py:79,96-97 assembles before tracing."""
    xyz = g.get_xyz + d_xyz
    scales = g.get_scaling + d_scaling
    rotation = g.get_rotation_bias(d_rotation)          # normalize(_rotation + d)
    opacity = g.get_opacity                             # d_opacity is None (mlp)
    return xyz, scales, rotation, opacity


@torch.no_grad()
def coverage_frame(g, cam, xyz, scales, rotation, opacity,
                   light_t_min, t_scale, back_culling=BACK_CULLING):
    """(N,) vis / infr / face for one camera, per observability.py:135-153."""
    mu = xyz
    v = cam.camera_center - mu
    dist = v.norm(dim=-1, keepdim=True)
    d = v / dist.clamp_min(1e-8)

    # frustum: world -> clip via full_proj_transform, then NDC box test
    h = torch.cat([mu, torch.ones_like(mu[:, :1])], -1)
    clip = h @ cam.full_proj_transform
    w = clip[:, 3:4].clamp_min(1e-8)
    ndc = clip[:, :3] / w
    infr = (clip[:, 3] > 0) & (ndc[:, 0].abs() < 1) & (ndc[:, 1].abs() < 1)

    # front-facing. Uses the same normal the tracer itself derives, i.e.
    # get_covariance(...)[:, 2, :3] on the DEFORMED geometry
    # (gaussian_model.py:654-655), normalised. camera_center is deliberately not
    # passed to trace(), so flip_align_view does not run and the sign is the
    # raw surfel orientation -- matching observability.py:130,149.
    splat2world = g.get_covariance(xyz=mu, scales=scales, rotation=rotation)
    nrm = torch.nn.functional.normalize(splat2world[:, 2, :3], dim=-1)
    face = (nrm * d).sum(-1) > 0

    out = g.trace(mu + t_scale * light_t_min * d, d,
                  xyz=mu, scales=scales, rotation=rotation, opacity=opacity,
                  back_culling=back_culling)
    vis = 1.0 - out["alpha"]
    return vis, infr, face, nrm


@torch.no_grad()
def run_arm(g, deform, bfeat, cams, fids, light_t_min, arm, guard_report):
    """One arm over all frames. Returns per-t_scale (N,C) boolean masks.

    arm == "rigid": d_xyz = d_rotation = d_scaling = 0 exactly, every frame.
    arm == "seq":   the field evaluated at each frame's own fid.
    """
    N, C = g.get_xyz.shape[0], len(cams)
    xyz0 = g.get_xyz.detach()
    zeros3 = torch.zeros_like(xyz0)
    zeros4 = torch.zeros((N, 4), device="cuda")
    zeros2 = torch.zeros((N, 2), device="cuda")

    ok = {ts: torch.zeros(N, C, dtype=torch.bool, device="cuda") for ts in T_SCALES}
    vis_sum = torch.zeros(N, device="cuda")
    infr_sum = torch.zeros(N, dtype=torch.int32, device="cuda")
    face_sum = torch.zeros(N, dtype=torch.int32, device="cuda")
    disp = torch.zeros(C, device="cuda")

    guard = BVHGuard()
    built = False
    for j, cam in enumerate(cams):
        if arm == "rigid":
            d_xyz, d_rotation, d_scaling = zeros3, zeros4, zeros2
        else:
            t = torch.full((N, 1), float(fids[j]), device="cuda", dtype=torch.float32)
            dv = deform.step(xyz0, t, feature=bfeat)
            d_xyz, d_rotation = dv["d_xyz"], dv["d_rotation"]
            d_scaling = dv["d_scaling"]
        disp[j] = d_xyz.norm(dim=-1).median()

        # --- BVH, per scripts/train_stage2.py:155-159 -------------------------
        if not built:
            g.build_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)
            built = True
        else:
            g.update_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)
        guard.record(d_xyz, d_rotation, d_scaling)
        # ----------------------------------------------------------------------

        xyz, scales, rotation, opacity = deformed_geometry(g, d_xyz, d_rotation, d_scaling)
        guard.check(d_xyz, d_rotation, d_scaling)

        for ts in T_SCALES:
            vis, infr, face, _ = coverage_frame(g, cam, xyz, scales, rotation,
                                                opacity, light_t_min, ts)
            ok[ts][:, j] = (vis > THR) & infr & face
            if ts == 1.0:
                vis_sum += vis * infr * face
                infr_sum += infr.int()
                face_sum += face.int()
        if (j + 1) % 25 == 0 or j == C - 1:
            print(f"    [{arm}] frame {j+1}/{C}", flush=True)

    guard_report[arm] = guard._frames_built
    assert guard._frames_built == C, \
        f"{arm}: BVH refit {guard._frames_built} times for {C} frames"
    return ok, vis_sum, infr_sum, face_sum, disp


def load_train_fids(source_path, cams):
    """Train times, asserted to match the cameras Scene actually built."""
    with open(os.path.join(source_path, "transforms_train.json")) as f:
        frames = json.load(f)["frames"]
    key = lambda x: int(os.path.basename(x["file_path"]).split(".")[0].split("_")[-1])
    assert [f["file_path"] for f in sorted(frames, key=key)] == \
           [f["file_path"] for f in frames], "dataset_readers.py:164 reorders these"
    fids = np.asarray([f["time"] for f in frames], dtype=np.float64)
    assert len(cams) == len(fids), \
        f"Scene built {len(cams)} train cameras, transforms_train.json has {len(fids)}"
    got = np.asarray([float(c.fid.item()) for c in cams], dtype=np.float64)
    assert np.allclose(got, fids, atol=0, rtol=0), \
        "camera fid order does not match transforms_train.json order"
    return fids


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    model = ModelParams(parser, sentinel=True)
    pipeline = PipelineParams(parser)
    parser.add_argument("--iteration", default=55000, type=int)
    parser.add_argument("--out", default="")
    parser.add_argument("--quiet", action="store_true")
    args = get_combined_args(parser)
    safe_state(args.quiet)
    dataset, pipe = model.extract(args), pipeline.extract(args)

    assert "/projects/LumiMotion/" not in os.path.abspath(dataset.source_path), (
        f"source_path resolves into the sibling worktree: {dataset.source_path}\n"
        "Pass --source_path explicitly (amendment sec 7 / CLAUDE.md footgun).")
    assert dataset.eval is True, (
        "eval must be True; with eval=False dataset_readers.py:229-231 appends the "
        "15 test cameras into the train list, which is not the registered set.")
    assert abs(pipe.light_t_min - 0.1) < 1e-12, \
        f"light_t_min is {pipe.light_t_min}, amendment sec 7 declares 0.1"

    with torch.no_grad():
        deform = DeformModel(deform_type=dataset.deform_type,
                             is_blender=dataset.is_blender,
                             hyper_dim=dataset.hyper_dim,
                             pred_color=dataset.pred_color)
        assert deform.load_weights(dataset.model_path, iteration=args.iteration)

        g = GaussianModel(dataset.sh_degree,
                          no_binary_separation=dataset.no_binary_separation,
                          fea_dim=dataset.hyper_dim)
        scene = Scene(dataset, g, load_iteration=args.iteration, shuffle=False)
        assert abs(g.alpha_min - 1.0 / 100) < 1e-12, \
            f"alpha_min is {g.alpha_min}, amendment sec 7 declares 1/100"
        assert abs(g.gaussian_tracer.transmittance_min - 0.03) < 1e-12, \
            f"transmittance_min is {g.gaussian_tracer.transmittance_min}, declared 0.03"

        cams = scene.getTrainCameras()
        fids = load_train_fids(dataset.source_path, cams)
        N, C = g.get_xyz.shape[0], len(cams)
        bfeat = g.get_binary_feature()
        dyn = (bfeat[:, 0] > 0.5)

        print(f"[{dataset.model_path}]")
        print(f"  N={N} train_cams={C} dynamic={int(dyn.sum())} "
              f"({100.0*float(dyn.float().mean()):.2f}%)")
        print(f"  back_culling={BACK_CULLING} light_t_min={pipe.light_t_min} "
              f"alpha_min={g.alpha_min} transmittance_min="
              f"{g.gaussian_tracer.transmittance_min} thr={THR} t_scales={T_SCALES}")

        guard_report = {}
        res = {}
        for arm in ("rigid", "seq"):
            print(f"  arm: {arm}")
            res[arm] = run_arm(g, deform, bfeat, cams, fids,
                               pipe.light_t_min, arm, guard_report)

        # brief sec 4 / HANDOVER.md sec 9.7 -- assert the arms actually differ
        d_rigid, d_seq = res["rigid"][4], res["seq"][4]
        assert float(d_rigid.abs().max()) == 0.0, "C_rigid arm displaced something"
        assert float(d_seq.max()) > 0.0, "C_seq arm did not deform"
        print(f"  displacement sanity: rigid max {float(d_rigid.abs().max()):.3e}, "
              f"seq per-frame median in [{float(d_seq.min()):.4f}, "
              f"{float(d_seq.max()):.4f}]")

        out = args.out or os.path.join(
            "docs", "exp1_assets",
            f"coverage_{os.path.basename(dataset.model_path)}.npz")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        payload = dict(
            xyz_canonical=g.get_xyz.cpu().numpy(),
            opacity=g.get_opacity.cpu().numpy(),
            scaling=g.get_scaling.cpu().numpy(),
            binary_feature=bfeat[:, 0].cpu().numpy(),
            dynamic=dyn.cpu().numpy(),
            fids=fids, n_cams=C,
            params=json.dumps(dict(back_culling=BACK_CULLING,
                                   light_t_min=pipe.light_t_min,
                                   alpha_min=g.alpha_min,
                                   transmittance_min=g.gaussian_tracer.transmittance_min,
                                   thr=THR, t_scales=list(T_SCALES),
                                   iteration=args.iteration,
                                   model_path=dataset.model_path,
                                   source_path=dataset.source_path)),
        )
        for arm in ("rigid", "seq"):
            ok, vis_sum, infr_sum, face_sum, disp = res[arm]
            for ts in T_SCALES:
                tag = "" if ts == 1.0 else "_t3"
                # RAW per-camera mask, not aggregated (brief sec 6). C_single for
                # frame j is mask[:, j]; n_views is mask.sum(1).
                payload[f"ok_{arm}{tag}"] = np.packbits(
                    ok[ts].cpu().numpy(), axis=1)
                payload[f"n_views_{arm}{tag}"] = ok[ts].sum(1).cpu().numpy().astype(np.int32)
            payload[f"vis_sum_{arm}"] = vis_sum.cpu().numpy()
            payload[f"infr_sum_{arm}"] = infr_sum.cpu().numpy()
            payload[f"face_sum_{arm}"] = face_sum.cpu().numpy()
            payload[f"disp_median_per_frame_{arm}"] = disp.cpu().numpy()
        np.savez_compressed(out, **payload)
        print(f"  BVH refits per arm: {guard_report}")
        print(f"  wrote {out}")
        print("  NB masks are packbits-packed along axis 1; "
              f"unpack with np.unpackbits(a, axis=1)[:, :{C}]")
