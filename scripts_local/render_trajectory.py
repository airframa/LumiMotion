#
# Probe D (Test 1): render LumiMotion's own 150-frame camera trajectory --
# camera XXXX paired with pose XXXX, matching r_XXXX.png, i.e. the dataset's
# real one-camera-per-timestep sequence -- NOT the bullet-time pattern used
# for Probe B. Dumps, per frame, everything scripts_local/analyse_probe_d.py
# needs to test for a deformation-correlated brightness bias in indirectly
# lit regions: the beauty render, the linear-space per-pixel L_ind
# reduction, the (scaled) linear albedo, the foreground alpha mask, the
# per-Gaussian d_xyz (for pose-similarity search), and the train/test split.
#
# Relies on the additive `dump_light_indirect=True` hook on render_ir()
# introduced for Probe B (gaussian_renderer/render_ir.py) -- no further
# changes to render_ir.py were needed for this probe.
#
# --relight (added for the novel-illumination rerun of Probe D, see
# docs/test1_probe_d_relight.md): swaps the envmap for the held-out test
# light (dataset.test_light_folder's raw .hdr file, not the envmap
# optimized during training) and passes relight=True into render_ir(), using
# exactly the envmap-construction pattern from scripts/eval_relight_dynamic.py
# (:51-60) -- copied verbatim rather than re-derived, since it encodes a
# specific coordinate-frame transform. Default (--relight absent) is
# unchanged: the training-light path this script always had.
#
# Run from the repo root:
#   python -m scripts_local.render_trajectory --model_path ... --source_path ... \
#       --load_iter 55000 --train_light_folder ... --resolution 2 --depth_ratio 0.0 \
#       [--relight]
#
import argparse
import json
import os

import torch
import torchvision
from tqdm import tqdm

from arguments import ModelParams, PipelineParams, OptimizationParams, get_combined_args
from gaussian_renderer.render_ir import render_ir
from scene import DeformModel, GaussianModel, Scene
from scene.light import EnvLight
from utils.general_utils import safe_state


def frame_num(camera):
    """Real dataset frame index (1-based) from e.g. 'r_0083' -> 83."""
    return int(camera.image_name_train_light.split('_')[-1])


def load_albedo_scale(model_path, resolution):
    """Reuse the pipeline's own per-channel albedo scale correction (the
    same scalar-ambiguity fix applied by scripts/scale_albedo_dynamic.py and
    consumed by scripts/eval_material_dynamic.py), keyed by render
    resolution. Falls back to the '2' entry (this project's standard
    resolution) if the exact key is missing."""
    path = os.path.join(model_path, "albedo_scale_linear_dynamic.json")
    with open(path) as f:
        scale_dict = json.load(f)
    key = str(resolution) if str(resolution) in scale_dict else "2"
    return torch.tensor(scale_dict[key], dtype=torch.float32, device="cuda")


def build_relight_envlight(dataset):
    """Verbatim copy of the envmap setup in scripts/eval_relight_dynamic.py:51-60:
    load the held-out light's raw .hdr directly (not the envmap optimized
    during training -- there's nothing to optimize for a light the model
    never saw), build its mip chain / importance-sampling PDF, and apply the
    fixed coordinate-frame transform the relight path expects."""
    env_light = EnvLight(path=os.path.join(dataset.source_path, f"{dataset.test_light_folder}.hdr"),
                         device='cuda', activation='none')
    env_light.build_mips()
    env_light.update_pdf()
    transform = torch.tensor([
        [0, -1, 0],
        [0, 0, 1],
        [-1, 0, 0]
    ], dtype=torch.float32, device="cuda")
    env_light.set_transform(transform)
    return env_light


