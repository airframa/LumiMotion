# CLAUDE.md — LumiMotion fork (Test 1 investigation)

## What this repo is
Fork of LumiMotion (CVPR 2026 Highlight, arXiv 2604.10994) — dynamic 2D Gaussian
Splatting inverse rendering. Trains a canonical 2DGS scene + a time-conditioned
deformation MLP, then does PBR inverse rendering with ray-traced visibility and
one-bounce indirect illumination.

**I am NOT developing LumiMotion.** This fork exists purely to run a diagnostic
experiment ("Test 1") on their released model. My actual project lives in a
separate RadioGS-based repo.

## Why I'm here — the experiment
My research project extends inverse rendering to temporally coherent light
transport on deforming surfels. LumiMotion is the nearest published neighbour.

**Established by prior code audit (see `docs/lumimotion_eval.md`):**
- LumiMotion's BVH IS rebuilt every training iteration against the currently
  sampled frame's deformed geometry → transport GEOMETRY is frame-aware.
- BUT the radiance a traced ray picks up comes from `_albedo_dc_stage1` — a
  canonical, frame-INDEPENDENT per-Gaussian SH bank baked in Stage 1.
  → transport CONTENT is frozen.
- Exhaustive grep confirmed zero temporal mechanism: no loss, EMA, warping, or
  previous-frame state anywhere in shading.

**The physical error I'm testing for:** under fixed lighting with deforming
geometry, a surfel's outgoing radiance genuinely changes — its normal rotates
w.r.t. the light, its self-shadowing changes. A surfel that rotates away from the
light should dim, and should therefore bleed LESS light onto its neighbours. But
its stored radiance still says it is as bright as it was in canonical pose.

**Test 1 asks:** does that stale-radiance error produce measurable, localized
error under deformation, and does it grow with deformation magnitude?

⚠️ **Critical subtlety — do not fall for this.** `L_ind` DOES change frame to
frame, because the BVH is rebuilt so a ray from point x hits a different Gaussian
at each frame. That is change for the WRONG reason. Observing "the indirect
channel changes" does NOT refute the frozen-content problem. The error is in the
stored per-surfel radiance, not in which surfel gets hit.

## Ground rules for Claude Code
- **Read before writing.** Trace the actual code path and report it before
  proposing any modification.
- All modifications go on the current branch (`test1-indirect-probe`), never on
  `main`. `main` mirrors upstream.
- Prefer ADDITIVE instrumentation (new flags defaulting to off, new dump scripts)
  over changing existing behaviour. The trained checkpoints must stay valid and
  the reproduction must stay reproducible.
- Cite exact `file:line`. Flag uncertainty rather than guessing.
- Never `git add .` — submodules are dirty from compilation, stage explicitly.
- Write analysis to `docs/`, not just chat output.

## Key code locations (from `docs/lumimotion_eval.md`)
- `gaussian_renderer/render_ir.py:435-555` — `rendering_equation()`, the shading path
  - `:469` global direct: `envlight(incident_dirs, mode='pure_env')`
  - `:482-484` / `:512-514` — `pc.trace(...)` calls (relight / training paths)
  - `:487,516` — `incident_visibility = 1 - trace_outputs['alpha']`
  - **`:517` — `local_incident_lights = srgb_to_rgb(trace_outputs['color'])`**
    ← THE indirect term. This is the primary hook point.
  - `:523` — `incident_lights = visibility*global + local`
  - `:529-531` — MC integration; `:558-591` — `GGX_specular`
  - `:147-149` — `sh_features` built from `pc._albedo_dc_stage1` (the frozen bank)
- `scene/gaussian_model.py`
  - `:102` — `GaussianTracer(transmittance_min=0.03)`
  - `:610-621` `get_boundings`; `:624-632` `build_bvh`/`update_bvh`
  - `:634-674` — `trace()`
  - `:43-107` — per-Gaussian state incl. `_albedo_dc_stage1`, `_roughness`
- `utils/time_utils.py:80-211` — `DeformNetwork`. Outputs `d_xyz`, `d_rotation`.
  `d_scaling` is predicted then ZEROED at `:192`. Opacity never deformed.
  `:190-191` — deltas gated by `binary_features`.
- `scene/light.py` — `EnvLight`. Single global `nn.Parameter`, no time index.
- `scripts/train_stage2.py:155-159` — per-iteration BVH update
- `arguments/__init__.py:95-98` — ablation flags: `wo_indirect`,
  `wo_indirect_relight`, `detach_indirect`, `wo_specular`

⚠️ Stage-2 shading is DEFERRED — the rendering equation is applied per-pixel AFTER
rasterization, not per-Gaussian. So "this Gaussian's outgoing radiance at frame t"
is NOT something the existing code computes in per-surfel form.

## Validated baseline (see `docs/lumimotion_repro.md`)
`hook150_v5_spec32`, chapel_day → golden_bay, resolution=2 (their published
config). All metrics within ~1 std of the paper's 5-scene average. Reproduction
confirmed — this pipeline can be trusted as an experimental substrate.

## Test 1 plan (three probes)
- **Probe B (visual):** instrument `render_ir.py` to dump `L_ind` per frame →
  video. Qualitative backbone.
- **Probe C (core):** measure, per Gaussian per frame, the residual between its
  STORED canonical radiance and what its outgoing radiance SHOULD be given its
  deformed normal + current visibility + optimized envmap. This is exactly the
  quantity my method would minimize. Key diagnostic: does it grow with deformation
  magnitude relative to canonical pose?
- **Probe D (free cross-check):** per-pixel error vs. the existing 150 GT renders.
  Does error concentrate in high-indirect regions (concavities, contacts,
  self-shadow) and grow with distance from canonical pose? No code changes needed.

**Scenes:** `jumpingjacks150_v5_spec32` (PERIODIC — same pose recurs, so two frames
at the same phase must have identical indirect illumination; free control with no
ground truth needed) and `standup150_v5_spec32` (monotonic crouch→stand, gives a
deformation-magnitude trend). NOT `hook` (weak self-occlusion) or `spheres` (too
convex).

## Environment
- conda env: `lumimotion` (Python 3.8.18, CUDA 12.1, PyTorch 2.1.0+cu121)
- Server: 10× RTX 4090 (48GB). `CUDA_VISIBLE_DEVICES` to pick a GPU.
- Git: conda shadows OpenSSL → use `gitssh` alias for push/pull/fetch.
- `--load2gpu_on_the_fly` if OOM.
