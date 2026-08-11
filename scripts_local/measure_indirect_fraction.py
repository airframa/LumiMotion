#
# Measure the indirect-illumination fraction: what share of final rendered
# radiance comes from the traced one-bounce indirect term
# (local_incident_lights, render_ir.py:526) rather than the direct
# environment term (incident_visibility * global_incident_lights)?
#
# Motivation (docs/indirect_fraction.md): physics says correct diffuse
# irradiance should change 8-93% under the normal rotations present in
# these scenes (docs/irradiance_frequency_test.md), and
# docs/test1_probe_c_reanalysis.md confirms a real rotation-dependent error
# in the frozen stored radiance -- yet LumiMotion's renders and relighting
# are good (docs/test1_probe_d*.md). If indirect illumination is only a
# small fraction of total radiance, a large RELATIVE error in it is
# negligible in the render, which would reconcile all three results.
#
# WHY THIS RE-RENDERS. scripts_local/render_trajectory.py's dumps are still
# on disk (150 frames x 2 scenes x 2 lighting conditions) but do NOT contain
# the quantity needed. They store `lind_linear` = local_incident_lights
# .mean(dim=1), the raw mean INCIDENT indirect radiance. The contribution to
# final radiance is mean_s[ f * L_local(s) * incident_areas(s) * cos(s) ]
# -- weighted by BRDF, solid angle, and cosine, none of which were saved.
# So it is not recoverable from the dumps and a second pass is required.
#
# METHOD -- exact linear split, two passes, no approximation.
# render_ir.py:538-540 computes
#     transport = incident_lights * incident_areas * n_d_i
#     diffuse   = (f_d * transport).mean(-2);  specular = (f_s * transport).mean(-2)
# f_d, f_s, incident_areas and n_d_i are all independent of incident_lights,
# so (diffuse + specular) is EXACTLY linear in
# incident_lights = incident_visibility*global + local. The existing
# `pipe.wo_indirect` ablation (render_ir.py:527-528) zeroes only the local
# term, and does so AFTER pc.trace(), so visibility, sample directions and
# geometry are bit-identical between passes (training=False =>
# sample_incident_rays uses random_rotate=False, i.e. deterministic
# directions). Therefore:
#     indirect_contribution = full_render_linear - wo_indirect_render_linear
# holds exactly, not approximately. The same argument holds for the
# relight=True path via `pipe.wo_indirect_relight` (render_ir.py:504-507).
#
# The subtraction is done on the LINEAR diffuse/specular images exposed by
# the additive `dump_linear_components` hook added to render_ir.py -- the
# pre-existing "diffuse"/"specular" result keys are sRGB-encoded AND clipped
# to [0,1] by rgb_to_srgb(), so they cannot recover linear radiance for
# bright pixels.
#
# Run from the repo root:
#   python -m scripts_local.measure_indirect_fraction --model_path ... \
#       --source_path ... --load_iter 55000 --train_light_folder ... \
#       --resolution 2 --depth_ratio 0.0 [--relight] --out_dir ...
#
import argparse
import copy
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from tqdm import tqdm

from arguments import ModelParams, PipelineParams, OptimizationParams, get_combined_args
from gaussian_renderer.render_ir import render_ir
from scene import DeformModel, GaussianModel, Scene
from scene.light import EnvLight
from utils.general_utils import safe_state
from scripts_local.render_trajectory import frame_num, load_albedo_scale, build_relight_envlight
from scripts_local.analyse_probe_d import erode_mask, load_dynamic_mask


def stats(x):
    if x.size == 0:
        return {k: float("nan") for k in ["mean", "median", "p90", "p99", "max", "n"]}
    return {
        "mean": float(x.mean()), "median": float(np.median(x)),
        "p90": float(np.percentile(x, 90)), "p99": float(np.percentile(x, 99)),
        "max": float(x.max()), "n": int(x.size),
    }


