#
# Probe D (Test 1): test whether LumiMotion's render exhibits a signed,
# spatially-localized, deformation-correlated brightness bias in regions
# receiving indirect illumination -- the signature predicted by the
# frozen-radiance hypothesis (see CLAUDE.md / docs/test1_hook_points.md):
# a surfel that has deformed into shadow still bleeds its stale, too-bright
# canonical radiance onto its neighbours via _albedo_dc_stage1.
#
# Consumes the per-frame dumps from scripts_local/render_trajectory.py
# (render, linear L_ind, linear albedo, alpha mask, per-Gaussian d_xyz) and
# scripts_local/dump_lind.py's frame_stats.csv (deformation magnitude).
# Produces PNG plots + a JSON summary per scene; does not write the final
# docs/test1_probe_d.md itself (that's assembled by hand from these numbers,
# per the project's "read before writing" / no-auto-generated-docs practice).
#
# Read-only with respect to the trained models -- pure post-hoc analysis of
# already-rendered pixels, no GPU/model code touched here.
#
# --relative_error / --dynamic_mask_dir (added for the novel-illumination
# rerun, docs/test1_probe_d_relight.md): additive, default-off fixes to the
# original Probe D methodology (docs/test1_probe_d.md's Limitations #3 and
# the qualitative panels showing the background floor pattern/checkerboard
# prop dominating the signal instead of the body). Both default to the
# original absolute-error, full-foreground-mask behaviour when omitted, so
# the original run remains exactly reproducible with the same flags used
# before.
#
# --relative_eps_k (added for docs/test1_probe_d_relight.md's "Brightness
# confound" section): a *fixed* --relative_eps reweights pixels differently
# between a bright and a dark lighting condition, contaminating exactly the
# training-vs-test-light comparison this probe exists to make. When set,
# epsilon is instead k * mean(GT_foreground_linear) for that frame, so the
# relative-error metric is scale-invariant across lighting conditions.
# Additive/default-off: omitting it reproduces the fixed-epsilon behaviour
# exactly.
#
import argparse
import csv
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
from scipy import ndimage
from torchvision.io import read_image

from utils.graphics_utils import srgb_to_rgb

SPLITS = ("train", "test")


def load_gt_rgb(folder, frame_num, target_hw):
    path = os.path.join(folder, f"r_{frame_num:04d}.png")
    img = read_image(path).float()[:3]
    img = F.interpolate(img.unsqueeze(0), size=target_hw, mode='bilinear', align_corners=False).squeeze(0)
    return srgb_to_rgb(img / 255.0)  # (3,H,W) linear


def load_gt_albedo(albedo_folder, frame_num, target_hw):
    # dynamic-scene albedo GT is named r_{cam}{cam}.png (camera index and
    # geometry-timestep index are the same for the dynamic variant --
    # docs/lumimotion_eval.md Part D).
    path = os.path.join(albedo_folder, f"r_{frame_num:04d}{frame_num:04d}.png")
    img = read_image(path).float()[:3]
    img = F.interpolate(img.unsqueeze(0), size=target_hw, mode='bilinear', align_corners=False).squeeze(0)
    return srgb_to_rgb(img / 255.0)  # (3,H,W) linear


def load_dynamic_mask(dynamic_mask_dir, frame_num, target_hw, channel="rgb"):
    """dynamic_mask/mask_XXXX.png -> (H,W) bool "this pixel shows a DYNAMIC
    (armature-driven) surface".

    Channel semantics, established by reading the generation script itself
    (docs/blend_files_survey.md 1c) and confirmed empirically
    (docs/indirect_fraction.md, "Correction" section):
      * RGB   -- the actual dynamic/static segmentation. The generator assigns
                 a pure-white emission material to meshes carrying an Armature
                 modifier targeting "Armature" (the moving character) and
                 pure-black to everything else (the static floor/props).
                 R==G==B exactly; effectively binary.
      * Alpha -- ordinary render alpha of ANY opaque object in frame. Both
                 character and floor are opaque, so this is just the
                 whole-scene foreground silhouette (measured IoU 0.999 against
                 the beauty render's own alpha) and carries NO dynamic/static
                 information at all.

    `channel="rgb"` is correct and the default. `channel="alpha"` reproduces
    the original (buggy) behaviour so that pre-fix numbers in
    docs/test1_probe_d*.md and docs/indirect_fraction.md stay reproducible.
    """
    if channel not in ("rgb", "alpha"):
        raise ValueError(f"channel must be 'rgb' or 'alpha', got {channel!r}")
    path = os.path.join(dynamic_mask_dir, f"mask_{frame_num:04d}.png")
    img = read_image(path).float()
    sel = img[:3].mean(dim=0, keepdim=True) if channel == "rgb" else img[3:4]
    sel = F.interpolate(sel.unsqueeze(0), size=target_hw, mode='bilinear', align_corners=False).squeeze(0)
    return (sel[0] > 127)  # (H,W) bool


