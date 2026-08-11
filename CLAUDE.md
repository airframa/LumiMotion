# CLAUDE.md — LumiMotion fork (diagnostic experiments)

## What this repo is
Fork of LumiMotion (CVPR 2026 Highlight, arXiv 2604.10994) — dynamic 2D Gaussian
Splatting inverse rendering. Trains a canonical 2DGS scene + a time-conditioned
deformation MLP, then does PBR inverse rendering with ray-traced visibility and
one-bounce indirect illumination.

**I am NOT developing LumiMotion.** This fork exists purely to run diagnostic
experiments on their released model and data. My actual project lives in a separate
RadioGS-based repo.

---

## STATUS

### Test 1: COMPLETE — see `docs/test1_conclusion.md`

**Question:** LumiMotion's BVH is rebuilt per frame (transport *geometry* is
frame-aware), but traced radiance comes from `_albedo_dc_stage1`, a canonical
frame-independent SH bank (transport *content* is frozen). Does that produce
measurable, deformation-scaled error?

**Answer:** the error is **REAL** but its render effect is **NEGLIGIBLE in these
scenes**. Full causal chain, all links measured:

1. Relative error in stored radiance is large — 8% / 49% / 93% at the median / p90 /
   p99 observed normal rotations (8.7° / 49.6° / 91.2°); 15–112% under occlusion.
2. The error is genuinely present per-Gaussian — 61% (jumpingjacks) / 75% (standup)
   of dynamic Gaussians show residual magnitude tracking their own rotation.
3. **But indirect light is only 2.8% (jumpingjacks) / 9.6% (standup) of total
   rendered radiance.**
4. So implied render error is 0.12–0.45% / 0.89–4.92% — at or below the measured
   reconstruction noise floor (2.4–5.4% / 5.5–13.2%).

Nothing is left unexplained. The renders are good *because* the images contain
little indirect light, not because the transport model is right.

**The chain has one free parameter: indirect fraction.** Implied error scales
linearly with it.

### Test 2: CURRENT — measure indirect fraction in realistic configurations

**Decisive question:** does any realistic scene configuration exceed ~25% indirect
fraction? If yes, the effect clears the noise floor and the direction is live. If
no, abandon. **This threshold is pre-committed.**

Measured directly in Blender via the Cycles indirect diffuse AOV — **no Gaussian
training needed**, just single-frame renders.

**The ladder** (each step isolates one variable):
1. `jumpingjacks` as shipped, `diffuse_bounces=1` — should reproduce ~3%, validating
   the Blender-side method against the Gaussian-side measurement
2. Same scene, `diffuse_bounces=8` — isolates the render-setting contribution
3. Corner (two nearby walls) — isolates enclosure
4. Saturated coloured bounce surface — isolates albedo
5. Draped cloth with real folds — the configuration of actual interest
6. Enclosed interior — upper bound

---

## ⚠️ Benchmark properties discovered (`docs/blend_files_survey.md`)

- **`diffuse_bounces=1`** — the GT itself is single-bounce. This partly explains the
  low indirect fraction independently of geometry. LumiMotion's model also does
  one-bounce indirect, so it is internally consistent with its GT; evaluating them
  on multi-bounce data would be testing outside their design assumption, which is a
  legitimate benchmark critique but must be stated plainly.
- **128 samples + denoising** — caveat on any noise-floor comparison.
- **Cameras are fixed-seed (40422) random points on a sphere, NOT an orbit** — the
  same seed is reused across every scene. Generating multi-view-per-timestep data is
  therefore a trivial modification. This removes the blocker that made per-frame
  training impossible on the released data.
- **`dynamic_mask` PNGs: RGB is the dynamic/static segmentation; ALPHA is just the
  whole-scene silhouette.** `analyse_probe_d.py`'s `load_dynamic_mask()` thresholds
  Alpha — wrong channel. Impact likely small (foreground-only and dynamic-restricted
  numbers agreed to within 0.1pp), but **not yet re-verified**.
- **View Transform ("Raw" vs "Standard") is never set by any script** — always a
  manual per-file GUI setting. This is exactly the author's warning. Cannot be
  inferred or fixed from code; verify manually and record what you set.
- **Blender 3.6.13 required.** System Blender 3.0.1 crashes on these files. A
  portable 3.6.13 was downloaded for headless work.
- Only Combined / DiffuseColor / Z / Cryptomatte passes are enabled. Indirect
  diffuse and glossy are off but trivial to enable.
- Envmap-only lighting — no light objects. Mixamo-rigged character, procedural
  checker floor, fixed-scalar roughness on the character material.

---

## Ground rules for Claude Code
- **Read before writing.** Trace the actual code path and report it before proposing
  any modification.
- All modifications go on the current branch, never on `main`. `main` mirrors
  upstream.
- Prefer ADDITIVE instrumentation (new flags defaulting to off, new scripts) over
  changing existing behaviour. Trained checkpoints must stay valid and the
  reproduction must stay reproducible.
