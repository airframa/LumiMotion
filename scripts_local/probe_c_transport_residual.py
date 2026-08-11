#
# Probe C (Test 1): per-Gaussian transport residual.
#
# What this measures. LumiMotion's traced indirect light reports each
# surfel's radiance from the frame-independent, canonical `_albedo_dc_stage1`
# SH bank (gaussian_renderer/render_ir.py:517, srgb_to_rgb(trace_outputs['color'])).
# A surfel's TRUE outgoing radiance at frame t depends on its deformed
# normal, its current self-shadowing, and the envmap. This script computes
# both quantities directly in Gaussian space and reports their gap, per
# Gaussian, per frame -- bypassing the confounds that dominated Probes B and
# D (albedo estimation error, the learned per-Gaussian shadow-modulation
# head absorbing the error during training, render-space brightness scale).
#
# A NEW standalone module, not a change to render_ir.py -- per
# docs/test1_hook_points.md's own recommendation, render_ir.py is
# pixel-space by construction; this is a sibling code path at the same level
# of abstraction as rendering_equation(), with Gaussian centers as query
# points instead of rasterized pixels. GaussianTracer, EnvLight, and
# sample_incident_rays are reused unmodified.
#
# Per frame: deform.step() for that fid -> d_xyz, d_rotation (d_scaling is
# zeroed by the network, utils/time_utils.py:192); gaussians.update_bvh()
# against the deformed geometry (build_bvh on the very first frame -- the
# tracer's update_bvh asserts the triangle topology, self.faces_b, was
# already set by a prior build_bvh call, surfel_tracer/raytracer.py:79-82);
# deformed normal from build_rotation(get_rotation_bias(d_rotation))'s third
# column, matching gaussian_model.py's trace()-internal derivation
# (gaussian_model.py:648-656); visibility from pc.trace() with rays_o at
# deformed centers offset along each individual SAMPLE direction by
# pipe.light_t_min (matching render_ir.py:482,512's exact ray-origin
# convention -- NOT a fixed offset along the normal, which is a different,
# untested construction) and rays_d from sample_incident_rays(); diffuse-only
# outgoing radiance integrated as envlight(dirs) * visibility * cos against
# albedo/pi -- no specular (w_o is undefined for an isolated surfel, and the
# effect under test is an irradiance effect, not a view-dependent one).
#
# Normal orientation: camera_center=None throughout (no view-dependent
# flip). The outward sign is resolved ONCE at canonical pose (a
# centroid-heuristic: flip any canonical normal pointing toward the
# scene's canonical centroid) and then rigidly propagated through each
# frame's deformation rotation -- the same Lagrangian propagation the
# author's own method will use. This is a real simplification for
# non-star-shaped geometry (e.g. between the legs, in an armpit) -- flagged,
# not hidden.
#
# Run from the repo root:
#   python -m scripts_local.probe_c_transport_residual --model_path ... \
#       --source_path ... --load_iter 55000 --train_light_folder ... \
#       --resolution 2 --diffuse_sample_num 512 --out_dir ...
#
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from tqdm import tqdm

from arguments import ModelParams, PipelineParams, OptimizationParams, get_combined_args
from scene import DeformModel, GaussianModel, Scene
from scene.light import EnvLight
from utils.general_utils import build_rotation, safe_normalize, safe_state
from utils.graphics_utils import srgb_to_rgb
from utils.relight_utils import sample_incident_rays
from utils.sh_utils import SH2RGB


def resolve_canonical_sign(gaussians):
    """Outward-normal heuristic at canonical pose: flip any normal pointing
    toward the scene's canonical centroid. A simplification for non-convex
    geometry -- reasonable for a roughly star-shaped standing/jumping human
    figure, not exact everywhere (e.g. armpits, between the legs)."""
    xyz = gaussians.get_xyz
    centroid = xyz.mean(dim=0, keepdim=True)
    R0 = build_rotation(gaussians.get_rotation)
    normals_raw = safe_normalize(R0[:, :, 2])
    outward = xyz - centroid
    dot = (normals_raw * outward).sum(-1)
    sign = torch.where(dot >= 0, 1.0, -1.0)
    return sign, normals_raw * sign[:, None]


def deformed_normals(rotation, canonical_sign):
    R = build_rotation(rotation)
    return safe_normalize(R[:, :, 2]) * canonical_sign[:, None]


