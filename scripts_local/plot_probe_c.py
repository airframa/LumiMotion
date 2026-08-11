#
# Probe C (Test 1): plots from scripts_local/probe_c_transport_residual.py's
# summary.json + pooled_subsample.npz. Pure post-hoc analysis of already
# computed per-Gaussian data -- no GPU/model code touched here.
#
# Run from the repo root:
#   python -m scripts_local.plot_probe_c --probe_c_dir ... --out_dir ... --scene_label ...
#
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def decile_bin(x, y, n_bins=10):
    order = np.argsort(x)
    x, y = x[order], y[order]
    edges = np.linspace(0, len(x), n_bins + 1).astype(int)
    bx, by, bse = [], [], []
    for i in range(n_bins):
        xs, ys = x[edges[i]:edges[i + 1]], y[edges[i]:edges[i + 1]]
        if len(xs) == 0:
            bx.append(np.nan); by.append(np.nan); bse.append(np.nan)
            continue
        bx.append(xs.mean())
        by.append(ys.mean())
        bse.append(ys.std() / max(np.sqrt(len(ys)), 1))
    return np.array(bx), np.array(by), np.array(bse)


def plot_pooled(residual, rotation, dynamic_flag, out_path, scene_label, y_label="signed residual"):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, mask, title in [(axes[0], np.ones_like(dynamic_flag, dtype=bool), "all Gaussians"),
                            (axes[1], dynamic_flag, "dynamic-only")]:
        rot = rotation[:, mask].reshape(-1)
        res = residual[:, mask].reshape(-1)
        hb = ax.hexbin(rot, res, gridsize=60, mincnt=1, cmap="viridis", bins="log")
        bx, by, bse = decile_bin(rot, res, n_bins=10)
        ax.plot(bx, by, color="red", marker="o", lw=1.5, label="decile mean")
        ax.axhline(0, color="gray", lw=0.7)
        r = np.corrcoef(rot, res)[0, 1] if rot.std() > 0 and res.std() > 0 else float("nan")
        ax.set_title(f"{title} (pooled, all frames)\nPearson r={r:.4f}, n={len(rot)}")
        ax.set_xlabel("normal rotation from canonical (deg)")
        ax.set_ylabel(y_label)
        ax.legend()
        fig.colorbar(hb, ax=ax, label="log10(count)")
    fig.suptitle(scene_label)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return