- Cite exact `file:line`. Flag uncertainty rather than guessing.
- Never `git add .` — submodules are dirty from compilation, stage explicitly.
- Write analysis to `docs/`, not just chat output.
- `blend_files/` is READ-ONLY reference material from the original author. Do not
  modify anything in it; copy out first if a modified scene is needed.

---

## Key code locations (from `docs/lumimotion_eval.md`)
- `gaussian_renderer/render_ir.py:435-555` — `rendering_equation()`, the shading path
  - `:469` global direct: `envlight(incident_dirs, mode='pure_env')`
  - `:482-484` / `:512-514` — `pc.trace(...)` (relight / training paths)
  - `:487,516` — `incident_visibility = 1 - trace_outputs['alpha']`
  - **`:517` — `local_incident_lights = srgb_to_rgb(trace_outputs['color'])`** ← the
    indirect term, primary hook point
  - `:523` — `incident_lights = visibility*global + local`
  - `:529-531` — MC integration; `:558-591` — `GGX_specular`
  - `:147-149` — `sh_features` built from `pc._albedo_dc_stage1` (the frozen bank)
  - **Our additive hooks:** `dump_light_indirect`, `dump_linear_components` (both
    default off; outputs bit-for-bit unchanged when unset)
- `scene/gaussian_model.py` — `:102` `GaussianTracer`; `:610-621` `get_boundings`;
  `:624-632` `build_bvh`/`update_bvh`; `:634-674` `trace()`; `:43-107` per-Gaussian
  state incl. `_albedo_dc_stage1`, `_roughness`; `:179-197` `get_binary_feature`
- `utils/time_utils.py:80-211` — `DeformNetwork`. Outputs `d_xyz`, `d_rotation`.
  `d_scaling` predicted then ZEROED at `:192`. Opacity never deformed. `:190-191`
  deltas gated by `binary_features`.
- `scene/light.py` — `EnvLight`. Single global `nn.Parameter`, no time index.
- `scripts/train_stage2.py:155-159` — per-iteration BVH update (the CORRECT pattern)
- `arguments/__init__.py:95-98` — `wo_indirect`, `wo_indirect_relight`,
  `detach_indirect`, `wo_specular`

⚠️ Stage-2 shading is DEFERRED — the rendering equation is applied per-pixel AFTER
rasterization, not per-Gaussian. "This Gaussian's outgoing radiance at frame t" is
NOT computed in per-surfel form by the existing code.

⚠️ **Bug in their released eval scripts.** `eval_nvs_dynamic.py:69,86-88` and
`eval_relight_dynamic.py:80,97-99` build the BVH once on frame 0 and never call
`update_bvh`. Fails silently — passing deformed geometry into `trace()` affects
returned normals and colour math, but ray–triangle intersection still uses the stale
BVH. Likely *understates* their published dynamic numbers. **Any head-to-head
comparison must fix this first**, or we would be beating a handicapped baseline.
Reported to the author.

---

## Methodological lessons from Test 1 (worth re-reading before designing a probe)

Three separate statistical artifacts each independently produced a spurious null in
the original Probe C. Any one alone would have killed the direction:

1. **Pooled correlations across heterogeneous units mask within-unit effects.**
   `residual_i(t) = C_i + Δ_i(t)`; `std(C_i)` was 13–15× the within-Gaussian spread
   of `Δ_i(t)`.
2. **Correlating a signed quantity against an unsigned one is ≈0 by construction.**
   Rotation is an angular distance (≥0); the residual is signed. Check the sign
   structure of both variables before trusting a null.
3. **Small denominators destroy mean-based relative statistics.** 18–56% of dynamic
   Gaussians had `|L_true(canonical)| < 0.05`. Use medians or filter.

Also: **a probe can test the wrong thing convincingly** (Probe B's brightening was
real, visible, and irrelevant — it measured visibility change, which LumiMotion gets
right). And **measure the fraction before chasing the error** — the cheapest
measurement in the whole investigation was the decisive one, and it came last.

---

## Validated baseline (`docs/lumimotion_repro.md`)
`hook150_v5_spec32`, chapel_day → golden_bay, resolution=2 (their published config).
All metrics within ~1 std of the paper's 5-scene average. Reproduction confirmed.

Also trained: `jumpingjacks150_v5_spec32` and `standup150_v5_spec32` under
`outputs_test1/chapelday_goldenbay/`, using their per-scene hyperparameters from
`bash_scripts/synthetic_results_from_paper.sh` (jumpingjacks: `lambda_separation`
0.001 / `d_xyz_loss_weight` 0.001; standup: 0.005 / 0.0 — **these differ**).
`spheres_v5_spec32` has never been trained — a standing gap in every probe.

---

## Environment
- conda env: `lumimotion` (Python 3.8.18, CUDA 12.1, PyTorch 2.1.0+cu121)
- Server: 10× RTX 4090 (48GB). `CUDA_VISIBLE_DEVICES` to pick a GPU.
- Git: conda shadows OpenSSL → use `gitssh` alias for push/pull/fetch.
- `--load2gpu_on_the_fly` if OOM.
- Blender 3.6.13 (portable, downloaded) — system 3.0.1 crashes on these files.