def relative_error_scalar(render_linear, gt_linear, relative, eps):
    """Channel-mean signed error, either absolute (render-GT) or relative
    ((render-GT)/(GT+eps)) -- the hypothesis is a multiplicative brightness
    bias, so relative error is what docs/test1_probe_d_relight.md uses;
    absolute is kept as the default to exactly reproduce docs/test1_probe_d.md."""
    diff = render_linear - gt_linear
    if relative:
        diff = diff / (gt_linear + eps)
    return diff.mean(dim=0)


def compute_eps(gt_linear, mask, relative_eps, relative_eps_k):
    """Fixed epsilon by default; if relative_eps_k is given, epsilon scales
    with this frame's own foreground GT brightness (channel- and
    pixel-mean over `mask`) instead -- see the module docstring."""
    if relative_eps_k is not None:
        return relative_eps_k * gt_linear.mean(dim=0)[mask].mean().item()
    return relative_eps


def erode_mask(mask_bool, px):
    if px <= 0:
        return mask_bool
    m = mask_bool.numpy()
    structure = np.ones((2 * px + 1, 2 * px + 1), dtype=bool)
    return torch.from_numpy(ndimage.binary_erosion(m, structure=structure))


def load_frame_stats(csv_path):
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    by_fid = {}
    for r in rows:
        by_fid[round(float(r["fid"]), 6)] = {
            "mean_d_xyz": float(r["mean_d_xyz"]),
            "max_d_xyz": float(r["max_d_xyz"]),
            "mean_normal_angle_deg": float(r["mean_normal_angle_deg"]),
        }
    return by_fid


def decile_bin(residual_list, predictor_list, n_bins=10):
    residual = np.concatenate(residual_list)
    predictor = np.concatenate(predictor_list)
    order = np.argsort(predictor)
    residual, predictor = residual[order], predictor[order]
    edges = np.linspace(0, len(predictor), n_bins + 1).astype(int)
    px, py, pse = [], [], []
    for i in range(n_bins):
        seg, pseg = residual[edges[i]:edges[i + 1]], predictor[edges[i]:edges[i + 1]]
        if len(seg) == 0:
            px.append(np.nan); py.append(np.nan); pse.append(np.nan)
            continue
        px.append(pseg.mean())
        py.append(seg.mean())
        pse.append(seg.std() / max(np.sqrt(len(seg)), 1))
    return np.array(px), np.array(py), np.array(pse)


def find_near_identical_pairs(frame_num_list, dxyz_subsampled, min_gap, top_k):
    """Nearest-in-pose-space frame pairs (by mean per-Gaussian |d_xyz|
    difference on a fixed random subsample of Gaussians), restricted to
    pairs at least `min_gap` frames apart so periodicity, not adjacency, is
    what's being found."""
    X = np.stack(dxyz_subsampled, axis=0)  # (n_frames, n_sub*3)
    n = X.shape[0]
    best = []
    for i in range(n):
        for j in range(i + 1, n):
            if abs(frame_num_list[i] - frame_num_list[j]) < min_gap:
                continue
            dist = float(np.sqrt(((X[i] - X[j]) ** 2).mean()))
            best.append((dist, frame_num_list[i], frame_num_list[j]))
    best.sort(key=lambda t: t[0])
    return best[:top_k]