def plot_per_frame_deformation(per_frame, out_path, scene_label):
    d_xyz = np.array([r["all"]["d_xyz"]["mean"] for r in per_frame])
    res_all = np.array([r["all"]["abs_residual"]["mean"] for r in per_frame])
    res_dyn = np.array([r["dynamic"]["abs_residual"]["mean"] for r in per_frame])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)
    for ax, res, title in [(axes[0], res_all, "all Gaussians"), (axes[1], res_dyn, "dynamic-only")]:
        ax.scatter(d_xyz, res, s=14, alpha=0.7)
        r = np.corrcoef(d_xyz, res)[0, 1]
        ax.set_title(f"{title}\nPearson r={r:.3f}")
        ax.set_xlabel("frame mean |d_xyz|")
        ax.set_ylabel("frame mean |residual|")
    fig.suptitle(f"{scene_label}: per-frame mean |residual| vs. deformation magnitude")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_per_frame_correlation(per_frame, out_path, scene_label):
    idx = np.array([r["frame_idx"] for r in per_frame])
    corr_all = np.array([r["corr_residual_rotation_all"] for r in per_frame])
    corr_dyn = np.array([r["corr_residual_rotation_dynamic"] for r in per_frame])
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(idx, corr_all, label="all Gaussians", marker=".", lw=1)
    ax.plot(idx, corr_dyn, label="dynamic-only", marker=".", lw=1)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("frame index")
    ax.set_ylabel("within-frame Pearson r(residual, rotation)")
    ax.set_title(f"{scene_label}: per-frame residual-vs-rotation correlation over the sequence")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_distribution(residual, rotation, dynamic_flag, frame_idx, out_path, scene_label, tag):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].hist(residual[frame_idx, ~dynamic_flag], bins=80, alpha=0.6, label="static", density=True)
    axes[0].hist(residual[frame_idx, dynamic_flag], bins=80, alpha=0.6, label="dynamic", density=True)
    axes[0].set_xlabel("signed residual"); axes[0].set_ylabel("density"); axes[0].legend()
    axes[0].set_title("residual distribution")

    axes[1].hist(rotation[frame_idx, ~dynamic_flag], bins=80, alpha=0.6, label="static", density=True)
    axes[1].hist(rotation[frame_idx, dynamic_flag], bins=80, alpha=0.6, label="dynamic", density=True)
    axes[1].set_xlabel("normal rotation from canonical (deg)"); axes[1].set_ylabel("density"); axes[1].legend()
    axes[1].set_title("rotation distribution")
    fig.suptitle(f"{scene_label}: frame {frame_idx} ({tag})")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def main(probe_c_dir, out_dir, scene_label):
    os.makedirs(out_dir, exist_ok=True)
    summary = json.load(open(os.path.join(probe_c_dir, "summary.json")))
    npz = np.load(os.path.join(probe_c_dir, "pooled_subsample.npz"))
    residual, rel_residual, rotation = npz["residual"], npz["rel_residual"], npz["rotation_deg"]
    dynamic_flag = npz["dynamic_flag"]

    plot_pooled(residual, rotation, dynamic_flag,
               os.path.join(out_dir, "pooled_residual_vs_rotation.png"), scene_label,
               y_label="signed residual (L_true - L_stored)")
    plot_pooled(rel_residual, rotation, dynamic_flag,
               os.path.join(out_dir, "pooled_relresidual_vs_rotation.png"), scene_label,
               y_label="relative residual (residual / L_stored)")
    plot_per_frame_deformation(summary["per_frame"], os.path.join(out_dir, "per_frame_vs_deformation.png"), scene_label)
    plot_per_frame_correlation(summary["per_frame"], os.path.join(out_dir, "per_frame_correlation.png"), scene_label)

    d_xyz = np.array([r["all"]["d_xyz"]["mean"] for r in summary["per_frame"]])
    idx_max = int(np.argmax(d_xyz))
    idx_min = int(np.argmin(d_xyz))
    plot_distribution(residual, rotation, dynamic_flag, idx_max,
                      os.path.join(out_dir, "distribution_max_deformation.png"), scene_label, "max-deformation frame")
    plot_distribution(residual, rotation, dynamic_flag, idx_min,
                      os.path.join(out_dir, "distribution_min_deformation.png"), scene_label, "min-deformation frame")

    # pooled correlation numbers (all-frame, subsampled) for the report
    pooled_stats = {}
    for name, mask in [("all", np.ones_like(dynamic_flag, dtype=bool)), ("dynamic", dynamic_flag)]:
        rot = rotation[:, mask].reshape(-1)
        res = residual[:, mask].reshape(-1)
        rel = rel_residual[:, mask].reshape(-1)
        pooled_stats[name] = {
            "n": int(len(rot)),
            "pooled_corr_residual_rotation": float(np.corrcoef(rot, res)[0, 1]),
            "pooled_corr_relresidual_rotation": float(np.corrcoef(rot, rel)[0, 1]) if np.isfinite(rel).all() else None,
        }
    with open(os.path.join(out_dir, "pooled_stats.json"), "w") as f:
        json.dump(pooled_stats, f, indent=2)
    print(json.dumps(pooled_stats, indent=2))
    print(f"Wrote plots to {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot Probe C results")
    parser.add_argument("--probe_c_dir", required=True, help="Output dir of probe_c_transport_residual.py")
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--scene_label", required=True)
    args = parser.parse_args()
    main(args.probe_c_dir, args.out_dir, args.scene_label)