def render_trajectory(dataset, pipe, opt, load_iter, output_dir, relight=False):
    frames_dir = os.path.join(output_dir, "frames")
    data_dir = os.path.join(output_dir, "frame_data")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    with torch.no_grad():
        deform = DeformModel(deform_type=dataset.deform_type, is_blender=dataset.is_blender,
                             hyper_dim=dataset.hyper_dim, pred_color=dataset.pred_color)
        deform_loaded = deform.load_weights(dataset.model_path, iteration=load_iter)
        assert deform_loaded, f"No deform checkpoint under {dataset.model_path}/deform for iteration {load_iter}"

        gaussians = GaussianModel(dataset.sh_degree, no_binary_separation=dataset.no_binary_separation,
                                  fea_dim=dataset.hyper_dim)
        scene = Scene(dataset, gaussians, load_iteration=load_iter)

        if relight:
            env_light = build_relight_envlight(dataset)
            light_folder = dataset.test_light_folder
        else:
            env_light = EnvLight(path=None, device='cuda',
                                 resolution=[opt.envmap_resolution // 2, opt.envmap_resolution],
                                 max_res=opt.envmap_resolution, activation=opt.envmap_activation)
            env_light.load_weights(dataset.model_path, scene.loaded_iter)
            light_folder = dataset.train_light_folder

        base_color_scale = load_albedo_scale(dataset.model_path, dataset.resolution)

        bg_val = 1 if dataset.white_background else 0
        background = torch.tensor([bg_val, bg_val, bg_val], dtype=torch.float32, device="cuda")

        # Dataset's own trajectory: camera XXXX paired with pose XXXX, sorted
        # by real frame index (not scene.all_timesteps' fid-sort order, and
        # not a single fixed camera).
        tagged = [(c, "train") for c in scene.getTrainCameras()] + [(c, "test") for c in scene.getTestCameras()]
        tagged.sort(key=lambda cs: frame_num(cs[0]))
        assert len(tagged) == len(scene.all_timesteps), (
            f"{len(tagged)} cameras vs {len(scene.all_timesteps)} unique fids -- "
            "train/test camera sets overlap (dataset.eval was probably left False)?")

        N = gaussians.get_xyz.shape[0]
        built_bvh = False

        for view, split in tqdm(tagged, desc="Rendering trajectory"):
            if dataset.load2gpu_on_the_fly:
                view.load2device()

            time_input = view.fid.unsqueeze(0).expand(N, -1)
            d_values = deform.step(gaussians.get_xyz.detach(), time_input,
                                   feature=gaussians.get_binary_feature())
            d_xyz, d_rotation, d_scaling, d_opacity, d_color = (
                d_values['d_xyz'], d_values['d_rotation'], d_values['d_scaling'],
                d_values['d_opacity'], d_values['d_color'])

            # CRITICAL: refit the ray-tracer BVH to *this* frame's deformed
            # geometry before tracing -- every frame, not just frame 0. The
            # shipped eval scripts (eval_nvs_dynamic.py, eval_relight_dynamic.py)
            # build the BVH once and never rebuild it, so pc.trace() silently
            # intersects every later frame against frame-0 geometry (see
            # docs/test1_hook_points.md, "Corrections" item 3). This mirrors
            # the training loop's pattern instead (train_stage2.py:155-159).
            if not built_bvh:
                gaussians.build_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)
                built_bvh = True
            else:
                gaussians.update_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)

            render_pkg = render_ir(viewpoint_camera=view, pc=gaussians, pipe=pipe,
                                   bg_color=background, d_xyz=d_xyz, d_rotation=d_rotation,
                                   d_scaling=d_scaling, d_opacity=d_opacity, d_color=d_color,
                                   relight=relight, env_light=env_light, training=False,
                                   dump_light_indirect=True, base_color_scale=base_color_scale)

            fnum = frame_num(view)
            tag = f"{fnum:04d}"

            torchvision.utils.save_image(render_pkg["render"].clamp(0.0, 1.0),
                                         os.path.join(frames_dir, f"render_{tag}.png"))
            torchvision.utils.save_image(render_pkg["light_indirect"].clamp(0.0, 1.0),
                                         os.path.join(frames_dir, f"lind_{tag}.png"))

            # Per-pixel, linear-space reduction of the raw per-ray L_ind
            # (mean over hemisphere samples). Distinct from Probe B's raw
            # (P,S,3) dump: Probe D's analysis is pixel-by-pixel against GT,
            # so only the reduced, still-linear quantity is kept here.
            H, W = render_pkg["render"].shape[-2:]
            lind_raw = render_pkg["light_indirect_raw"]              # (P,S,3), linear
            lind_pixel_mask = render_pkg["light_indirect_raw_mask"]  # (H,W) bool
            lind_linear = torch.zeros(H, W, 3, device=lind_raw.device, dtype=lind_raw.dtype)
            if lind_raw.shape[0] > 0:
                lind_linear[lind_pixel_mask] = lind_raw.mean(dim=1)

            alpha_mask = (render_pkg["rend_alpha"][0] > 0.5)

            torch.save({
                "render_srgb": render_pkg["render"].detach().cpu(),
                "lind_linear": lind_linear.detach().cpu(),
                "base_color_linear": render_pkg["base_color_linear"].detach().cpu(),
                "alpha_mask": alpha_mask.detach().cpu(),
                # per-Gaussian deformation, half precision -- only used for
                # the "near-identical geometry" pose-similarity search in
                # Probe D's controls, not for anything numerically sensitive.
                "d_xyz": d_xyz.detach().to(torch.float16).cpu(),
                "fid": float(view.fid.item()),
                "frame_num": fnum,
                "split": split,
                "camera_name": view.image_name_train_light,
                "relight": relight,
                "light_folder": light_folder,
            }, os.path.join(data_dir, f"frame_{tag}.pt"))

            if dataset.load2gpu_on_the_fly:
                view.load2device("cpu")

    print(f"Wrote {len(tagged)} frames to {output_dir}")
    print(f"  images: {frames_dir}")
    print(f"  data:   {data_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render the dataset's own camera trajectory (Probe D, Test 1)")
    model = ModelParams(parser)
    pipeline = PipelineParams(parser)
    opt = OptimizationParams(parser)

    parser.add_argument('--load_iter', type=int, default=-1, help="Iteration to load.")
    parser.add_argument("--iteration", default=-1, type=int)
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Defaults to <model_path>/probe_d_trajectory"
                             " (or .../probe_d_trajectory_relight with --relight)")
    parser.add_argument("--relight", action="store_true",
                        help="Render under the held-out test_light_folder envmap "
                             "(relight=True path) instead of the training light.")
    parser.add_argument("--quiet", action="store_true")

    # See scripts_local/dump_lind.py for why these must be defaulted: this
    # targets LumiMotion's Blender/D-NeRF-relight scenes, and
    # get_combined_args() (arguments/__init__.py) always lets a *present*
    # argparse default override the saved cfg_args value for booleans, even
    # when the flag wasn't passed on the command line.
    parser.set_defaults(is_blender=True, eval=True)

    args = get_combined_args(parser)
    print("Rendering trajectory for", args.model_path)

    safe_state(args.quiet)

    # See scripts_local/dump_lind.py: get_combined_args() drops any argparse
    # arg left at its default of None entirely, so args.output_dir may not
    # exist rather than being None -- use getattr, not `args.output_dir or ...`.
    default_dirname = "probe_d_trajectory_relight" if args.relight else "probe_d_trajectory"
    output_dir = getattr(args, "output_dir", None) or os.path.join(args.model_path, default_dirname)

    render_trajectory(model.extract(args), pipeline.extract(args), opt.extract(args), args.load_iter,
                      output_dir, relight=args.relight)