def diffuse_outgoing_radiance(gaussians, env_light, pipe, xyz, scales, rotation, opacity,
                              normals, albedo_linear, n_samples, chunk_size):
    """Per-Gaussian diffuse exitant radiance under the (trained) envmap,
    self-shadowed by the current deformed geometry. Chunked over the
    N-Gaussian query axis; the scene-geometry args (xyz/scales/rotation/
    opacity) are always passed in full -- the tracer's BVH indexes into the
    whole cloud regardless of which subset is being queried, exactly as
    render_ir.py's pixel-space call passes the full deformed cloud for a
    masked pixel subset."""
    N = xyz.shape[0]
    out_chunks = []
    for start in range(0, N, chunk_size):
        end = min(start + chunk_size, N)
        normals_c = normals[start:end]
        xyz_c = xyz[start:end]
        albedo_c = albedo_linear[start:end]

        incident_dirs, incident_areas = sample_incident_rays(normals_c, False, n_samples)  # (n,S,3),(n,S,1)
        rays_o = xyz_c.unsqueeze(1) + incident_dirs * pipe.light_t_min
        rays_d = incident_dirs

        trace_out = gaussians.trace(rays_o, rays_d, features=None, camera_center=None,
                                    xyz=xyz, scales=scales, rotation=rotation, opacity=opacity, shs=None)
        visibility = 1 - trace_out['alpha'][..., None]  # (n,S,1)
        n_dot_i = (normals_c[:, None] * incident_dirs).sum(-1, keepdim=True).clamp(min=0)
        global_light = env_light(incident_dirs, mode='pure_env')  # (n,S,3)

        f_d = albedo_c[:, None] / np.pi
        transport = global_light * visibility * incident_areas * n_dot_i
        out_chunks.append((f_d * transport).mean(dim=-2))  # (n,3)
    return torch.cat(out_chunks, dim=0)


def evaluate_pose(gaussians, deform, env_light, pipe, N, canonical_sign, n_samples, chunk_size,
                  time_input=None):
    """One deformation + trace + integrate pass. time_input=None means the
    true canonical pose (d_xyz=d_rotation=0), bypassing the deform network
    entirely -- used only for the sanity check, kept structurally identical
    to the real-frame path otherwise."""
    if time_input is None:
        d_xyz = torch.zeros_like(gaussians.get_xyz)
        d_rotation = torch.zeros_like(gaussians._rotation)
        d_scaling = torch.zeros_like(gaussians.get_scaling)
    else:
        d_values = deform.step(gaussians.get_xyz.detach(), time_input, feature=gaussians.get_binary_feature())
        d_xyz, d_rotation, d_scaling = d_values['d_xyz'], d_values['d_rotation'], d_values['d_scaling']

    xyz = gaussians.get_xyz + d_xyz
    scales = gaussians.get_scaling + d_scaling
    rotation = gaussians.get_rotation_bias(d_rotation)
    opacity = gaussians.get_opacity

    normals = deformed_normals(rotation, canonical_sign)
    albedo_linear = srgb_to_rgb(gaussians.get_albedo)

    L_true = diffuse_outgoing_radiance(gaussians, env_light, pipe, xyz, scales, rotation, opacity,
                                       normals, albedo_linear, n_samples, chunk_size)
    return {
        "L_true": L_true, "d_xyz": d_xyz, "normals": normals,
        "d_rotation": d_rotation, "d_scaling": d_scaling,
    }


def percentiles(x):
    return {
        "mean": float(x.mean()), "median": float(np.median(x)),
        "p90": float(np.percentile(x, 90)), "p99": float(np.percentile(x, 99)),
        "max": float(x.max()),
    }


