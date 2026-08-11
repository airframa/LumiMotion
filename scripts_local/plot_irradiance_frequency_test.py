#
# Plots + summary table from scripts_local/irradiance_frequency_test.py's
# results.json. Standalone, no LumiMotion code/models touched.
#
# Run from the repo root:
#   python -m scripts_local.plot_irradiance_frequency_test --out_dir docs/irradiance_frequency_test_assets
#
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def res_sort_key(label):
    # "512x256" or "4096x2048 (full)" -> width, for numeric x-ordering
    w = int(label.split("x")[0])
    return w


def main(out_dir):
    with open(os.path.join(out_dir, "results.json")) as f:
        data = json.load(f)

    results = data["results"]
    thetas = data["thetas"]
    occlusion_fracs = data["occlusion_fracs"]
    measured = data["measured_angles"]
    envmaps = list(results.keys())
    resolutions = sorted(results[envmaps[0]].keys(), key=res_sort_key)
    widths = [res_sort_key(r) for r in resolutions]

    # ---- main plot: relative irradiance change vs resolution, at the 3 measured angles, per occlusion ----
    measured_thetas = {k: min(thetas, key=lambda t: abs(t - v)) for k, v in measured.items()}
    fig, axes = plt.subplots(1, len(occlusion_fracs), figsize=(5.5 * len(occlusion_fracs), 5), sharey=True)
    if len(occlusion_fracs) == 1:
        axes = [axes]
    colors = {"median": "tab:blue", "p90": "tab:orange", "p99": "tab:red"}
    for ax, f in zip(axes, occlusion_fracs):
        for label, theta in measured_thetas.items():
            # mean across envmaps, per resolution
            means = []
            for r in resolutions:
                vals = [results[e][r][str(f)]["theta"][str(theta)]["mean"] for e in envmaps]
                means.append(np.mean(vals))
            ax.plot(widths, means, marker='o', label=f"{label} ({measured[label]}°)", color=colors[label])
        ax.set_xscale("log")
        ax.set_xlabel("envmap width (px, log scale)")
        ax.set_title(f"occlusion = {f}")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("relative irradiance change |ΔE|/E\n(mean over envmaps, normals, rotation axes)")
    axes[0].legend()
    fig.suptitle("Diffuse irradiance change vs. envmap resolution, at Probe C's measured rotation angles")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "main_result.png"), dpi=140)
    plt.close(fig)

    # ---- theta sweep, 0-180, at full resolution and 32x16, per occlusion ----
    fig, axes = plt.subplots(1, len(occlusion_fracs), figsize=(5.5 * len(occlusion_fracs), 5), sharey=True)
    if len(occlusion_fracs) == 1:
        axes = [axes]
    lo_res, hi_res = resolutions[0], resolutions[-1]
    for ax, f in zip(axes, occlusion_fracs):
        for r, style in [(lo_res, '--'), (hi_res, '-')]:
            means = []
            for t in thetas:
                vals = [results[e][r][str(f)]["theta"][str(t)]["mean"] for e in envmaps]
                means.append(np.mean(vals))
            ax.plot(thetas, means, style, marker='.', label=r)
        for label, theta in measured_thetas.items():
            ax.axvline(measured[label], color='gray', lw=0.7, ls=':')
        ax.set_xlabel("rotation angle θ (deg)")
        ax.set_title(f"occlusion = {f}")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("relative irradiance change |ΔE|/E")
    axes[0].legend()
    fig.suptitle(f"Full sweep: {lo_res} (dashed) vs. {hi_res} (solid)")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "theta_sweep.png"), dpi=140)
    plt.close(fig)

    # ---- occlusion comparison at full resolution ----
    fig, ax = plt.subplots(figsize=(7, 5))
    for f in occlusion_fracs:
        means = []
        for t in thetas:
            vals = [results[e][hi_res][str(f)]["theta"][str(t)]["mean"] for e in envmaps]
            means.append(np.mean(vals))
        ax.plot(thetas, means, marker='.', label=f"occlusion={f}")
    for label, theta in measured_thetas.items():
        ax.axvline(measured[label], color='gray', lw=0.7, ls=':')
    ax.set_xlabel("rotation angle θ (deg)")
    ax.set_ylabel("relative irradiance change |ΔE|/E")
    ax.set_title(f"Occlusion comparison at {hi_res} (full resolution)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "occlusion_comparison.png"), dpi=140)
    plt.close(fig)

    # ---- summary table (JSON + printed) ----
    table = []
    for f in occlusion_fracs:
        for label, theta in measured_thetas.items():
            row = {"occlusion": f, "angle_label": label, "theta_deg": measured[label]}
            for r in resolutions:
                vals = [results[e][r][str(f)]["theta"][str(theta)]["mean"] for e in envmaps]
                row[r] = float(np.mean(vals))
            table.append(row)
    with open(os.path.join(out_dir, "summary_table.json"), "w") as f_out:
        json.dump(table, f_out, indent=2)

    print(f"{'occ':>5} {'angle':>8} {'theta':>6} " + " ".join(f"{r:>16}" for r in resolutions))
    for row in table:
        vals = " ".join(f"{row[r]*100:15.2f}%" for r in resolutions)
        print(f"{row['occlusion']:>5} {row['angle_label']:>8} {row['theta_deg']:>6} {vals}")

    print(f"Wrote plots + summary_table.json to {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", type=str, default="docs/irradiance_frequency_test_assets")
    args = parser.parse_args()
    main(args.out_dir)
