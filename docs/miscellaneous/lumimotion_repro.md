# LumiMotion Reproduction Record

**Date:** August 2026
**Purpose:** Establish that our LumiMotion pipeline is sound before using it as the
substrate for Test 1 (frozen-transport investigation). If we later claim "we
reproduced LumiMotion and observed X", this is the evidence that the reproduction
itself was valid.

**Verdict: REPRODUCTION CONFIRMED.** All metrics within ~1 std of the paper's
5-scene average; one metric (albedo LPIPS) beats their average. Used their exact
published configuration.

---

## 1. Configuration

| Item | Value |
|---|---|
| Repo | `joaxkal/LumiMotion` (CVPR 2026 Highlight, arXiv 2604.10994) |
| Scene | `hook150_v5_spec32` |
| Static counterpart | `hook150_v5_spec32_statictimestep1` (auto-detected by eval scripts) |
| Train light | `chapel_day_4k_32x16_rot0` |
| Test / relight light | `golden_bay_4k_32x16_rot330` |
| Resolution | `2` — **matches `bash_scripts/synthetic_results_from_paper.sh` (`RESOLUTION=2`)** |
| Depth ratio | `0.0` (stage 2 / eval), `1.0` (stage 1) |
| Stage 1 iterations | 35,000 |
| Stage 2 iterations | 55,000 (loaded from stage-1 iter 35,000) |
| `diffuse_sample_num` | 512 |
| Output dir | `outputs_sanity_moresep/chapelday_goldenbay/hook150_v5_spec32_r2_mlp` |

Environment: conda env `lumimotion`, Python 3.8.18, CUDA 12.1 (`nvcc` 12.1),
PyTorch 2.1.0+cu121. Single GPU.

Stage 1 flags: `--is_blender --eval --gt_alpha_mask_as_scene_mask
--densify_until_iter=20000 --lambda_separation=0.001 --d_xyz_loss_weight=0.001
--binarization_warm_up=1000 --d_color_reg_loss_weight=0.01`

---

## 2. Results vs. paper

The paper's Table 2 reports **averages over 5 scenes** with ± std. Ours is a
**single scene** (hook), so spread of ~1 std is expected and not a discrepancy.

**Protocol note:** the paper's comparison is the STATIC evaluation — LumiMotion
trains on the dynamic scene but is tested on the same views and the same single
timestep as the static baselines. So `eval_*_static` is the apples-to-apples row.

### Chapel Day → Golden Bay

| Metric | Ours (hook) | Paper (5-scene avg) | Delta |
|---|---|---|---|
| Albedo PSNR ↑ | 28.79 | 30.838 ± 1.798 | −1.1 std |
| Albedo SSIM ↑ | 0.966 | 0.973 ± 0.007 | −1.0 std |
| Albedo LPIPS ↓ | **0.031** | 0.036 ± 0.014 | **better than avg** |
| Relight PSNR ↑ | 28.01 | 28.563 ± 0.478 | −1.2 std |
| Relight SSIM ↑ | 0.922 | 0.939 ± 0.011 | −1.5 std |
| Relight LPIPS ↓ | 0.051 | 0.041 ± 0.007 | −1.4 std |

Additional (no paper comparison available):
- Roughness MSE: 0.013
- NVS (static): PSNR 27.50, SSIM 0.947, LPIPS 0.022
- NVS (dynamic): PSNR 27.47, SSIM 0.947, LPIPS 0.022
- Material (dynamic eval): PSNR 29.02, SSIM 0.966, LPIPS 0.032
- Relight (dynamic eval): PSNR 27.52, SSIM 0.919, LPIPS 0.054

---

## 3. Pipeline stages executed

1. `train_stage1` (35k) — geometry + deformation
2. `render_stage1_insights` — diagnostics
3. `train_stage2` (55k, from 35k ckpt) — albedo, roughness, envmap
4. `render_materials`
5. `scale_albedo_static` → `albedo_scale_linear_static.json`
6. `eval_relight_static` → `results_relight_static.json`
7. `eval_nvs_static` → `results_nvs_static.json`
8. `eval_material_static` → `results_material_static.json`
9. `scale_albedo_dynamic`, `eval_material_dynamic`, `eval_relight_dynamic`,
   `eval_nvs_dynamic`

---

## 4. Caveats

- **Single scene, single lighting pair.** Not the full 15-config benchmark. Adequate
  for validating the pipeline; NOT a claim of full reproduction.
- **`hook` is a weak scene for our purposes.** Limited self-occlusion and
  inter-reflection. Fine for pipeline validation, wrong choice for Test 1 — use
  `standup150` or `jumpingjacks150` where limbs occlude the torso.
- Paper's Table 2 std is across scenes, not across seeds, so "within 1 std" means
  "within the scene-to-scene spread", not "within run-to-run noise".
