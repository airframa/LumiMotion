#
# Probe B (Test 1): dump the indirect-illumination term L_ind
# (local_incident_lights, gaussian_renderer/render_ir.py:517) for every frame
# of a trained dynamic scene, holding ONE camera fixed across all frames --
# the "bullet-time" pattern used by scripts/render_materials.py:50,70 -- so
# that any change in the dumped signal is attributable to the deforming
# scene, not to viewpoint change.
#
# Relies on the additive, opt-in `dump_light_indirect=True` hook added to
# render_ir()/rendering_equation() on this branch (see the diff on
# gaussian_renderer/render_ir.py) -- default behaviour of that function is
# untouched, this script is the only caller that sets the flag.
#
# Run from the repo root:
#   python -m scripts_local.dump_lind --model_path ... --source_path ... \
#       --load_iter 55000 --train_light_folder ... --resolution 2 \
#       --depth_ratio 0.0 --output_dir ... --camera_idx 0
#
import argparse
import csv
import json
import os

import torch
import torchvision
from tqdm import tqdm

from arguments import ModelParams, PipelineParams, OptimizationParams, get_combined_args
from gaussian_renderer.render_ir import render_ir
from scene import DeformModel, GaussianModel, Scene
from scene.light import EnvLight
from utils.general_utils import build_rotation, safe_state


def normals_from_quat(quat):
    """World-space surfel normal = 3rd column of the rotation matrix built
    from the (possibly deformed) per-Gaussian quaternion -- the same
    derivation gaussian_model.GaussianModel.trace() uses internally
    (gaussian_model.py:648-656), minus its camera_center-dependent
    flip_align_view step. There's no single camera a per-Gaussian, camera-
    independent quantity should be oriented toward here, so the normal is
    left unsigned (see docs/test1_hook_points.md's open decision #1)."""
    R = build_rotation(quat)
    return R[:, :, 2]