def save_qualitative_panel(data_dir, gt_color_folder, gt_albedo_folder, frame_num,
                           erosion_px, out_path, scene_label, tag,
                           relative_error=False, relative_eps=0.01, dynamic_mask_dir=None,
                           relative_eps_k=None, dynamic_mask_channel="rgb"):
    """Beauty render | GT | L_ind (visualised) | signed residual heatmap for
    one specific frame, so the numeric correlations can be checked against
    an actual image rather than taken on faith."""
    d = torch.load(os.path.join(data_dir, f"frame_{frame_num:04d}.pt"))
    render_srgb, lind_linear = d["render_srgb"], d["lind_linear"]
    alpha_mask = d["alpha_mask"]
    H, W = render_srgb.shape[-2:]

    mask = erode_mask(alpha_mask, erosion_px)
    if dynamic_mask_dir is not None:
        mask = mask & load_dynamic_mask(dynamic_mask_dir, frame_num, (H, W), channel=dynamic_mask_channel)
    gt_rgb_linear = load_gt_rgb(gt_color_folder, frame_num, (H, W))
    render_linear = srgb_to_rgb(render_srgb)
    color_eps = compute_eps(gt_rgb_linear, mask, relative_eps, relative_eps_k)
    err_scalar = relative_error_scalar(render_linear, gt_rgb_linear, relative_error, color_eps)
    offset = err_scalar[mask].mean().item()
    residual = (err_scalar - offset) * mask

    render_np = render_srgb.permute(1, 2, 0).clamp(0, 1).numpy()
    gt_np = torch.clamp(torch.pow(gt_rgb_linear.clamp_min(0), 1 / 2.4) * 1.055 - 0.055, 0, 1).permute(1, 2, 0).numpy()
    lind_vis = (lind_linear.clamp_min(0) ** (1 / 2.2)).clamp(0, 1).numpy()  # rough display gamma
    residual_np = residual.numpy()
    vmax = max(abs(np.percentile(residual_np[mask.numpy()], 1)), abs(np.percentile(residual_np[mask.numpy()], 99)), 1e-6)

    fig, axes = plt.subplots(1, 4, figsize=(18, 4.5))
    axes[0].imshow(render_np); axes[0].set_title("render (sRGB)")
    axes[1].imshow(gt_np); axes[1].set_title("GT (sRGB)")
    axes[2].imshow(lind_vis); axes[2].set_title("L_ind (linear, display gamma)")
    im = axes[3].imshow(residual_np, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    axes[3].set_title("offset-removed signed residual\n(red = render too bright)")
    for ax in axes:
        ax.axis("off")
    fig.colorbar(im, ax=axes[3], fraction=0.046, pad=0.04)
    fig.suptitle(f"{scene_label} frame {frame_num} ({tag})")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def analyse_scene(traj_dir, source_path, train_light_folder, frame_stats_csv,
                  erosion_px, out_dir, scene_label, pose_subsample=4000, pose_seed=0,
                  relative_error=False, relative_eps=0.01, dynamic_mask_dir=None,
                  relative_eps_k=None, dynamic_mask_channel="rgb"):
    os.makedirs(out_dir, exist_ok=True)
    data_dir = os.path.join(traj_dir, "frame_data")
    frame_files = sorted(glob.glob(os.path.join(data_dir, "frame_*.pt")))
    assert frame_files, f"No frame_*.pt under {data_dir} -- did render_trajectory.py run?"

    gt_color_folder = os.path.join(source_path, train_light_folder)
    gt_albedo_folder = os.path.join(source_path, "albedo")
    stats_by_fid = load_frame_stats(frame_stats_csv)
    error_kind = "relative" if relative_error else "absolute"

    per_frame = []
    pooled = {s: {"residual": [], "lind": [], "albedo_err": []} for s in SPLITS}

    rng = np.random.default_rng(pose_seed)
    sub_idx = None
    frame_nums_for_pose = []
    dxyz_subsampled = []

    for fpath in frame_files:
        d = torch.load(fpath)
        frame_num, split, fid = d["frame_num"], d["split"], round(d["fid"], 6)

        render_srgb = d["render_srgb"]
        lind_linear = d["lind_linear"]
        base_color_linear = d["base_color_linear"]
        alpha_mask = d["alpha_mask"]
        H, W = render_srgb.shape[-2:]

        mask = erode_mask(alpha_mask, erosion_px)
        if dynamic_mask_dir is not None:
            mask = mask & load_dynamic_mask(dynamic_mask_dir, frame_num, (H, W),
                                            channel=dynamic_mask_channel)
        if mask.sum().item() < 100:
            print(f"  [skip] frame {frame_num}: <100 foreground px after erosion"
                  f"{' + dynamic-mask' if dynamic_mask_dir else ''}")
            continue

        gt_rgb_linear = load_gt_rgb(gt_color_folder, frame_num, (H, W))
        render_linear = srgb_to_rgb(render_srgb)
        color_eps = compute_eps(gt_rgb_linear, mask, relative_eps, relative_eps_k)
        err_scalar = relative_error_scalar(render_linear, gt_rgb_linear, relative_error, color_eps)

        err_masked = err_scalar[mask]
        offset = err_masked.mean().item()
        residual_masked = err_masked - offset

        lind_masked = lind_linear.mean(dim=-1)[mask]

        gt_albedo_linear = load_gt_albedo(gt_albedo_folder, frame_num, (H, W))
        albedo_eps = compute_eps(gt_albedo_linear, mask, relative_eps, relative_eps_k)
        albedo_err_scalar = relative_error_scalar(base_color_linear, gt_albedo_linear, relative_error, albedo_eps)
        albedo_err_masked = albedo_err_scalar[mask]

        residual_np = residual_masked.numpy()
        lind_np = lind_masked.numpy()
        albedo_err_np = albedo_err_masked.numpy()

        def safe_corr(a, b):
            if a.std() == 0 or b.std() == 0:
                return float("nan")
            return float(np.corrcoef(a, b)[0, 1])

        r_lind = safe_corr(residual_np, lind_np)
        r_albedo = safe_corr(residual_np, albedo_err_np)

        # per-frame 5-bin residual-vs-Lind curve, used only for the
        # periodicity control (fewer bins than the pooled 10-bin plots
        # since a single frame has far fewer pixels).
        _, own_bins_y, _ = decile_bin([residual_np], [lind_np], n_bins=5)

        stat = stats_by_fid.get(fid, {})
        per_frame.append({
            "frame_num": frame_num, "split": split, "fid": fid,
            "n_px": int(mask.sum().item()), "offset": offset,
            "mean_abs_residual": float(np.abs(residual_np).mean()),
            "color_eps": color_eps, "albedo_eps": albedo_eps,
            "r_lind": r_lind, "r_albedo": r_albedo,
            "own_decile5_residual": own_bins_y.tolist(),
            "mean_d_xyz": stat.get("mean_d_xyz"),
            "max_d_xyz": stat.get("max_d_xyz"),
            "mean_normal_angle_deg": stat.get("mean_normal_angle_deg"),
        })
        pooled[split]["residual"].append(residual_np)
        pooled[split]["lind"].append(lind_np)
        pooled[split]["albedo_err"].append(albedo_err_np)

        d_xyz = d["d_xyz"].float().numpy()
        if sub_idx is None:
            sub_idx = rng.choice(d_xyz.shape[0], size=min(pose_subsample, d_xyz.shape[0]), replace=False)
        frame_nums_for_pose.append(frame_num)
        dxyz_subsampled.append(d_xyz[sub_idx].reshape(-1))

    # ---- decile binning, pooled per split ----
    decile_results = {}
    for split in SPLITS:
        if not pooled[split]["residual"]:
            continue
        lx, ly, lse = decile_bin(pooled[split]["residual"], pooled[split]["lind"])
        ax_, ay, ase = decile_bin(pooled[split]["residual"], pooled[split]["albedo_err"])
        decile_results[split] = {
            "lind_decile_x": lx.tolist(), "lind_decile_y": ly.tolist(), "lind_decile_sem": lse.tolist(),
            "albedo_decile_x": ax_.tolist(), "albedo_decile_y": ay.tolist(), "albedo_decile_sem": ase.tolist(),
            "n_pixels_pooled": int(sum(len(r) for r in pooled[split]["residual"])),
        }

    # ---- plots ----
    fig, ax = plt.subplots(figsize=(7, 5))
    for split, marker in [("train", "o"), ("test", "^")]:
        xs = [r["mean_d_xyz"] for r in per_frame if r["split"] == split and r["mean_d_xyz"] is not None]
        ys = [r["r_lind"] for r in per_frame if r["split"] == split and r["mean_d_xyz"] is not None]
        ax.scatter(xs, ys, marker=marker, label=split, alpha=0.7)
    ax.axhline(0, color='gray', lw=0.8)
    ax.set_xlabel("mean |d_xyz| (deformation magnitude, this frame)")
    ax.set_ylabel("Pearson r(offset-removed residual, L_ind)")
    ax.set_title(f"{scene_label}: residual-vs-L_ind correlation vs. deformation magnitude")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "r_lind_vs_deformation.png"), dpi=140)
    plt.close(fig)

    for split in decile_results:
        dr = decile_results[split]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
        axes[0].errorbar(range(10), dr["lind_decile_y"], yerr=dr["lind_decile_sem"], marker='o')
        axes[0].axhline(0, color='gray', lw=0.8)
        axes[0].set_xlabel("L_ind decile (0=lowest)")
        axes[0].set_ylabel("mean signed residual (offset removed)")
        axes[0].set_title(f"[{split}] residual vs. L_ind decile")

        axes[1].errorbar(range(10), dr["albedo_decile_y"], yerr=dr["albedo_decile_sem"], marker='o', color='tab:orange')
        axes[1].axhline(0, color='gray', lw=0.8)
        axes[1].set_xlabel("albedo-error decile (0=lowest)")
        axes[1].set_title(f"[{split}] residual vs. albedo-error decile (confound check)")
        fig.suptitle(scene_label)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, f"decile_{split}.png"), dpi=140)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    for split, marker in [("train", "o"), ("test", "^")]:
        xs = [r["frame_num"] for r in per_frame if r["split"] == split]
        ys = [r["offset"] for r in per_frame if r["split"] == split]
        ax.scatter(xs, ys, marker=marker, label=split, alpha=0.7, s=14)
    ax.axhline(0, color='gray', lw=0.8)
    ax.set_xlabel("frame number")
    ax.set_ylabel(f"global mean {error_kind} error (render vs. GT), linear")
    ax.set_title(f"{scene_label}: global per-frame brightness offset ({error_kind} error)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "global_offset_per_frame.png"), dpi=140)
    plt.close(fig)

    # ---- qualitative panels: best-case-for-the-hypothesis frame (max
    # r_lind) and the median-r_lind frame (typical case), so the numeric
    # correlations can be checked against actual images. ----
    ranked = sorted([r for r in per_frame if not np.isnan(r["r_lind"])], key=lambda r: r["r_lind"])
    if ranked:
        best = ranked[-1]
        median = ranked[len(ranked) // 2]
        save_qualitative_panel(data_dir, gt_color_folder, gt_albedo_folder, best["frame_num"],
                               erosion_px, os.path.join(out_dir, "qualitative_best_case.png"),
                               scene_label, f"max r_lind={best['r_lind']:.3f}",
                               relative_error=relative_error, relative_eps=relative_eps,
                               dynamic_mask_dir=dynamic_mask_dir, relative_eps_k=relative_eps_k,
                               dynamic_mask_channel=dynamic_mask_channel)
        save_qualitative_panel(data_dir, gt_color_folder, gt_albedo_folder, median["frame_num"],
                               erosion_px, os.path.join(out_dir, "qualitative_median_case.png"),
                               scene_label, f"median r_lind={median['r_lind']:.3f}",
                               relative_error=relative_error, relative_eps=relative_eps,
                               dynamic_mask_dir=dynamic_mask_dir, relative_eps_k=relative_eps_k,
                               dynamic_mask_channel=dynamic_mask_channel)

    # ---- control (a): minimum-deformation frames vs. the rest ----
    valid = [r for r in per_frame if r["mean_d_xyz"] is not None]
    valid_sorted = sorted(valid, key=lambda r: r["mean_d_xyz"])
    n_low = max(1, len(valid_sorted) // 10)
    low_def, high_def = valid_sorted[:n_low], valid_sorted[-n_low:]
    control_a = {
        "n_low_deformation_frames": n_low,
        "low_deformation_frame_nums": [r["frame_num"] for r in low_def],
        "low_deformation_mean_abs_residual": float(np.mean([r["mean_abs_residual"] for r in low_def])),
        "low_deformation_mean_r_lind": float(np.nanmean([r["r_lind"] for r in low_def])),
        "high_deformation_frame_nums": [r["frame_num"] for r in high_def],
        "high_deformation_mean_abs_residual": float(np.mean([r["mean_abs_residual"] for r in high_def])),
        "high_deformation_mean_r_lind": float(np.nanmean([r["r_lind"] for r in high_def])),
    }

    # ---- control (b): near-identical-pose frame pairs (periodicity) ----
    # NOTE: this is a real-trajectory render, so each frame also has its own
    # camera pose -- two frames with near-identical body pose are generally
    # viewed from very different angles. Pixel-registered error-map
    # comparison isn't meaningful here; "agreement" is compared at the
    # summary-statistic level (offset, r_lind, the 5-bin residual-vs-L_ind
    # curve), not pixel-by-pixel.
    pairs = find_near_identical_pairs(frame_nums_for_pose, dxyz_subsampled, min_gap=15, top_k=3)
    by_frame_num = {r["frame_num"]: r for r in per_frame}
    control_b = []
    for dist, fa, fb in pairs:
        ra, rb = by_frame_num.get(fa), by_frame_num.get(fb)
        if ra is None or rb is None:
            continue
        curve_a, curve_b = np.array(ra["own_decile5_residual"]), np.array(rb["own_decile5_residual"])
        curve_corr = float(np.corrcoef(curve_a, curve_b)[0, 1]) if curve_a.std() > 0 and curve_b.std() > 0 else float("nan")
        control_b.append({
            "frame_a": fa, "frame_b": fb, "pose_distance": dist,
            "offset_a": ra["offset"], "offset_b": rb["offset"],
            "r_lind_a": ra["r_lind"], "r_lind_b": rb["r_lind"],
            "residual_curve_a": ra["own_decile5_residual"], "residual_curve_b": rb["own_decile5_residual"],
            "residual_curve_correlation": curve_corr,
        })

    summary = {
        "scene": scene_label, "n_frames_analysed": len(per_frame), "erosion_px": erosion_px,
        "error_kind": error_kind, "relative_eps": relative_eps if relative_error else None,
        "relative_eps_k": relative_eps_k, "dynamic_mask_dir": dynamic_mask_dir,
        "dynamic_mask_channel": dynamic_mask_channel,
        "per_frame": per_frame, "decile_results": decile_results,
        "control_min_deformation": control_a, "control_periodicity": control_b,
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[{scene_label}] analysed {len(per_frame)} frames -> {out_dir}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse Probe D: deformation-correlated brightness bias")
    parser.add_argument("--traj_dir", required=True, help="Output dir of render_trajectory.py")
    parser.add_argument("--source_path", required=True)
    parser.add_argument("--train_light_folder", default="chapel_day_4k_32x16_rot0")
    parser.add_argument("--frame_stats_csv", required=True, help="frame_stats.csv from dump_lind.py")
    parser.add_argument("--erosion_px", type=int, default=5)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--scene_label", required=True)
    parser.add_argument("--relative_error", action="store_true",
                        help="Use (render-GT)/(GT+eps) instead of the original absolute (render-GT).")
    parser.add_argument("--relative_eps", type=float, default=0.01)
    parser.add_argument("--relative_eps_k", type=float, default=None,
                        help="If given, overrides --relative_eps: epsilon = k * mean(GT "
                             "foreground linear brightness) for that frame, so relative "
                             "error is scale-invariant across lighting conditions of "
                             "different overall brightness (see docs/test1_probe_d_relight.md).")
    parser.add_argument("--dynamic_mask_dir", type=str, default=None,
                        help="If given, intersect the eroded alpha mask with this "
                             "dynamic_mask/ folder's per-frame mask (restricts to "
                             "pixels showing a dynamic/armature-driven surface).")
    parser.add_argument("--dynamic_mask_channel", choices=["rgb", "alpha"], default="rgb",
                        help="Which channel of the dynamic_mask PNGs encodes dynamic/static. "
                             "'rgb' is correct (see docs/blend_files_survey.md); 'alpha' "
                             "reproduces the original buggy behaviour for comparison.")
    args = parser.parse_args()

    analyse_scene(args.traj_dir, args.source_path, args.train_light_folder, args.frame_stats_csv,
                 args.erosion_px, args.out_dir, args.scene_label,
                 relative_error=args.relative_error, relative_eps=args.relative_eps,
                 dynamic_mask_dir=args.dynamic_mask_dir, relative_eps_k=args.relative_eps_k,
                 dynamic_mask_channel=args.dynamic_mask_channel)
