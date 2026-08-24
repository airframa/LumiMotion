#
# Experiment 1 / Task 1 -- canonical-pose check.
#
# Required by `docs/exp1_prereg_amendment_2.md` sec 6, which fixes the C_rigid arm
# as reading (a): d_xyz = d_rotation = 0 exactly. That decision is only meaningful
# if the canonical Gaussian set is itself a plausible configuration, so this
# reports the distribution of ||d_xyz(t)|| across all 135 train times and applies
# the amendment's STOP CONDITION:
#
#   "If the canonical set is geometrically degenerate -- collapsed,
#    self-intersecting, or otherwise not a plausible pose -- stop and report."
#
# This doubles as brief sec 4's "verify the deformation deforms" check
# (HANDOVER.md sec 9.7: a mask-channel bug made "dynamic-only" a no-op across four
# probes before anyone checked).
#
# READ-ONLY with respect to the model. Writes one .npz + stdout. No training,
# no rendering, no BVH, no tracer call.
#
#   python scripts_local/exp1/canonical_pose_check.py \
#       --model_path /data/fmb/lumimotion/outputs_test1/chapelday_goldenbay/jumpingjacks150_v5_spec32_r2_mlp \
#       --source_path $PWD/data/d-nerf-relight-spec32/jumpingjacks150_v5_spec32 \
#       --iteration 55000
#
import os, sys, json, argparse
import numpy as np
import torch

sys.path.insert(0, os.getcwd())
from scene import GaussianModel, DeformModel
from arguments import ModelParams, PipelineParams, get_combined_args
from utils.general_utils import safe_state