def dump_scene(dataset, pipe, opt, load_iter, output_dir, camera_idx):
    frames_dir = os.path.join(output_dir, "frames")
    raw_dir = os.path.join(output_dir, "light_indirect_raw")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)

    with torch.no_grad():
        deform = DeformModel(deform_type=dataset.deform_type, is_blender=dataset.is_blender,
                              hyper_dim=dataset.hyper_dim, pred_color=dataset.pred_color)
        deform_loaded = deform.load_weights(dataset.model_path, iteration=load_iter)
        assert deform_loaded, f"No deform checkpoint under {dataset.model_path}/deform for iteration {load_iter}"

        gaussians = GaussianModel(dataset.sh_degree, no_binary_separation=dataset.no_binary_separation,
                                  fea_dim=dataset.hyper_dim)
        scene = Scene(dataset, gaussians, load_iteration=load_iter)

        env_light = EnvLight(path=None, device='cuda',
                             resolution=[opt.envmap_resolution // 2, opt.envmap_resolution],
                             max_res=opt.envmap_resolution, activation=opt.envmap_activation)
        env_light.load_weights(dataset.model_path, scene.loaded_iter)

        bg_val = 1 if dataset.white_background else 0
        background = torch.tensor([bg_val, bg_val, bg_val], dtype=torch.float32, device="cuda")

        # Bullet-time camera: one fixed test camera for the whole sequence,
        # mirroring scripts/render_materials.py:50,70 (`getTestCameras()[:1]`),
        # generalised to a caller-chosen index.
        test_cameras = scene.getTestCameras()
        assert 0 <= camera_idx < len(test_cameras), \
            f"--camera_idx {camera_idx} out of range: only {len(test_cameras)} test cameras available"
        view = test_cameras[camera_idx]
        if dataset.load2gpu_on_the_fly:
            view.load2device()

        N = gaussians.get_xyz.shape[0]
        canonical_normals = normals_from_quat(gaussians.get_rotation)

        stats_rows = []
        built_bvh = False

        for fid, timestep_idx in tqdm(list(scene.all_timesteps.items()), desc="Dumping L_ind"):
            time_input = fid.unsqueeze(0).expand(N, -1)
            d_values = deform.step(gaussians.get_xyz.detach(), time_input,
                                   feature=gaussians.get_binary_feature())
            d_xyz, d_rotation, d_scaling, d_opacity, d_color = (
                d_values['d_xyz'], d_values['d_rotation'], d_values['d_scaling'],
                d_values['d_opacity'], d_values['d_color'])

            # CRITICAL: refit the ray-tracer BVH to *this* frame's deformed
            # geometry before tracing. build_bvh() must run once first (it
            # also fixes the triangle topology / self.faces_b that
            # update_bvh() asserts against); every later frame refits via
            # update_bvh(), mirroring the training loop
            # (scripts/train_stage2.py:155-159) -- NOT the eval-script pattern
            # of building once and never rebuilding, which silently traces
            # every frame after the first against frame 0's geometry (see
            # docs/test1_hook_points.md, "Corrections" item 3).
            if not built_bvh:
                gaussians.build_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)
                built_bvh = True
            else:
                gaussians.update_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)

            render_pkg = render_ir(viewpoint_camera=view, pc=gaussians, pipe=pipe,
                                   bg_color=background, d_xyz=d_xyz, d_rotation=d_rotation,
                                   d_scaling=d_scaling, d_opacity=d_opacity, d_color=d_color,
                                   relight=False, env_light=env_light, training=False,
                                   dump_light_indirect=True)

            frame_tag = f"{timestep_idx:04d}"

            # (a) L_ind as a viewable image: reduced exactly the way the
            # shading path itself reduces it -- mean over hemisphere samples,
            # sRGB-encoded, scattered onto the pixel grid and alpha-masked
            # (render_ir.py:552 -> :376-378,391). This key already exists in
            # any training=False, relight=False render_ir() call; no new
            # reduction logic needed.
            torchvision.utils.save_image(
                render_pkg["light_indirect"].clamp(0.0, 1.0),
                os.path.join(frames_dir, f"lind_{frame_tag}.png"))

            # (b) full beauty render, for side-by-side reference.
            torchvision.utils.save_image(
                render_pkg["render"].clamp(0.0, 1.0),
                os.path.join(frames_dir, f"beauty_{frame_tag}.png"))

            # (c) raw per-sampled-ray tensor for offline re-analysis without
            # re-rendering. Shape (P,S,3), linear RGB, P = number of unmasked
            # pixels this frame (varies frame to frame) -- saved together
            # with the boolean (H,W) pixel mask needed to place it back on
            # the image grid.
            torch.save({
                "light_indirect_raw": render_pkg["light_indirect_raw"].detach().cpu(),
                "mask": render_pkg["light_indirect_raw_mask"].detach().cpu(),
                "fid": float(fid.item()),
                "timestep_idx": timestep_idx,
            }, os.path.join(raw_dir, f"lind_raw_{frame_tag}.pt"))

            # Deformation-magnitude + normal-angle stats: x-axis for the next
            # probe, essentially free to collect alongside the render above.
            d_xyz_norm = d_xyz.norm(dim=-1)
            frame_normals = normals_from_quat(gaussians.get_rotation_bias(d_rotation))
            # Unsigned angle: a 2D-Gaussian surfel has no intrinsic
            # front/back, so a sign flip of the same physical plane must not
            # read as a 180-degree change.
            cos_angle = (frame_normals * canonical_normals).sum(-1).abs().clamp(0.0, 1.0)
            angle_deg = torch.rad2deg(torch.arccos(cos_angle))

            stats_rows.append({
                "timestep_idx": timestep_idx,
                "fid": float(fid.item()),
                "mean_d_xyz": d_xyz_norm.mean().item(),
                "max_d_xyz": d_xyz_norm.max().item(),
                "mean_normal_angle_deg": angle_deg.mean().item(),
            })

        if dataset.load2gpu_on_the_fly:
            view.load2device("cpu")

    stats_csv_path = os.path.join(output_dir, "frame_stats.csv")
    with open(stats_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["timestep_idx", "fid", "mean_d_xyz", "max_d_xyz", "mean_normal_angle_deg"])
        writer.writeheader()
        writer.writerows(stats_rows)
    with open(os.path.join(output_dir, "frame_stats.json"), "w") as f:
        json.dump(stats_rows, f, indent=2)

    print(f"Wrote {len(stats_rows)} frames to {output_dir}")
    print(f"  images:    {frames_dir}")
    print(f"  raw L_ind: {raw_dir}")
    print(f"  stats:     {stats_csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dump per-frame L_ind (Probe B, Test 1)")
    model = ModelParams(parser)
    pipeline = PipelineParams(parser)
    opt = OptimizationParams(parser)

    parser.add_argument('--load_iter', type=int, default=-1, help="Iteration to load.")
    parser.add_argument("--iteration", default=-1, type=int)
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Defaults to <model_path>/probe_b_lind/cam<camera_idx>")
    parser.add_argument("--camera_idx", type=int, default=0,
                        help="Fixed test-camera index to render every frame from (bullet-time).")
    parser.add_argument("--quiet", action="store_true")

    # This script targets LumiMotion's Blender/D-NeRF-relight scenes (Test
    # 1's dataset). `is_blender` selects the deform-MLP architecture that was
    # actually trained (time-embedding width, presence of the timenet head --
    # utils/time_utils.py:89-108) and must match the checkpoint being loaded.
    # get_combined_args() (arguments/__init__.py) always lets a *present*
    # argparse default override the saved cfg_args value, even when the flag
    # wasn't passed on the command line, so every training/eval invocation in
    # this repo repeats --is_blender --eval on every call (see
    # scripts_local/run_test1_scene.sh). We default them the same way here so
    # the script works against these checkpoints without requiring the
    # caller to repeat them; pass --is_blender/--eval explicitly if a
    # non-Blender scene ever needs this script.
    parser.set_defaults(is_blender=True, eval=True)

    args = get_combined_args(parser)
    print("Dumping L_ind for", args.model_path)

    safe_state(args.quiet)

    # get_combined_args() drops any argparse arg left at its default of None
    # (neither cfg_args nor the cmdline provided a non-None value for it), so
    # args.output_dir may not exist at all rather than being None -- use
    # getattr, not `args.output_dir or ...`.
    output_dir = getattr(args, "output_dir", None) or os.path.join(
        args.model_path, "probe_b_lind", f"cam{args.camera_idx}")

    dump_scene(model.extract(args), pipeline.extract(args), opt.extract(args),
              args.load_iter, output_dir, args.camera_idx)
