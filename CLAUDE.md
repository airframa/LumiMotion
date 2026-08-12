# CLAUDE.md — LumiMotion fork (diagnostic campaign)

## What this repo is
Fork of LumiMotion (CVPR 2026 Highlight, arXiv 2604.10994) — dynamic 2D Gaussian
Splatting inverse rendering. Canonical 2DGS + time-conditioned deformation MLP, then
PBR inverse rendering with ray-traced visibility and one-bounce indirect illumination.

**I am NOT developing LumiMotion.** This fork exists purely to run diagnostic
experiments on their released model and data. My actual project lives in a separate
RadioGS-based repo.

---

## STATUS: campaign COMPLETE — read `docs/lumimotion_campaign_summary.md` first

**Outcome: CONTINUE, conditionally.**

The hypothesised error (LumiMotion's traced indirect radiance comes from
`_albedo_dc_stage1`, a canonical frame-independent SH bank — transport *content* is
frozen while transport *geometry* is frame-aware) is **real and measured**. It is
**negligible in the published benchmark**, and the reason is fully explained:

1. Relative error in stored radiance is large — 8/49/93% at median/p90/p99 rotation
2. It is genuinely present per-Gaussian — 61% (jj) / 75% (standup) of dynamic Gaussians
3. **But indirect light is only 4.4% / 9.6% of these images**
4. So render error is 0.19% / 0.90% — at or below the 2.4–13.2% noise floor

**One free parameter: indirect fraction.** Implied error scales linearly with it.

**Test 2 gate PASSED.** Blender ladder: enclosed interior reaches 33.3% mean /
53.5% p90; corner 18.2/38.3; cloth 14.7/34.7 — vs. 6.7/16.5 as shipped. But the
honest read is narrower than "four of six clear": the trustworthy `mean × median`
implied error clears the floor in exactly one cell (interior + standup-like
deformation, 3.13% vs 2.4%). **The effect becomes real in enclosed scenes with
substantial deformation, and remains marginal elsewhere.**

**Binding open risk (NOT tested here):** does RadioGS actually work at 33% indirect
fraction? Inverse rendering gets *harder* under strong inter-reflection. The interior
scene in `scripts_local/test2/` is directly reusable as that test.

---

## ⚠️ Corrections — do not cite the superseded numbers

- `docs/test1_probe_c.md` — **superseded** by `test1_probe_c_reanalysis.md`. Its null
  was three compounding statistical artifacts.
- `docs/test1_probe_d.md`, `docs/test1_probe_d_relight.md` — **superseded** by
  `test1_probe_d_corrected.md`. Three claims retracted: the "99–100% frames positive"
  figure, the standup/golden deformation correlation (+0.099 → +0.011), and the
  "prop is dynamic" claim (it is static — no Armature modifier).
- `docs/indirect_fraction.md` — the pre-RGB-mask numbers (2.79% / 9.56% mean) are
  **superseded** by the corrected ones (4.37% / 9.60% mean; p99 23.7% / 50.8%).

---

## ⚠️ Data and code issues

**In LumiMotion's released code — BVH built once, never updated, in eval.**
`eval_nvs_dynamic.py:69,86-88` and `eval_relight_dynamic.py:80,97-99` build on frame 0
then never call `update_bvh`. Training does it right (`train_stage2.py:155-159`).
**Fails silently** — deformed geometry passed to `trace()` affects returned normals
and colour math, but ray–triangle intersection uses the stale BVH. Likely
*understates* their published dynamic numbers. **Fix before any head-to-head
comparison**, or we would beat a handicapped baseline. Not yet reported to the author.

**`dynamic_mask` PNGs: RGB is the segmentation, ALPHA is the whole-scene silhouette.**
IoU between them 0.18–0.22; alpha selects 4.4–5.3× more pixels. `load_dynamic_mask()`
now defaults to `rgb`; `--dynamic_mask_channel alpha` reproduces old behaviour.
Probe C is unaffected — it uses `get_binary_feature()`, never these PNGs.

**Benchmark suppresses indirect light three independent ways:** open-platform
geometry (dominant — enclosure multiplies indirect 2.7–5×), `diffuse_bounces = 1`
(minor — worth only +7%), and `sample_clamp_indirect = 10.0` (an authored clamp).

**Blender:** files are authored at 4.4.**32**; both 3.6.13 and 4.4.0 warn "expect
loss of data". Verified empirically that **no scene content is lost** (206/264 keys
identical, geometry byte-identical). Render difference ≤5.8%, from the Principled
BSDF v2 rewrite. **Prefer `~/blender-4.4.0-linux-x64/blender`** — the author's GT was
rendered under 4.4.x. Colour management confirmed: `view_transform = Standard`,
exposure 0, gamma 1, envmap `Linear`. `blend_files/` is READ-ONLY — copy before
modifying.

---

## Methodological lessons (re-read before designing any probe)

1. **A probe can test the wrong thing convincingly.** Probe B's brightening was real,
   visible, and irrelevant — it measured visibility change, which LumiMotion gets right.
