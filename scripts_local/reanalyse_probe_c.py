#
# Re-analysis of Probe C (docs/test1_probe_c.md), motivated by a contradiction
# with docs/irradiance_frequency_test.md: the standalone physics experiment
# says diffuse irradiance should change by ~8%/49%/93% at the median/p90/p99
# rotation angles Probe C measured, but Probe C's pooled dynamic-only
# correlation between residual and rotation was ~0. Hypothesis under test:
# residual_i(t) = C_i + Delta_i(t), a large per-Gaussian constant C_i from
# the L_stored/L_true definitional mismatch (Probe C's own canonical-pose
# sanity check failure) plus the rotation-dependent term Delta_i(t) of
# actual interest -- pooling across Gaussians mixes between-Gaussian
# variance in C_i with within-Gaussian variance in Delta_i(t), which can
# mask a real effect.
#
# NO new rendering or ray tracing. Reuses the per-Gaussian, per-frame data
# already saved by scripts_local/probe_c_transport_residual.py
# (outputs_test1/.../probe_c_transport_residual/pooled_subsample.npz:
# residual(t), rotation_deg(t), canonical_residual, for a fixed
# 20,000-Gaussian subsample tracked across all 150 frames, plus a
# dynamic/static flag). The ONLY new computation is reading
# `_albedo_dc_stage1` back out of the trained checkpoint's .ply for that
# same subsample -- a parameter read, not a render -- because L_stored
# itself (as opposed to L_true - L_stored) was not persisted, and Check 1
# needs the absolute L_true(canonical) as a relative-change denominator.
#
# A second methodological issue was found during this re-analysis, beyond
# the one the task hypothesized, and is handled explicitly throughout:
# rotation_deg(t) is an angular DISTANCE from canonical, always >= 0.
# residual_i(t) and Delta_i(t) are SIGNED (a Gaussian can rotate toward
# brighter or darker light). Correlating a signed quantity against an
# unsigned one is a different, and generally much weaker, statistical test
# than correlating MAGNITUDES -- which is what the physics experiment
# itself measures (|E(n)-E(n')|/E(n), absolute value throughout). Every
# check below is therefore reported both as literally specified (signed vs.
# rotation) and in the magnitude-consistent form (|.| vs. rotation), and the
# difference between the two is itself a finding, not a footnote.
#
# Run from the repo root:
#   python -m scripts_local.reanalyse_probe_c --out_dir docs/test1_probe_c_reanalysis_assets
#
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

from scene import GaussianModel
from utils.graphics_utils import srgb_to_rgb
from utils.sh_utils import SH2RGB

SCENES = {
    "jumpingjacks": "outputs_test1/chapelday_goldenbay/jumpingjacks150_v5_spec32_r2_mlp",
    "standup": "outputs_test1/chapelday_goldenbay/standup150_v5_spec32_r2_mlp",
}
LOAD_ITER = 55000
ANGLE_EDGES = np.array([0, 3, 6, 9, 15, 22, 30, 40, 52, 65, 80, 95, 115, 140, 165, 181], dtype=float)


def load_L_stored_subsample(model_path, sub_idx, sh_degree=3, fea_dim=1):
    """Channel-mean L_stored for exactly the Gaussians in sub_idx -- a
    parameter read from the checkpoint .ply, no tracer/deform/BVH involved.
    Matches Probe C's own L_stored definition exactly
    (probe_c_transport_residual.py): srgb_to_rgb(SH2RGB(_albedo_dc_stage1)),
    channel-averaged."""
    ply_path = os.path.join(model_path, "point_cloud", f"iteration_{LOAD_ITER}", "point_cloud.ply")
    gaussians = GaussianModel(sh_degree, no_binary_separation=False, fea_dim=fea_dim)
    gaussians.load_ply(ply_path)
    with torch.no_grad():
        L_stored_full = srgb_to_rgb(SH2RGB(gaussians._albedo_dc_stage1.squeeze())).mean(dim=-1)
    idx = torch.from_numpy(sub_idx).long()
    return L_stored_full[idx].detach().cpu().numpy()