def run(dataset, pipe, opt, load_iter, out_dir, n_samples, chunk_size, subsample_n, subsample_seed):
    os.makedirs(out_dir, exist_ok=True)

    with torch.no_grad():
        deform = DeformModel(deform_type=dataset.deform_type, is_blender=dataset.is_blender,
                             hyper_dim=dataset.hyper_dim, pred_color=dataset.pred_color)
        assert deform.load_weights(dataset.model_path, iteration=load_iter), \
            f"No deform checkpoint under {dataset.model_path}/deform for iteration {load_iter}"

        gaussians = GaussianModel(dataset.sh_degree, no_binary_separation=dataset.no_binary_separation,
                                  fea_dim=dataset.hyper_dim)
        scene = Scene(dataset, gaussians, load_iteration=load_iter)

        env_light = EnvLight(path=None, device='cuda',
                             resolution=[opt.envmap_resolution // 2, opt.envmap_resolution],
                             max_res=opt.envmap_resolution, activation=opt.envmap_activation)
        env_light.load_weights(dataset.model_path, scene.loaded_iter)

        N = gaussians.get_xyz.shape[0]
        canonical_sign, canonical_normals = resolve_canonical_sign(gaussians)
        dynamic_mask = (gaussians.get_binary_feature().squeeze(-1) > 0.5)
        L_stored = srgb_to_rgb(SH2RGB(gaussians._albedo_dc_stage1.squeeze()))  # (N,3), matches
        # render_ir.py:148's SH2RGB(pc._albedo_dc_stage1[:, :1]) for the DC
        # (degree-0, direction-independent) term -- no shadow-modulation
        # multiply (that's the frame-dependent learned correction this probe
        # exists to bypass) and no _albedo_rest (that's a genuine
        # view-direction dependence the diffuse-only, viewer-free L_true
        # side of this comparison has no analogue for).

        rng = np.random.default_rng(subsample_seed)
        sub_idx = rng.choice(N, size=min(subsample_n, N), replace=False)
        sub_idx_t = torch.from_numpy(sub_idx).long()

        # ---- canonical-pose sanity check (build_bvh once, at zero deformation) ----
        d_zero = torch.zeros_like(gaussians._rotation)
        gaussians.build_bvh(d_rotation=d_zero, d_xyz=torch.zeros_like(gaussians.get_xyz),
                            d_scaling=torch.zeros_like(gaussians.get_scaling))
        canon = evaluate_pose(gaussians, deform, env_light, pipe, N, canonical_sign, n_samples, chunk_size,
                              time_input=None)
        canon_residual = (canon["L_true"] - L_stored).mean(dim=-1)  # (N,) channel-mean signed
        canon_stats_all = percentiles(canon_residual.abs().cpu().numpy())
        canon_stats_dyn = percentiles(canon_residual[dynamic_mask].abs().cpu().numpy())
        canon_signed_mean_all = float(canon_residual.mean())
        canon_signed_mean_dyn = float(canon_residual[dynamic_mask].mean())
        canonical_report = {
            "abs_residual_all": canon_stats_all, "abs_residual_dynamic": canon_stats_dyn,
            "signed_mean_all": canon_signed_mean_all, "signed_mean_dynamic": canon_signed_mean_dyn,
            "L_stored_mean_all": float(L_stored.mean().item()),
            "L_true_mean_all": float(canon["L_true"].mean().item()),
        }
        print("=== Canonical-pose sanity check ===")
        print(json.dumps(canonical_report, indent=2))

        L_true_canonical = canon["L_true"].clone()

        # ---- real 150-frame trajectory ----
        # Rebuild the BVH for frame 1 with `build_bvh` (topology is
        # unchanged from the canonical build above, but this follows the
        # same build-once-then-update sequence as scripts_local/render_trajectory.py
        # and scripts/train_stage2.py:155-159 rather than assuming the
        # canonical build suffices).
        fids = sorted(scene.all_timesteps.items(), key=lambda kv: kv[1])  # (fid_tensor, idx), fid-sorted
        built_bvh = False

        per_frame = []
        sub_residual = np.zeros((len(fids), sub_idx.shape[0]), dtype=np.float32)
        sub_rel_residual = np.zeros((len(fids), sub_idx.shape[0]), dtype=np.float32)
        sub_rotation_deg = np.zeros((len(fids), sub_idx.shape[0]), dtype=np.float32)
        sub_canonical_residual = (canon["L_true"] - L_stored).mean(dim=-1)[sub_idx_t].cpu().numpy()

        for fid, idx in tqdm(fids, desc="Probe C"):
            time_input = fid.unsqueeze(0).expand(N, -1)

            d_values = deform.step(gaussians.get_xyz.detach(), time_input, feature=gaussians.get_binary_feature())
            d_xyz, d_rotation, d_scaling = d_values['d_xyz'], d_values['d_rotation'], d_values['d_scaling']

            if not built_bvh:
                gaussians.build_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)
                built_bvh = True
            else:
                gaussians.update_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)

            frame = evaluate_pose(gaussians, deform, env_light, pipe, N, canonical_sign, n_samples, chunk_size,
                                  time_input=time_input)

            residual = (frame["L_true"] - L_stored).mean(dim=-1)  # (N,) signed, channel-mean
            residual_vs_canon = (frame["L_true"] - L_true_canonical).mean(dim=-1)
            L_stored_mag = L_stored.mean(dim=-1).clamp_min(1e-6)
            rel_residual = residual / L_stored_mag

            rot_deg = torch.rad2deg(torch.arccos((frame["normals"] * canonical_normals).sum(-1).clamp(-1, 1)))
            d_xyz_norm = d_xyz.norm(dim=-1)

            def stat_block(mask):
                r = residual[mask].abs().cpu().numpy()
                rs = residual[mask].cpu().numpy()
                rr = rel_residual[mask].abs().cpu().numpy()
                rc = residual_vs_canon[mask].cpu().numpy()
                rot = rot_deg[mask].cpu().numpy()
                dxyz = d_xyz_norm[mask].cpu().numpy()
                return {
                    "n": int(mask.sum().item()),
                    "abs_residual": percentiles(r), "signed_residual_mean": float(rs.mean()),
                    "rel_abs_residual": percentiles(rr),
                    "residual_vs_canonical_mean": float(rc.mean()),
                    "rotation_deg": percentiles(rot),
                    "d_xyz": percentiles(dxyz),
                }

            all_mask = torch.ones(N, dtype=torch.bool, device="cuda")
            rec = {
                "frame_idx": idx, "fid": float(fid.item()),
                "all": stat_block(all_mask), "dynamic": stat_block(dynamic_mask),
            }
            # per-frame correlation, full population (not just the subsample)
            r_np, rot_np = residual.cpu().numpy(), rot_deg.cpu().numpy()
            rec["corr_residual_rotation_all"] = float(np.corrcoef(r_np, rot_np)[0, 1])
            dyn_np_mask = dynamic_mask.cpu().numpy()
            if dyn_np_mask.sum() > 1:
                rec["corr_residual_rotation_dynamic"] = float(np.corrcoef(r_np[dyn_np_mask], rot_np[dyn_np_mask])[0, 1])
            else:
                rec["corr_residual_rotation_dynamic"] = float("nan")
            per_frame.append(rec)

            sub_residual[idx] = residual[sub_idx_t].cpu().numpy()
            sub_rel_residual[idx] = rel_residual[sub_idx_t].cpu().numpy()
            sub_rotation_deg[idx] = rot_deg[sub_idx_t].cpu().numpy()

    dynamic_mask_np = dynamic_mask.cpu().numpy()
    np.savez(os.path.join(out_dir, "pooled_subsample.npz"),
            residual=sub_residual, rel_residual=sub_rel_residual, rotation_deg=sub_rotation_deg,
            canonical_residual=sub_canonical_residual, sub_idx=sub_idx,
            dynamic_flag=dynamic_mask_np[sub_idx])

    summary = {
        "n_gaussians": N, "n_dynamic": int(dynamic_mask.sum().item()),
        "n_samples": n_samples, "subsample_n": int(sub_idx.shape[0]),
        "canonical": canonical_report,
        "per_frame": per_frame,
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {out_dir}")
    return summary, sub_residual, sub_rotation_deg, sub_rel_residual, dynamic_mask_np[sub_idx]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Probe C: per-Gaussian transport residual (Test 1)")
    model = ModelParams(parser)
    pipeline = PipelineParams(parser)
    opt = OptimizationParams(parser)

    parser.add_argument('--load_iter', type=int, default=-1)
    parser.add_argument("--iteration", default=-1, type=int)
    parser.add_argument("--out_dir", type=str, default=None,
                        help="Defaults to <model_path>/probe_c_transport_residual")
    parser.add_argument("--n_samples", type=int, default=512, help="Hemisphere samples per Gaussian.")
    parser.add_argument("--gaussian_chunk_size", type=int, default=20000)
    parser.add_argument("--subsample_n", type=int, default=20000,
                        help="Fixed random Gaussian subsample tracked across all frames "
                             "for the pooled per-Gaussian diagnostic.")
    parser.add_argument("--subsample_seed", type=int, default=0)
    parser.add_argument("--quiet", action="store_true")

    # Same reasoning as scripts_local/dump_lind.py and render_trajectory.py:
    # get_combined_args() always lets a present argparse default override
    # the saved cfg_args value for booleans, even when absent from the CLI.
    parser.set_defaults(is_blender=True, eval=True)

    args = get_combined_args(parser)
    print("Probe C for", args.model_path)
    safe_state(args.quiet)

    out_dir = getattr(args, "out_dir", None) or os.path.join(args.model_path, "probe_c_transport_residual")

    run(model.extract(args), pipeline.extract(args), opt.extract(args), args.load_iter, out_dir,
       args.n_samples, args.gaussian_chunk_size, args.subsample_n, args.subsample_seed)