def load_train_fids(source_path):
    """The 135 train times, in the order Scene will present them.

    dataset_readers.py:164 re-sorts frames by the trailing integer of file_path
    before assigning fid (:170-173). For these assets the JSON is already in that
    order, but that is asserted here rather than assumed -- the three arms are
    index-matched by frame position, so an ordering surprise would silently
    misalign them.
    """
    p = os.path.join(source_path, "transforms_train.json")
    with open(p) as f:
        contents = json.load(f)
    frames = contents["frames"]
    key = lambda x: int(os.path.basename(x["file_path"]).split(".")[0].split("_")[-1])
    resorted = sorted(frames, key=key)
    assert [f["file_path"] for f in resorted] == [f["file_path"] for f in frames], \
        "dataset_readers.py:164 re-sorts these frames; JSON order is NOT Scene order"
    fids = [f["time"] for f in frames]
    assert len(fids) == len(set(fids)), "duplicate train times"
    return np.asarray(fids, dtype=np.float64), [f["file_path"] for f in frames]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    model = ModelParams(parser, sentinel=True)
    pipeline = PipelineParams(parser)
    parser.add_argument("--iteration", default=55000, type=int)
    parser.add_argument("--out", default="")
    parser.add_argument("--quiet", action="store_true")
    args = get_combined_args(parser)
    safe_state(args.quiet)
    dataset = model.extract(args)

    # sec 7 of the amendment: cfg_args records source_path in the SIBLING worktree.
    # Refuse to run rather than silently read through it.
    # get_combined_args:181-183 merges only non-None cmdline values over cfg_args.
    # ModelParams is built with sentinel=True here, so anything NOT passed on the
    # command line comes from cfg_args -- the correct merge. The released eval
    # scripts use ModelParams(parser) WITHOUT sentinel, which makes every argparse
    # default silently override cfg_args; that is why they must pass
    # --eval --is_blender --resolution on the command line. Do not copy that.
    print(f"  resolved config: eval={dataset.eval} is_blender={dataset.is_blender} "
          f"hyper_dim={dataset.hyper_dim} pred_color={dataset.pred_color} "
          f"no_binary_separation={dataset.no_binary_separation} "
          f"sh_degree={dataset.sh_degree} deform_type={dataset.deform_type}")
    assert dataset.eval is True, (
        "eval must be True so Scene yields the 135 train cameras separately; "
        "with eval=False dataset_readers.py:229-231 appends the 15 test cameras "
        "into the train list (150), which is NOT the registered camera set.")
    assert dataset.hyper_dim == 1 and dataset.no_binary_separation is False, \
        "binary-feature wiring differs from the trained models"

    assert "/projects/LumiMotion/" not in os.path.abspath(dataset.source_path), (
        f"source_path resolves into the sibling worktree: {dataset.source_path}\n"
        "Pass --source_path explicitly. NB the -m/-s shorthands are commented out\n"
        "in this repo (arguments/__init__.py:31-36); use the long forms.\n"
        "(amendment sec 7 / CLAUDE.md footgun).")

    with torch.no_grad():
        deform = DeformModel(deform_type=dataset.deform_type,
                             is_blender=dataset.is_blender,
                             hyper_dim=dataset.hyper_dim,
                             pred_color=dataset.pred_color)
        ok = deform.load_weights(dataset.model_path, iteration=args.iteration)
        assert ok, f"no deform weights at iteration {args.iteration}"

        g = GaussianModel(dataset.sh_degree,
                          no_binary_separation=dataset.no_binary_separation,
                          fea_dim=dataset.hyper_dim)
        g.load_ply(os.path.join(dataset.model_path, "point_cloud",
                                f"iteration_{args.iteration}", "point_cloud.ply"))

        xyz0 = g.get_xyz.detach()                       # canonical positions, (N,3)
        N = xyz0.shape[0]
        bfeat = g.get_binary_feature()                  # (N,1), sigmoid(2*feature)
        dyn = (bfeat[:, 0] > 0.5)
        n_dyn = int(dyn.sum())

        fids, fpaths = load_train_fids(dataset.source_path)
        T = len(fids)

        print(f"[{dataset.model_path}]")
        print(f"  N = {N}   dynamic (binary_feature > 0.5) = {n_dyn} "
              f"({100.0*n_dyn/N:.2f}%)   train times = {T}")
        print(f"  source_path = {dataset.source_path}")

        # ---- scale references, so displacements can be read as a fraction of the subject
        bb0 = (xyz0.max(0).values - xyz0.min(0).values)
        diag0 = float(bb0.norm())
        print(f"  canonical bbox extent = {bb0.tolist()}  diagonal = {diag0:.4f}")

        # ---- evaluate the field at every train time
        norms = torch.zeros(N, T, device="cuda")
        rot_norms = torch.zeros(N, T, device="cuda")
        possum = torch.zeros(N, 3, device="cuda", dtype=torch.float64)
        bbox_ext = np.zeros((T, 3))
        for j, fid in enumerate(fids):
            t = torch.full((N, 1), float(fid), device="cuda", dtype=torch.float32)
            dv = deform.step(xyz0, t, feature=bfeat)
            d_xyz, d_rot = dv["d_xyz"], dv["d_rotation"]
            norms[:, j] = d_xyz.norm(dim=-1)
            rot_norms[:, j] = d_rot.norm(dim=-1)
            xt = xyz0 + d_xyz
            possum += xt.double()
            bbox_ext[j] = (xt.max(0).values - xt.min(0).values).cpu().numpy()
            assert dv["d_scaling"].abs().max() == 0, "d_scaling is expected to be identically 0"

        # ---- brief sec 4: does the deformation actually deform?
        alln = norms.reshape(-1)
        dynn = norms[dyn].reshape(-1)
        statn = norms[~dyn].reshape(-1)
        # torch.quantile refuses inputs above ~16M elements and N*T = 19.76M here,
        # so quantiles are taken by sorting. Same value, no subsampling.
        def q(x, p):
            if x.numel() == 0:
                return float("nan")
            xs = x.reshape(-1).float().sort().values
            i = min(int(round(p * (xs.numel() - 1))), xs.numel() - 1)
            return float(xs[i])

        def q_dim0(x, p):
            """Column-wise quantile of an (N,T) tensor, by sorting along dim 0."""
            xs = x.float().sort(dim=0).values
            i = min(int(round(p * (xs.shape[0] - 1))), xs.shape[0] - 1)
            return xs[i]

        def line(tag, x):
            print(f"    {tag:<28} median {q(x,0.5):.6f}   p90 {q(x,0.9):.6f}   "
                  f"p99 {q(x,0.99):.6f}   max {float(x.max()):.6f}")

        print("\n  ||d_xyz(t)|| over all N x T pairs (world units):")
        line("all Gaussians", alln)
        line("dynamic (bf > 0.5)", dynn)
        line("static  (bf <= 0.5)", statn)
        # "Verify the restriction restricts" (HANDOVER.md sec 9.7). d_xyz is
        # raw_d_xyz * binary_feature, so the gate is MULTIPLICATIVE, not boolean: a
        # Gaussian at binary_feature = 0.4 is "static" under thr 0.5 yet still
        # receives 40% of the displacement. Quantify that leak rather than assert
        # it away.
        stat_moved = (norms[~dyn].max(1).values > 1e-6)
        n_stat = int((~dyn).sum())
        print(f"    static set: {int(stat_moved.sum())}/{n_stat} "
              f"({100.0*float(stat_moved.float().mean()):.4f}%) move at all "
              f"(max over t > 1e-6); max displacement {float(statn.max()):.3e}")
        if int(stat_moved.sum()):
            bf_moved = bfeat[:, 0][~dyn][stat_moved]
            print(f"      their binary_feature: min {float(bf_moved.min()):.2e} "
                  f"median {float(bf_moved.median()):.2e} max {float(bf_moved.max()):.4f}")
            big = (norms[~dyn].max(1).values > 0.01)
            print(f"      static Gaussians moving > 0.01 world units: {int(big.sum())} "
                  f"({100.0*float(big.float().mean()):.4f}% of static)")
        print(f"\n  as a fraction of the canonical bbox diagonal ({diag0:.4f}):")
        print(f"    dynamic median {q(dynn,0.5)/diag0*100:.3f}%   "
              f"p90 {q(dynn,0.9)/diag0*100:.3f}%   p99 {q(dynn,0.99)/diag0*100:.3f}%")

        print("\n  ||d_rotation(t)|| (raw quaternion delta, pre-normalisation):")
        line("dynamic", rot_norms[dyn].reshape(-1))

        # ---- per-time medians
        med_t_all = q_dim0(norms, 0.5).cpu().numpy()
        med_t_dyn = q_dim0(norms[dyn], 0.5).cpu().numpy()
        mean_t_dyn = norms[dyn].mean(0).cpu().numpy()
        print(f"\n  per-time median ||d_xyz|| over the DYNAMIC set, {T} times:")
        print(f"    min {med_t_dyn.min():.6f} (t={fids[med_t_dyn.argmin()]:.6f}, "
              f"{fpaths[int(med_t_dyn.argmin())]})")
        print(f"    max {med_t_dyn.max():.6f} (t={fids[med_t_dyn.argmax()]:.6f}, "
              f"{fpaths[int(med_t_dyn.argmax())]})")
        print(f"    mean over times {med_t_dyn.mean():.6f}   "
              f"ratio max/min {med_t_dyn.max()/max(med_t_dyn.min(),1e-12):.2f}")

        # ---- STOP CONDITION 1: collapse
        ext_ratio = bbox_ext / bb0.cpu().numpy()[None, :]
        print(f"\n  collapse check -- deformed bbox extent / canonical bbox extent:")
        print(f"    min over times and axes {ext_ratio.min():.4f}   "
              f"max {ext_ratio.max():.4f}")

        # nearest-neighbour spacing, on a fixed random subsample (collapse detector)
        gen = torch.Generator(device="cuda").manual_seed(0)
        sub = torch.randperm(N, generator=gen, device="cuda")[:4096]
        def nn_med(P):
            D = torch.cdist(P[sub], P[sub])
            D.fill_diagonal_(float("inf"))
            return float(D.min(1).values.median())
        nn0 = nn_med(xyz0)
        t_mid = float(fids[T // 2])
        dv_mid = deform.step(xyz0, torch.full((N,1), t_mid, device="cuda"), feature=bfeat)
        nn_mid = nn_med(xyz0 + dv_mid["d_xyz"])
        print(f"    median NN spacing (4096-pt subsample, seed 0): "
              f"canonical {nn0:.6f}   deformed t={t_mid:.4f} {nn_mid:.6f}   "
              f"ratio {nn0/max(nn_mid,1e-12):.4f}")

        # ---- STOP CONDITION 2: is canonical a pose the sequence contains,
        #      or an extrapolation outside the observed trajectory?
        xbar = (possum / T).float()                        # temporal mean position
        traj_r = torch.zeros(N, device="cuda")
        for j, fid in enumerate(fids):
            t = torch.full((N, 1), float(fid), device="cuda", dtype=torch.float32)
            xt = xyz0 + deform.step(xyz0, t, feature=bfeat)["d_xyz"]
            traj_r = torch.maximum(traj_r, (xt - xbar).norm(dim=-1))
        d_canon = (xyz0 - xbar).norm(dim=-1)
        ratio = d_canon[dyn] / traj_r[dyn].clamp_min(1e-9)
        print(f"\n  is canonical inside the observed trajectory? (dynamic set)")
        print(f"    ||x_canonical - mean_t x(t)|| / max_t ||x(t) - mean_t x(t)||")
        print(f"    median {q(ratio,0.5):.4f}   p90 {q(ratio,0.9):.4f}   "
              f"p99 {q(ratio,0.99):.4f}   max {float(ratio.max()):.4f}")
        print(f"    fraction with ratio > 1 (canonical outside trajectory hull): "
              f"{float((ratio > 1).float().mean())*100:.2f}%")

        # closest actual frame to the canonical pose
        closest = int(med_t_dyn.argmin())
        print(f"    closest observed frame to canonical: index {closest} "
              f"(t={fids[closest]:.6f}), median displacement {med_t_dyn[closest]:.6f} "
              f"= {med_t_dyn[closest]/diag0*100:.3f}% of bbox diagonal")

        out = args.out or os.path.join(
            "docs", "exp1_assets",
            f"canonpose_{os.path.basename(dataset.model_path)}.npz")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        np.savez_compressed(
            out,
            fids=fids, N=N, dynamic=dyn.cpu().numpy(),
            binary_feature=bfeat[:, 0].cpu().numpy(),
            dnorm_median_per_time_all=med_t_all,
            dnorm_median_per_time_dyn=med_t_dyn,
            dnorm_mean_per_time_dyn=mean_t_dyn,
            dnorm_per_gauss_median=q_dim0(norms.t().contiguous(), 0.5).cpu().numpy(),
            dnorm_per_gauss_max=norms.max(1).values.cpu().numpy(),
            bbox_extent_per_time=bbox_ext,
            bbox_extent_canonical=bb0.cpu().numpy(),
            canon_offset_ratio=(d_canon / traj_r.clamp_min(1e-9)).cpu().numpy(),
            nn_canonical=nn0, nn_deformed_mid=nn_mid,
        )
        print(f"\n  wrote {out}")