def load_physics_curve(path, envmap="chapel_day", resolution="4096x2048 (full)", occlusion=0.0):
    with open(path) as f:
        d = json.load(f)
    thetas = d["thetas"]
    means = [d["results"][envmap][resolution][str(occlusion)]["theta"][str(t)]["mean"] for t in thetas]
    return np.array(thetas), np.array(means)


def pearson(a, b):
    if a.std() == 0 or b.std() == 0 or len(a) < 2:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def bin_by_angle(angle, value, edges, stat="mean"):
    centers, agg, sems, ns = [], [], [], []
    fn = np.mean if stat == "mean" else np.median
    for i in range(len(edges) - 1):
        m = (angle >= edges[i]) & (angle < edges[i + 1])
        if m.sum() < 5:
            centers.append(np.nan); agg.append(np.nan); sems.append(np.nan); ns.append(int(m.sum()))
            continue
        centers.append(float(angle[m].mean()))
        agg.append(float(fn(value[m])))
        sems.append(float(value[m].std() / max(np.sqrt(m.sum()), 1)))
        ns.append(int(m.sum()))
    return np.array(centers), np.array(agg), np.array(sems), np.array(ns)


def per_gaussian_corr(values_2d, rotation_2d, dyn_idx):
    """values_2d, rotation_2d: (n_frames, n_sub). Returns array over dyn_idx
    of within-trajectory Pearson r, nan where undefined."""
    out = np.full(len(dyn_idx), np.nan)
    for k, gi in enumerate(dyn_idx):
        v, r = values_2d[:, gi], rotation_2d[:, gi]
        if v.std() > 0 and r.std() > 0:
            out[k] = np.corrcoef(r, v)[0, 1]
    return out


def summarize_dist(x):
    x = x[~np.isnan(x)]
    return {
        "n": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)),
        "frac_positive": float((x > 0).mean()),
        "p10": float(np.percentile(x, 10)), "p90": float(np.percentile(x, 90)),
    }