2. **Pooled correlations across heterogeneous units mask within-unit effects.**
   `std(C_i)` was 13–15× the within-Gaussian spread of the signal.
3. **Correlating a signed quantity against an unsigned one is ≈0 by construction.**
   Pearson r is invariant to subtracting a per-series constant, so removing the offset
   alone changes nothing — both corrections were needed together.
4. **Small denominators destroy mean-based relative statistics.** Use medians or filter.
5. **Channel-mean scalarization hides chromatic effects entirely.** The red-wall
   configuration drives R to 1.58× G/B while the scalar mean *falls* — every probe in
   this campaign would have reported no effect. **Unexplored and worth pursuing.**
6. **Measure the denominator before chasing the numerator.** Indirect fraction was the
   cheapest measurement and the decisive one, and it came last.
7. **Verify a restriction actually restricts.** The dynamic mask was a no-op across
   four probes before anyone checked.

---

## Ground rules for Claude Code
- **Read before writing.** Trace the code path and report before proposing changes.
- Modifications on the working branch, never `main` (which mirrors upstream).
- Prefer ADDITIVE instrumentation (flags defaulting off, new scripts) over changing
  existing behaviour. Checkpoints must stay valid, reproduction reproducible.
- Cite exact `file:line`. Flag uncertainty rather than guessing.
- Never `git add .` — submodules are dirty from compilation; stage explicitly.
- Write analysis to `docs/`, not just chat output.
- `blend_files/` is READ-ONLY author material.

---

## Key code locations
- `gaussian_renderer/render_ir.py:435-555` — `rendering_equation()`
  - `:469` direct: `envlight(incident_dirs, mode='pure_env')`
  - `:482-484` / `:512-514` — `pc.trace(...)` (relight / training)
  - `:487,516` — `incident_visibility = 1 - trace_outputs['alpha']`
  - **`:517` — `local_incident_lights = srgb_to_rgb(trace_outputs['color'])`** ← the
    indirect term
  - `:523` — `incident_lights = visibility*global + local`; `:529-531` MC integration
  - `:147-149` — `sh_features` from `pc._albedo_dc_stage1` (the frozen bank)
  - **Our additive hooks:** `dump_light_indirect`, `dump_linear_components` (default
    off; outputs bit-for-bit unchanged when unset)
- `scene/gaussian_model.py` — `:102` `GaussianTracer`; `:610-621` `get_boundings`;
  `:624-632` `build_bvh`/`update_bvh`; `:634-674` `trace()`; `:43-107` per-Gaussian
  state; `:179-197` `get_binary_feature`
- `utils/time_utils.py:80-211` — `DeformNetwork`; `d_scaling` ZEROED at `:192`;
  opacity never deformed; `:190-191` deltas gated by `binary_features`
- `scene/light.py` — `EnvLight`, single global `nn.Parameter`, no time index
- `arguments/__init__.py:95-98` — `wo_indirect`, `wo_indirect_relight`,
  `detach_indirect`, `wo_specular`

⚠️ Stage-2 shading is DEFERRED — per-pixel after rasterization, not per-Gaussian.

---

## Our instrumentation (`scripts_local/`)
- `dump_lind.py` — per-frame `L_ind`, bullet-time fixed camera, per-frame `update_bvh`
- `render_trajectory.py` — dataset trajectory renders, `--relight` flag
- `analyse_probe_d.py` — render-space analysis; `--dynamic_mask_channel`,
  `--relative_error`, `--relative_eps_k`
- `probe_c_transport_residual.py`, `reanalyse_probe_c.py` — per-Gaussian residual
- `measure_indirect_fraction.py` — the decisive measurement
- `irradiance_frequency_test.py` — standalone physics
- `test2/` — Blender ladder: `render_config.py`, `analyse.py`, `dump_settings.py`

---

## Trained models
`outputs_test1/chapelday_goldenbay/{jumpingjacks150,standup150}_v5_spec32_r2_mlp`,
plus `hook` under `outputs_sanity_moresep/`. Per-scene hyperparameters from
`bash_scripts/synthetic_results_from_paper.sh` **differ** (jj: `lambda_separation`
0.001 / `d_xyz_loss_weight` 0.001; standup: 0.005 / 0.0). `spheres` never trained —
a standing gap in every probe.

⚠️ Their `synthetic_results_from_paper.sh` has two bugs: the `W_BIN` sed never
matches (no leading underscore in `CFG`), and `$START_BIN` is undefined under
`set -u`. Hardcode the values.

---

## Environment
- conda env `lumimotion` (Python 3.8.18, CUDA 12.1, PyTorch 2.1.0+cu121)
- 10× RTX 4090 (48GB). `CUDA_VISIBLE_DEVICES` to pick one.
- Git: conda shadows OpenSSL → `gitssh` alias for push/pull/fetch
- `--load2gpu_on_the_fly` if OOM
- Blender: `~/blender-4.4.0-linux-x64/blender` (preferred),
  `~/blender-3.6.13-linux-x64/blender`. System 3.0.1 crashes on these files.
- ⚠️ `dump_lind.py` raw dumps are ~18–19GB per scene