def run(dataset, pipe, opt, load_iter, out_dir, relight, erosion_px, dynamic_mask_dir,
        pixel_subsample, seed, map_frames):
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)

    with torch.no_grad():
        deform = DeformModel(deform_type=dataset.deform_type, is_blender=dataset.is_blender,
                             hyper_dim=dataset.hyper_dim, pred_color=dataset.pred_color)
        assert deform.load_weights(dataset.model_path, iteration=load_iter)

        gaussians = GaussianModel(dataset.sh_degree, no_binary_separation=dataset.no_binary_separation,
                                  fea_dim=dataset.hyper_dim)
        scene = Scene(dataset, gaussians, load_iteration=load_iter)

        if relight:
            env_light = build_relight_envlight(dataset)
        else:
            env_light = EnvLight(path=None, device='cuda',
                                 resolution=[opt.envmap_resolution // 2, opt.envmap_resolution],
                                 max_res=opt.envmap_resolution, activation=opt.envmap_activation)
            env_light.load_weights(dataset.model_path, scene.loaded_iter)

        base_color_scale = load_albedo_scale(dataset.model_path, dataset.resolution)
        bg_val = 1 if dataset.white_background else 0
        background = torch.tensor([bg_val] * 3, dtype=torch.float32, device="cuda")

        # second pipeline config with only the indirect term ablated
        pipe_direct = copy.deepcopy(pipe)
        pipe_direct.wo_indirect = True
        pipe_direct.wo_indirect_relight = True

        tagged = [(c, "train") for c in scene.getTrainCameras()] + [(c, "test") for c in scene.getTestCameras()]
        tagged.sort(key=lambda cs: frame_num(cs[0]))
        N = gaussians.get_xyz.shape[0]
        built_bvh = False

        per_frame = []
        pooled_fracs = []
        map_payloads = {}

        for view, split in tqdm(tagged, desc="Indirect fraction" + (" (relight)" if relight else "")):
            if dataset.load2gpu_on_the_fly:
                view.load2device()
            fnum = frame_num(view)

            time_input = view.fid.unsqueeze(0).expand(N, -1)
            dv = deform.step(gaussians.get_xyz.detach(), time_input, feature=gaussians.get_binary_feature())
            d_xyz, d_rotation, d_scaling = dv['d_xyz'], dv['d_rotation'], dv['d_scaling']
            d_opacity, d_color = dv['d_opacity'], dv['d_color']

            # per-frame BVH refit (never the eval scripts' frame-0-only BVH)
            if not built_bvh:
                gaussians.build_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)
                built_bvh = True
            else:
                gaussians.update_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)

            common = dict(viewpoint_camera=view, pc=gaussians, bg_color=background,
                          d_xyz=d_xyz, d_rotation=d_rotation, d_scaling=d_scaling,
                          d_opacity=d_opacity, d_color=d_color, relight=relight,
                          env_light=env_light, training=False, base_color_scale=base_color_scale,
                          dump_linear_components=True)
            pkg_full = render_ir(pipe=pipe, **common)
            pkg_direct = render_ir(pipe=pipe_direct, **common)

            total_lin = (pkg_full["diffuse_linear"] + pkg_full["specular_linear"])       # (3,H,W) linear
            direct_lin = (pkg_direct["diffuse_linear"] + pkg_direct["specular_linear"])
            indirect_lin = total_lin - direct_lin                                        # exact

            total_s = total_lin.mean(dim=0)      # channel-mean scalar radiance
            indirect_s = indirect_lin.mean(dim=0)

            H, W = total_s.shape
            mask = erode_mask((pkg_full["rend_alpha"][0] > 0.5).cpu(), erosion_px)
            if dynamic_mask_dir is not None:
                dyn = load_dynamic_mask(dynamic_mask_dir, fnum, (H, W))
                mask_dyn = mask & dyn
            else:
                mask_dyn = mask

            frac_map = (indirect_s / total_s.clamp_min(1e-8)).cpu()
            m_fg, m_dyn = mask.numpy(), mask_dyn.numpy()
            frac_np = frac_map.numpy()

            f_fg = frac_np[m_fg]
            f_dyn = frac_np[m_dyn]

            rec = {
                "frame_num": fnum, "split": split,
                "mean_d_xyz": float(d_xyz.norm(dim=-1).mean().item()),
                "n_fg": int(m_fg.sum()), "n_dyn": int(m_dyn.sum()),
                "foreground": stats(f_fg), "dynamic": stats(f_dyn),
                "mean_total_radiance_dyn": float(total_s.cpu().numpy()[m_dyn].mean()) if m_dyn.sum() else float("nan"),
                "mean_indirect_radiance_dyn": float(indirect_s.cpu().numpy()[m_dyn].mean()) if m_dyn.sum() else float("nan"),
            }
            per_frame.append(rec)

            if f_dyn.size:
                take = min(pixel_subsample, f_dyn.size)
                pooled_fracs.append(rng.choice(f_dyn, size=take, replace=False))

            if fnum in map_frames:
                map_payloads[fnum] = {
                    "render_srgb": pkg_full["render"].clamp(0, 1).cpu().numpy(),
                    "frac": frac_np, "mask_dyn": m_dyn,
                }

            if dataset.load2gpu_on_the_fly:
                view.load2device("cpu")

    pooled = np.concatenate(pooled_fracs) if pooled_fracs else np.array([])

    # ---- plots ----
    for fnum, p in map_payloads.items():
        fig, axes = plt.subplots(1, 2, figsize=(11, 5))
        axes[0].imshow(np.transpose(p["render_srgb"], (1, 2, 0)))
        axes[0].set_title("render (sRGB)")
        shown = np.where(p["mask_dyn"], p["frac"], np.nan)
        im = axes[1].imshow(shown, cmap="magma", vmin=0, vmax=max(np.nanpercentile(shown, 99), 1e-3))
        axes[1].set_title("indirect fraction (dynamic region)")
        for ax in axes:
            ax.axis("off")
        fig.colorbar(im, ax=axes[1], fraction=0.046)
        fig.suptitle(f"frame {fnum}")
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, f"map_frame{fnum:04d}.png"), dpi=140)
        plt.close(fig)

    if pooled.size:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.hist(pooled, bins=120, color="tab:purple", alpha=0.85)
        for q, c in [(50, "orange"), (90, "red"), (99, "darkred")]:
            v = np.percentile(pooled, q)
            ax.axvline(v, color=c, lw=1.2, label=f"p{q}={v:.4f}")
        ax.set_xlabel("indirect fraction of total linear radiance (per pixel)")
        ax.set_ylabel("count")
        ax.set_title("Distribution over dynamic-region pixels, all frames")
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "distribution.png"), dpi=140)
        plt.close(fig)

    dx = np.array([r["mean_d_xyz"] for r in per_frame])
    fm = np.array([r["dynamic"]["mean"] for r in per_frame])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].plot([r["frame_num"] for r in per_frame], fm, marker='.', lw=1)
    axes[0].set_xlabel("frame"); axes[0].set_ylabel("mean indirect fraction (dynamic)")
    axes[0].set_title("across the sequence")
    axes[1].scatter(dx, fm, s=14, alpha=0.75)
    r = float(np.corrcoef(dx, fm)[0, 1]) if dx.std() > 0 and fm.std() > 0 else float("nan")
    axes[1].set_xlabel("frame mean |d_xyz|"); axes[1].set_ylabel("mean indirect fraction (dynamic)")
    axes[1].set_title(f"vs. deformation magnitude (r={r:.3f})")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "per_frame.png"), dpi=140)
    plt.close(fig)

    summary = {
        "relight": relight, "erosion_px": erosion_px,
        "dynamic_mask_dir": dynamic_mask_dir,
        "pooled_dynamic": stats(pooled),
        "pooled_foreground_frameavg": {
            k: float(np.mean([r["foreground"][k] for r in per_frame])) for k in ["mean", "median", "p90", "p99"]
        },
        "corr_frac_vs_deformation": r,
        "per_frame": per_frame,
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k != "per_frame"}, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure indirect-illumination fraction of rendered radiance")
    model = ModelParams(parser)
    pipeline = PipelineParams(parser)
    opt = OptimizationParams(parser)
    parser.add_argument('--load_iter', type=int, default=-1)
    parser.add_argument("--iteration", default=-1, type=int)
    parser.add_argument("--out_dir", type=str, default=None)
    parser.add_argument("--relight", action="store_true")
    parser.add_argument("--erosion_px", type=int, default=5)
    parser.add_argument("--dynamic_mask_dir", type=str, default=None)
    parser.add_argument("--pixel_subsample", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--map_frames", type=int, nargs="*", default=[25, 75, 125])
    parser.add_argument("--quiet", action="store_true")
    parser.set_defaults(is_blender=True, eval=True)

    args = get_combined_args(parser)
    safe_state(args.quiet)
    out_dir = getattr(args, "out_dir", None) or os.path.join(
        args.model_path, "indirect_fraction" + ("_relight" if args.relight else ""))

    run(model.extract(args), pipeline.extract(args), opt.extract(args), args.load_iter, out_dir,
        args.relight, args.erosion_px, args.dynamic_mask_dir, args.pixel_subsample, args.seed,
        set(args.map_frames))