def analyse_scene(scene_label, model_path, physics_json, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    npz_path = os.path.join(model_path, "probe_c_transport_residual", "pooled_subsample.npz")
    d = np.load(npz_path)
    residual, rotation = d["residual"], d["rotation_deg"]  # (150, n_sub)
    canonical_residual, sub_idx, dynamic_flag = d["canonical_residual"], d["sub_idx"], d["dynamic_flag"]
    n_frames, n_sub = residual.shape

    L_stored = load_L_stored_subsample(model_path, sub_idx)
    L_true_canon = canonical_residual + L_stored          # (n_sub,)
    delta = residual - canonical_residual[None, :]        # (150,n_sub) == L_true(t) - L_true(canonical), exact

    dyn = dynamic_flag
    dyn_idx = np.where(dyn)[0]
    n_dyn = int(dyn.sum())
    rot_dyn = rotation[:, dyn]
    delta_dyn = delta[:, dyn]
    residual_dyn = residual[:, dyn]

    # ============ CHECK 1: pure physics, L_stored removed ============
    denom = np.abs(L_true_canon).clip(min=1e-6)
    relchg = np.abs(delta) / denom[None, :]  # (150, n_sub)
    relchg_dyn = relchg[:, dyn]

    rot_flat, relchg_flat = rot_dyn.reshape(-1), relchg_dyn.reshape(-1)
    check1_pooled_mean_corr = pearson(rot_flat, relchg_flat)

    c_mean, m_mean, sem_mean, n_mean = bin_by_angle(rot_flat, relchg_flat, ANGLE_EDGES, stat="mean")
    c_med, m_med, sem_med, n_med = bin_by_angle(rot_flat, relchg_flat, ANGLE_EDGES, stat="median")

    # denominator-instability diagnostic: within a representative low-rotation
    # bin, does 1/denom predict relchg, and how much of the bin's total comes
    # from the smallest-denominator few percent of samples?
    denom_dyn_bcast = np.broadcast_to(denom[dyn][None, :], rot_dyn.shape)
    low_mask = (rot_dyn > 3) & (rot_dyn < 6)
    denom_low, relchg_low = denom_dyn_bcast[low_mask], relchg_dyn[low_mask]
    order = np.argsort(denom_low)
    vals_sorted = relchg_low[order]
    top5 = int(max(1, 0.05 * len(vals_sorted)))
    denominator_artifact = {
        "frac_dynamic_gaussians_Ltruecanon_below_0.05": float((denom[dyn] < 0.05).mean()),
        "frac_dynamic_gaussians_Ltruecanon_below_0.10": float((denom[dyn] < 0.10).mean()),
        "low_rotation_bin_3to6deg_corr_relchg_vs_inv_denom": pearson(relchg_low, 1.0 / denom_low),
        "low_rotation_bin_smallest5pct_denom_share_of_total_relchg": float(vals_sorted[:top5].sum() / vals_sorted.sum()),
    }

    # denominator-filtered, robust version: keep only Gaussians whose
    # |L_true(canonical)| is at or above the dynamic-population median (a
    # simple, pre-registered-style threshold, not tuned to produce a result).
    thresh = float(np.median(np.abs(L_true_canon[dyn])))
    keep = np.abs(L_true_canon) >= thresh
    keep_dyn = keep[dyn]
    rot_filt = rot_dyn[:, keep_dyn].reshape(-1)
    relchg_filt = relchg_dyn[:, keep_dyn].reshape(-1)
    check1_filtered_corr = pearson(rot_filt, relchg_filt)
    c_filt, m_filt, sem_filt, n_filt = bin_by_angle(rot_filt, relchg_filt, ANGLE_EDGES, stat="mean")

    phys_theta, phys_mean = load_physics_curve(physics_json, occlusion=0.0)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    axes[0].errorbar(c_mean, m_mean, yerr=sem_mean, marker='o', label="observed, mean/bin (raw)", color="tab:blue")
    axes[0].plot(phys_theta, phys_mean, marker='s', ls='--', color="tab:red",
                label="physics-predicted (irradiance_frequency_test, chapel_day)")
    axes[0].set_title("raw (mean-per-bin) -- distorted by small-denominator outliers")
    axes[1].plot(c_med, m_med, marker='o', label="observed, median/bin", color="tab:green")
    axes[1].plot(c_filt, m_filt, marker='^', label=f"observed, mean/bin, |L_true(canon)|≥{thresh:.3f} only", color="tab:purple")
    axes[1].plot(phys_theta, phys_mean, marker='s', ls='--', color="tab:red", label="physics-predicted")
    axes[1].set_title("robust versions (median, or denominator-filtered)")
    for ax in axes:
        ax.set_xlabel("normal rotation from canonical (deg)")
        ax.set_ylabel("relative irradiance change |ΔL_true| / L_true(canonical)")
        ax.legend(fontsize=8)
    fig.suptitle(f"{scene_label}: Check 1 -- observed vs. physics-predicted")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "check1_physics_comparison.png"), dpi=140)
    plt.close(fig)

    # ============ CHECK 2: within-Gaussian differencing ============
    check2_signed = pearson(rot_dyn.reshape(-1), delta_dyn.reshape(-1))
    check2_abs = pearson(rot_dyn.reshape(-1), np.abs(delta_dyn).reshape(-1))
    original_pooled_signed = pearson(rot_dyn.reshape(-1), residual_dyn.reshape(-1))

    # ============ CHECK 3: per-Gaussian correlations, then aggregate ============
    check3_signed_residual = per_gaussian_corr(residual, rotation, dyn_idx)          # literal task spec
    check3_signed_delta = per_gaussian_corr(delta, rotation, dyn_idx)                # == check3_signed_residual exactly (shift-invariance of Pearson r) -- computed to confirm, not because it differs
    check3_abs_delta = per_gaussian_corr(np.abs(delta), rotation, dyn_idx)           # magnitude-consistent version

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].hist(check3_signed_residual[~np.isnan(check3_signed_residual)], bins=60, color="tab:gray", alpha=0.85)
    axes[0].axvline(0, color="k", lw=1)
    axes[0].set_title("signed residual vs. rotation\n(literal task spec)")
    axes[1].hist(check3_abs_delta[~np.isnan(check3_abs_delta)], bins=60, color="tab:green", alpha=0.85)
    axes[1].axvline(0, color="k", lw=1)
    axes[1].set_title("|Delta_i(t)| vs. rotation\n(magnitude-consistent, C_i removed)")
    for ax in axes:
        ax.set_xlabel("within-trajectory Pearson r, per dynamic Gaussian")
        ax.set_ylabel("count")
    fig.suptitle(f"{scene_label}: Check 3 -- distribution of per-Gaussian correlations")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "check3_per_gaussian_corr_hist.png"), dpi=140)
    plt.close(fig)

    # ============ C_i vs Delta_i(t) magnitude ============
    C_i = canonical_residual[dyn]
    delta_abs_dyn = np.abs(delta_dyn)
    within_gaussian_std = delta_dyn.std(axis=0)

    summary = {
        "scene": scene_label, "n_sub": int(n_sub), "n_dynamic": n_dyn,
        "check1": {
            "pooled_corr_mean_stat_raw": check1_pooled_mean_corr,
            "pooled_corr_denominator_filtered": check1_filtered_corr,
            "denominator_filter_threshold": thresh, "denominator_filter_n_kept": int(keep_dyn.sum()),
            "denominator_artifact_diagnostic": denominator_artifact,
            "binned_mean_raw": {"centers": c_mean.tolist(), "values": m_mean.tolist(), "n": n_mean.tolist()},
            "binned_median_raw": {"centers": c_med.tolist(), "values": m_med.tolist(), "n": n_med.tolist()},
            "binned_mean_filtered": {"centers": c_filt.tolist(), "values": m_filt.tolist(), "n": n_filt.tolist()},
        },
        "check2": {
            "signed_delta_vs_rotation": check2_signed,
            "abs_delta_vs_rotation": check2_abs,
            "original_probe_c_pooled_signed_residual_vs_rotation": original_pooled_signed,
        },
        "check3": {
            "signed_residual_vs_rotation": summarize_dist(check3_signed_residual),
            "signed_delta_vs_rotation_confirms_shift_invariance": summarize_dist(check3_signed_delta),
            "abs_delta_vs_rotation": summarize_dist(check3_abs_delta),
        },
        "C_i_vs_delta": {
            "C_i_mean": float(C_i.mean()), "C_i_median": float(np.median(C_i)), "C_i_std": float(C_i.std()),
            "delta_abs_mean": float(delta_abs_dyn.mean()), "delta_abs_median": float(np.median(delta_abs_dyn)),
            "within_gaussian_std_mean": float(within_gaussian_std.mean()),
            "ratio_Cstd_to_within_gaussian_std": float(C_i.std() / max(within_gaussian_std.mean(), 1e-12)),
            "ratio_Cstd_to_delta_abs_mean": float(C_i.std() / max(delta_abs_dyn.mean(), 1e-12)),
        },
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"=== {scene_label} ===")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", type=str, default="docs/test1_probe_c_reanalysis_assets")
    parser.add_argument("--physics_json", type=str, default="docs/irradiance_frequency_test_assets/results.json")
    args = parser.parse_args()

    all_summaries = {}
    for label, model_path in SCENES.items():
        out_dir = os.path.join(args.out_dir, label)
        all_summaries[label] = analyse_scene(label, model_path, args.physics_json, out_dir)

    with open(os.path.join(args.out_dir, "all_summary.json"), "w") as f:
        json.dump(all_summaries, f, indent=2)
