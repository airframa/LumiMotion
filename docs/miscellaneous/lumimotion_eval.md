# LumiMotion Evaluation — Method, Data Pipeline, and Dataset Audit

Read-only audit of `LumiMotion_ref/` (CVPR 2026 Highlight, arXiv 2604.10994) and
`data/dnerf-relight/`. Nothing modified anywhere. All citations `file:line` against
`LumiMotion_ref/` unless a path is explicitly given elsewhere. Uncertainty is flagged
inline rather than guessed past.

**Headline finding (Part A3, the priority question):** LumiMotion has **no temporal
coherence of illumination/shading anywhere in the codebase**. Every frame's
visibility, indirect light, direct light, and full shading equation is recomputed
completely independently — no loss term, cached buffer, EMA, or warping scheme ties
frame *t*'s illumination to frame *t*−1's. Its only "temporal coherence" is the
implicit smoothness of a time-conditioned MLP for *geometry*, which has no
illumination analogue. This is confirmed by exhaustive negative-result grepping, not
inferred from absence of a README claim — see §A3 for the full search record.

**Headline finding (Part B):** no Blender/rendering code exists in this repo at all.
The synthetic dataset is distributed pre-rendered via Zenodo. There is nothing here
to modify to add an indirect-illumination AOV pass — see §B.

---

## Part A — Method

### A1. Deformation model

`scene/deform_model.py` (`DeformModel` wrapper) + `utils/time_utils.py`
(`DeformNetwork`, `StaticNetwork`).

- `DeformModel.__init__` (`scene/deform_model.py:11-18`) selects between
  `{'mlp': DeformNetwork, 'static': StaticNetwork}` (`:8`). `.step()` (`:24-25`)
  forwards `(xyz, time_emb, iteration, **kwargs)` into the network.
- **Architecture**: `DeformNetwork` (`utils/time_utils.py:80-211`) is a plain
  coordinate-MLP, D-NeRF/Deformable-3D-Gaussians style — **no hash grid, no
  attention**. `D=8` hidden layers, `W=256`, skip connection at `D//2`
  (`:90,110-121`), separate positional-encoding embedders for xyz (`multires=10`)
  and time (`t_multires`: 6 for Blender scenes, 10 otherwise, `:89,92-96`). For
  Blender scenes specifically (`is_blender=True`, the flag used for d-nerf-relight),
  time first passes through a small `timenet` (`:106-108`) before concatenation with
  xyz features (`:176-177`) — an explicit dataset-specific architecture switch.
- **Inputs**: canonical position `x` (`pc.get_xyz`) and a per-Gaussian-broadcast
  scalar time `t` (`fid`, in `[0,1]`, one float per frame; `utils/time_utils.py:
  172-179`, called from `scripts/train_stage1.py:116-121` via
  `fid.unsqueeze(0).expand(N,-1)`).
- **Outputs / attributes deformed**: `d_xyz` (position offset,
  `gaussian_warp: Linear(W,3)`, `:125,186`), `d_rotation` (quaternion offset,
  `gaussian_rotation: Linear(W,4)`, `:127,188`). **`d_scaling` is predicted by a head
  but explicitly zeroed at output** (`'d_scaling': scaling*0`, `:192`) — scale never
  actually deforms despite the network computing it. Opacity is not deformed at all
  (`'d_opacity': None`, `:194`). If `pred_color=True`, an extra head
  (`gaussian_color`, `:140-152`) predicts a per-Gaussian "shadow modulation" color
  delta that darkens albedo in shadowed regions (`:196-204`, consumed in
  `gaussian_renderer/render_ir.py:147-148`) — a **learned local shading correction**,
  not physically-traced shadowing.
- **`binary_features` gating**: `d_xyz` and `d_rotation` are elementwise-multiplied
  by `binary_features` (`utils/time_utils.py:190-191`), sourced from
  `GaussianModel.get_binary_feature()` (`scene/gaussian_model.py:179-197`) — an
  unsupervised, temperature-annealed (Gumbel-sigmoid) per-Gaussian static/dynamic
  mask. Static Gaussians get zero deformation regardless of MLP output. This is a
  scene-decomposition mechanism, not temporal coherence.
- `StaticNetwork` (`:58-77`) is a no-op deform module (zero deltas) for ablations.

### A2. Indirect illumination / visibility — real, ray-traced, and actively used

A ray tracer submodule exists: `submodules/surfel_tracer/`
(`from surfel_tracer import GaussianTracer`, `scene/gaussian_model.py:13`), OptiX/BVH
code under `submodules/surfel_tracer/src/optix/`. It is instantiated per model
(`self.gaussian_tracer = GaussianTracer(transmittance_min=0.03)`,
`scene/gaussian_model.py:102`) and **actively invoked in the main training loop**,
not vendored-but-dormant:

- `build_bvh`/`update_bvh` (`scene/gaussian_model.py:624-632`) build a BVH over
  per-Gaussian bounding icosahedra (`get_boundings`, `:610-621`) using the **current
  frame's deformed** `d_xyz`/`d_rotation`/`d_scaling`. Rebuilt once, then `update_bvh`'d
  every subsequent Stage-2 training iteration (`scripts/train_stage2.py:155-159`),
  each iteration against that iteration's sampled frame's deformation — i.e. the
  accel structure tracks deforming geometry per-frame, then is discarded/rebuilt for
  the next (possibly different) sampled frame.
- `GaussianModel.trace()` (`:634-674`) calls `gaussian_tracer.trace(...)` to
  ray-march through the current surfel geometry, returning alpha (occlusion),
  traced normal, traced feature (albedo/roughness or SH color), and depth.
- `gaussian_renderer/render_ir.py:rendering_equation()` (`:435-555`) uses this for
  **both** visibility and one-bounce indirect illumination:
  - Global direct term: `global_incident_lights = envlight(incident_dirs,
    mode='pure_env')` (`:469`).
  - Occlusion: `trace_outputs = pc.trace(...)` (`:482-484` relight path, `:512-514`
    training path); `incident_visibility = 1 - trace_outputs['alpha']`
    (`:487,516`).
  - Indirect (one-bounce): training path uses
    `local_incident_lights = srgb_to_rgb(trace_outputs['color'])` (`:517`) — the
    traced radiance is the **Stage-1-optimized SH color baked per-Gaussian**
    (`shs=sh_features` from `pc._albedo_dc_stage1`, `:148-149,514`), i.e. a
    cached/precomputed-radiance-field approximation to one-bounce GI, not a full
    recursive path trace. The cache itself is per-Gaussian *canonical* state, not
    per-frame-in-time state (see A5).
  - In the `relight=True` path (novel-envmap relighting), indirect light is instead
    recomputed by re-shading the traced hit point's traced albedo/roughness against
    the new environment light (`trace_diffuse`/`trace_specular`, `:500-508`) — the
    correct behavior when only lighting changes.
  - Combination: `incident_lights = incident_visibility * global_incident_lights +
    local_incident_lights` (`:523`); Monte-Carlo integrated:
    `transport = incident_lights * incident_areas * n_d_i`,
    `diffuse = (f_d*transport).mean(-2)`, `specular = (f_s*transport).mean(-2)`
    (`:529-531`), `f_d = base_color/π`, `f_s` from GGX (`GGX_specular`, `:558-591`).
  - Ablation flags: `pipe.wo_indirect`, `pipe.wo_indirect_relight`,
    `pipe.detach_indirect`, `pipe.wo_specular` (`arguments/__init__.py:95-98`).

**Conclusion:** shading is not purely direct BRDF×envmap — there is a genuine
ray-traced visibility term and a one-bounce cached-radiance indirect term, both
routed through an OptiX BVH tracer rebuilt every training iteration against the
deformed geometry of the currently-sampled frame.

### A3. Temporal coherence of illumination — the priority question: none found

Exhaustive grep across the whole tree (excluding vendored
`submodules/2dgs_rasterizer_lumimotion`, `submodules/simple-knn`) for `temporal`,
`smooth`, `consisten`, `previous`, `prev_frame`, `t-1`, `cache`, `ema`, `running`,
`warp`, `flow`, `regulariz`. Every hit, categorized:

1. **Geometry-only regularizers, not illumination**: `d_xyz` L2 regularization
   (`scripts/train_stage1.py:168`) penalizes the *magnitude* of the current single
   frame's deformation offset — not its difference from frame *t*−1.
   `d_color_reg_loss` (`:174-180`) similarly regularizes the shadow-modulation
   delta's magnitude toward zero for the current frame only.
2. **Spatial (not temporal) smoothness losses, misleadingly named "smooth"**:
   `lambda_roughness_smooth`, `lambda_base_color_smooth`
   (`scripts/train_stage2.py:221-224,237-240`) are edge-aware *spatial* gradient
   losses (`first_order_edge_aware_loss`, `utils/loss_utils.py:90-91`) within one
   rendered image — no cross-frame term. `lambda_light_smooth`
   (`scripts/train_stage2.py:232-235`) is a spatial TV loss on the single
   (frame-independent) envmap image, not a temporal one.
3. **"warp"**: only the deformation MLP's output layer name `gaussian_warp`
   (`utils/time_utils.py:125,133,136,186`) — the position-deformation head itself
   (A1), a within-frame canonical-to-pose warp, not a temporal-consistency
   mechanism between frames.
4. **"cache"**: only PyTorch CUDA-extension JIT-compilation caching
   (`scene/renderutils/ops.py:22-27,68,81,83`) and `torch.cuda.empty_cache()` calls
   — unrelated build-system/memory management.
5. **"ema"**: only `self.ema_loss_for_log` (`scripts/train_stage2.py:284`), an
   exponential moving average of the *scalar training-loss value for console
   logging* — not model state, not illumination-related.
6. **Zero hits** for "previous", "prev_frame", "t-1", "running" (as a buffer),
   "flow" (optical flow), or "consisten[cy]" in any shading/rendering/training file.
7. **The environment light is a single global `nn.Parameter`** (`self.base`,
   `scene/light.py:28-31,180-185`) — **one envmap per training run**, not per-frame,
   not indexed by time at all. Optimized once across the whole sequence, used
   identically for every frame's rendering-equation call. There is no per-frame
   light state to be coherent or incoherent with.

**Definitive answer:** illumination is computed completely independently per frame,
per sample. No mechanism — loss term, cached buffer, warping scheme, or EMA — makes
frame *t*'s illumination depend on or be regularized against frame *t*−1 or any
historical state. The only temporal continuity in the codebase is implicit and
geometric: the deformation MLP is continuous in time by construction (an MLP
conditioned on scalar `t`, so nearby times give nearby deformations as a side effect
of network smoothness). There is no illumination analogue of that continuity. **This
is the concrete, exploitable gap for the user's project.**

### A4. Loss terms

**Stage 1** (`scripts/train_stage1.py`, geometry/appearance pretraining, no ray
tracing yet):

| Term | Compares | Constrains |
|---|---|---|
| `Ll1`/`loss_img` (`:149-150`) | rendered RGB vs `original_image_train_light` (D(1−dssim)·L1 + dssim·(1−SSIM)) | photometric fit to training-light GT |
| `normal_loss` (`:132,137-138`) | rasterized normal vs pseudo-surface normal from depth | 2DGS surfel-normal↔depth consistency (standard 2DGS reg, geometry only) |
| `dist_loss` (`:133,139`) | depth-distortion map | encourages thin/flat surfels (standard 2DGS reg) |
| `alpha_loss` (`:154-162`) | rendered alpha vs GT alpha mask | silhouette/mask supervision |
| `d_xyz` L2 (`:168`) | `d_xyz` magnitude vs 0 | penalizes large deformation offsets (single-frame magnitude reg, not temporal) |
| `d_color_reg_loss` (`:174-180`) | shadow-modulation delta magnitude vs 0 | keeps learned per-frame shading correction small |
| binarization L1 (`:185`) | `get_binary_feature()` vs 0 | sparse/confident static-vs-dynamic Gaussian assignment |

**Stage 2** (`scripts/train_stage2.py`, material/envmap training with ray-traced
shading):

| Term | Compares | Constrains |
|---|---|---|
| `Ll1` (`:182-183`) | ray-traced final RGB (or diffuse-only, gated by `iters_only_diffuse`) vs GT, sampled ray subset | photometric fit under the physically-shaded rendering equation |
| `loss_sh` (`:196-200`) | Stage-1 SH-color render vs GT (L1+SSIM) | keeps the Stage-1 radiance-cache SH bank matched to GT (this is what supplies the indirect-light cache queried by `pc.trace(..., shs=...)`) |
| `loss_env_lowerhem` (`:203-217`) | squared magnitude of envmap texels in the lower ~1/3 of the latlong map | discourages spurious bright light "below the horizon" (single global envmap, no time dependence) |
| `loss_roughness_smooth` (`:221-224`, default weight 0) | spatial gradient of rendered roughness vs edge-aware GT-derived weight | single-frame spatial roughness smoothness |
| `loss_light` (`:226-230`, default weight 0) | per-ray direct light vs its own per-ray mean | discourages high-frequency/noisy direct-light estimate (single frame) |
| `loss_light_smooth` (`:232-235`, default weight 0) | TV loss on rendered envmap | spatial (not temporal) envmap smoothness |
| `loss_base_color_smooth` (`:237-240`, default weight 0) | spatial gradient of rendered base color vs edge-aware GT weight | single-frame spatial albedo smoothness |

All the weight-0-by-default Stage-2 terms are inherited from IRGS per the readme's
acknowledgements, explicitly commented `##IRGS losses for tests:`
(`scripts/train_stage2.py:220`) — none, active or not, are temporal.

### A5. Per-Gaussian state

`GaussianModel` (`scene/gaussian_model.py:43-107`):

- `_xyz` — canonical position; per-frame position = `_xyz + d_xyz`.
- `_albedo_dc`, `_albedo_rest` — canonical SH albedo/color (frame-independent); the
  shadow-modulation `d_color` modulates `_albedo_dc_stage1` per-frame at render time
  (`render_ir.py:147-148`) but never overwrites the stored canonical parameter.
- `_albedo_dc_stage1` — a **second, frozen-ish copy** of the Stage-1-trained
  albedo/color SH, used specifically as the radiance-cache color queried by the ray
  tracer for indirect light; canonical, not per-frame.
- `_roughness`, `_opacity`, `_scaling`, `_rotation` — canonical base
  material/geometry; per-frame = `get_scaling + d_scaling` (though `d_scaling` is
  forced zero, A1) and `get_rotation_bias(d_rotation)`; opacity is never deformed.
- `feature` — canonical per-Gaussian logits for the unsupervised static/dynamic
  binary split.
- `max_radii2D`, `xyz_gradient_accum`, `denom` — canonical, densification
  bookkeeping only (not illumination-related; persist/accumulate across iterations
  purely to drive densify/prune, resetting at `densification_interval`).
- `gaussian_tracer` (the BVH) — rebuilt **every iteration** from that iteration's
  deformed geometry; recomputed fresh per call, not a persistent cross-frame cache.
- `FG_LUT` — static precomputed BRDF LUT (`assets/bsdf_256_256.bin`, `:103-104`),
  constant, not per-Gaussian, not per-frame.

**No buffer of any kind — illumination or otherwise — persists across training
iterations in a way that ties frame *t*'s state to frame *t*−1's.** The only
cross-iteration persistence is the standard densification-statistics accumulators
(reset periodically) and the model parameters themselves, which are canonical/
frame-independent by construction — deformation and shading are recomputed fully
from scratch, from canonical parameters plus the current sampled frame's time value,
on every forward pass.

---

## Part B — Data pipeline

**No Blender/bpy code exists anywhere in this repo.** Confirmed:
- `grep -rl "bpy"` over the entire tree → zero hits.
- `find . -iname "*.blend*"` → zero hits.
- `readme.md:69-70`: *"Our synthetic dataset is available at:
  https://zenodo.org/records/18894615. We cannot share ENeRF and DNA data due to
  signed agreements, but we provide exact instructions how to access and preprocess
  used scenes. Please refer to `notebooks` folder."* — the synthetic (d-nerf-relight)
  dataset ships as **pre-rendered images from Zenodo**, not generated by code in this
  repo. No compositor-node setup, no `view_layer.use_pass_*` flags, no
  camera-trajectory generator, no envmap-swap script exists here — whatever produced
  the Zenodo archive is not published in this reference copy.
- `notebooks/` (`enerf_prepare_colmap_from_scratch.ipynb`,
  `enerf_use_our_colmap.ipynb`, `dna_prepare_visualise_data.ipynb`,
  `colmap_database.py`) covers only the ENeRF (real, COLMAP-based) and DNA-Rendering
  (real, SMC-format) preprocessing — neither Blender-related; these are for the two
  real-capture families, not the synthetic one.

**Conclusion**: there is nothing in this repo to modify for adding an
indirect-diffuse/glossy Cycles AOV — no render engine choice, no pass configuration,
no spp setting, no camera-trajectory generator exists here to inspect or extend. To
re-render these scenes with additional passes, the options are: (a) reconstruct a
Blender generator from scratch, starting from the original D-NeRF Blender
scripts/generator (a separate, well-known public repo — the
`camera_angle_x`/`transform_matrix`/orbit-JSON schema here is D-NeRF-derived, so a
D-NeRF-compatible generator is the natural starting point), or (b) contact the
LumiMotion authors for their internal renderer, since it is not published here.

---

## Part C — Dataset structure (`hook150_v5_spec32`)

Top level of
`data/dnerf-relight/d-nerf-relight-spec32/hook150_v5_spec32/`:

```
albedo/                                150 PNGs (RGBA, 800×800)
depth/                                 150 PNGs (RGBA, 800×800 — depth encoded into an RGBA PNG, not raw/EXR)
dynamic_mask/                          151 PNGs (mask_0001..) — one more than the 150 image frames (see below)
chapel_day_4k_32x16_rot0/              150 PNGs (800×800) + chapel_day_4k_32x16_rot0.hdr (32×16 Radiance HDR)
dam_wall_4k_32x16_rot90/               150 PNGs (800×800) + dam_wall_4k_32x16_rot90.hdr (32×16)
golden_bay_4k_32x16_rot330/            150 PNGs (800×800) + golden_bay_4k_32x16_rot330.hdr (32×16)
small_harbour_sunset_4k_32x16_rot270/  150 PNGs (800×800) + small_harbour_sunset_4k_32x16_rot270.hdr (32×16)
config.json                            {"train_light": "chapel_day_4k_32x16_rot0", "test_light": "golden_bay_4k_32x16_rot330"}
transforms_train.json                  135 frame entries
transforms_test.json                   15 frame entries
points3d.ply                           initial point cloud
```

- **The four envmap directories** each hold 150 renders of the scene *under that
  specific low-res (32×16) HDR envmap* — per-frame GT renders under 4 fixed lighting
  conditions (the envmap images themselves are the sibling 32×16 `.hdr` files).
  `config.json` designates the training-supervision lighting
  (`chapel_day_4k_32x16_rot0`) and the held-out relighting-target lighting
  (`golden_bay_4k_32x16_rot330`) — matching `train_light_folder`/`test_light_folder`
  CLI args in `bash_scripts/synthetic_results_from_paper.sh`.
- **`albedo/`, `depth/`**: per-frame GT material/geometry buffers (150 each), used
  by `scripts/eval_material_*.py` / `scripts/scale_albedo_*.py`.
- **`dynamic_mask/`**: 151 files (`mask_0001.png`..), one more than the 150 frames —
  likely an extra reference/canonical-pose mask alongside the 150 per-frame masks;
  **not fully resolved from filenames alone**, flagged uncertain — worth checking
  against `scripts/eval_*` code if this exact count matters.

**`transforms_train.json`/`transforms_test.json` schema**: top-level
`camera_angle_x` (single scalar FOV shared across all frames) + `frames` (list).
Per-frame entry:
```json
{"file_path": "r_0001", "rotation": <float>, "transform_matrix": <4x4 nested list, camera-to-world>, "time": <float in [0,1]>}
```
This is the exact D-NeRF JSON schema plus an added `"time"` field — LumiMotion's own
reader (`LumiMotion_ref/scene/dataset_readers.py:170-173`) treats `"time"` as
optional, falling back to `idx/len(frames)` if absent. 135 train + 15 test = 150
total frames/timesteps, **one unique camera pose per timestep** — a single,
continuously-moving/orbiting camera visits each timestep once (classic D-NeRF setup,
not multi-view-per-timestep). `time` values evenly spaced in `[1/150, 1.0]`,
increment `0.00667` (=1/150).

Image format: PNG, RGBA, 800×800 confirmed across all image types (lighting
renders, albedo, depth-as-PNG, dynamic_mask). No resolution field in `config.json` —
inferred from the images themselves.

### Mapping to RadioGS's `CameraInfo`

RadioGS's `CameraInfo` (`scene/dataset_readers.py:32-44` in the RadioGS root, per
`docs/code_audit_final.md` §8): `uid, R, T, K, FovY, FovX, image, mask, image_path,
image_name, width, height` — **no frame_id/time field**.

| LumiMotion JSON/file | RadioGS `CameraInfo` field | Notes |
|---|---|---|
| `transform_matrix` (inverted/sign-flipped per LumiMotion's own conversion) | `R`, `T` | direct reuse of the conversion logic |
| `camera_angle_x` + image size | `FovX`, `FovY` | direct reuse (`focal2fov`/`fov2focal`) |
| — | `K` | **no LumiMotion equivalent** (no principal point given; D-NeRF assumes centered pinhole) — must be synthesized as a centered-pinhole matrix from `camera_angle_x` + resolution |
| `<train_light>/r_XXXX.png` or `<test_light>/...` | `image` | which of the 4 envmap folders to read is selected by `config.json` — **no RadioGS equivalent**; RadioGS's reader has no "which lighting variant" concept |
| RGBA alpha channel | `mask` | direct reuse, same convention as RadioGS |
| path / stem | `image_path`, `image_name` | direct reuse |
| image dimensions | `width`, `height` | direct reuse |
| `frame["time"]` | **no equivalent — new field needed** | the critical addition. RadioGS has nothing analogous to LumiMotion's `fid` (`LumiMotion_ref/scene/cameras.py:22,46`: `self.fid = torch.Tensor([fid])`, consumed by the deform MLP at `scripts/train_stage1.py:103,117`) |

**Fields with no RadioGS equivalent, requiring new `CameraInfo` fields or a parallel
loading path** (concrete, matches and extends `docs/code_audit_final.md` §8.3's
generic `frame_id` plan with this dataset's specifics):
1. **Frame/time index** (`fid`/`time`) — needed for any dynamic-scene support;
   new `CameraInfo.fid: float` (or `frame_id: int`) threaded to a new `Camera.fid`,
   exactly mirroring LumiMotion's own field.
2. **Envmap/lighting-condition selection** — RadioGS has no multi-lighting-variant
   concept; needs either a new `CameraInfo.light_id`/`envmap_path` field plus
   reading `config.json`, or a parallel reader function analogous to LumiMotion's
   `readCamerasFromTransforms(..., train_light, ...)`
   (`LumiMotion_ref/scene/dataset_readers.py:156-211`), parameterized by which
   lighting subfolder to read.
3. **Albedo/depth/dynamic-mask GT** — used only by evaluation scripts, not core
   `CameraInfo`, in *either* codebase: LumiMotion's own `CameraInfo`
   (`LumiMotion_ref/scene/dataset_readers.py:36-51`) likewise omits these paths —
   they're read separately by eval scripts. This is a reusable design pattern to
   copy into RadioGS (extra optional fields or a separate eval-only loading path),
   not something RadioGS is uniquely missing relative to LumiMotion.
4. **Multi-envmap directory structure** — RadioGS's reader function signature and
   layout assumptions (single `images`/`masks` folder) would need to become
   light-condition-aware (an extra path-join parameter), matching LumiMotion's
   `train_light_folder`/`test_light_folder` args threaded from CLI parsing into
   `readCamerasFromTransforms`.

---

## Part D — Static variants

Directly confirmed via file naming and JSON inspection — **the static variants are
the SAME scene geometry frozen at one single timestep, with the camera still
sweeping through all 150 view slots** (many camera views of one static pose), **not**
a different scene/setup:

- **Naming proof**: dynamic `hook150_v5_spec32/albedo/` files are
  `r_{XXXX}{XXXX}.png` where both index groups are identical and increment together
  (`r_00010001.png`, `r_00500050.png`, `r_01000100.png`) — camera-frame-index ==
  geometry-timestep-index, i.e. camera and pose both advance together. The static
  variant `hook150_v5_spec32_statictimestep1/albedo/` has
  `r_{XXXX}0001.png` for all 150 entries — the **second index frozen at `0001`**
  while the camera-view index still runs `0001..0150`. Spot-checked
  `jumpingjacks150_v5_spec32_statictimestep75`: second index frozen at `0075`
  (`r_00010075.png`, `r_00500075.png`, `r_01000075.png`) — confirming
  `..._statictimestepN` literally means "geometry frozen at timestep N, camera swept
  across all 150 views."
- **Important, non-obvious caveat**: `transforms_train.json`'s `"time"` field still
  varies in the static variant (135 distinct values spanning `[0,1]`, same
  distribution as the dynamic scene) — `time` tracks the *camera-view index*, still
  labeled as if it were a moving-camera dynamic sequence, **not** the frozen
  geometry timestep. Loading this variant through LumiMotion's own reader unmodified
  would still vary the deform-MLP's `fid` input per view, even though the rendered
  images are all of the identical frozen pose. Anyone using the static variant as a
  control must not assume `time` ≈ actual pose-time — the geometry itself is
  constant across all entries regardless of what `time` says.
- **Directory differences**: the static variant drops `dynamic_mask/` (no motion to
  mask) and adds a `roughness/` GT folder (300 files — double the 150 frame count,
  likely two roughness-related purposes; **not fully resolved from filenames alone**,
  flagged uncertain). `albedo/`/`depth/` counts (150 each) and the 4 envmap-lighting
  folders (150 each) are structurally identical between variants.
- **Frame count**: identical 150 total (135 train + 15 test) in both — the static
  variant doesn't reduce file count, it re-renders the same 150 camera positions
  against one frozen pose instead of 150 evolving poses.

---

## Contribution and limitations (for related-work use)

**What LumiMotion solves**: extends physically-based relightable Gaussian-splatting
reconstruction (in the IRGS/Relightable3DGaussian lineage — ray-traced visibility +
one-bounce indirect illumination via a BVH-based OptiX surfel tracer, BRDF material
decomposition into albedo/roughness, an optimizable HDR environment map) to
**deforming/dynamic scenes**, by adding a canonical-space, time-conditioned
coordinate-MLP deformation field (D-NeRF/Deformable-3D-GS style: MLP(canonical xyz,
embedded time) → position + rotation offset) on top of a 2D-Gaussian-surfel (2DGS)
representation, plus an unsupervised per-Gaussian static/dynamic binary decomposition
to avoid deforming genuinely static/rigid background parts. It also contributes a
new synthetic benchmark (`d-nerf-relight-spec32`: D-NeRF-style scenes rendered under
multiple environment maps with albedo/depth/dynamic-mask GT for material evaluation)
and demonstrates relighting of deforming objects under both trained and held-out
(novel) environment lighting, evaluated on synthetic D-NeRF-relight scenes, real
ENeRF actor captures, and DNA-Rendering human captures.

**What it explicitly does not do** (all determined by code absence in this pass — no
README limitations section was found stating these; treat as audit findings, not
author-stated limitations):
1. **No temporal coherence of illumination/shading whatsoever** (§A3) — every
   frame's visibility, indirect light, direct light, and full shading equation is
   recomputed completely independently; the BVH is rebuilt from scratch every
   training iteration for the currently-sampled frame and is not a persistent
   cross-frame cache; no loss term, EMA, or warping scheme ties frame *t*'s shading
   to any historical state. **The single largest gap relative to what the user's
   project needs to add.**
2. **Global environment light only** — one envmap parameter optimized across the
   whole sequence, applied identically to every frame; no support for
   time-varying/animated lighting within a sequence.
3. **Indirect illumination is a one-bounce approximation from a Stage-1-baked SH
   radiance cache** (`_albedo_dc_stage1`), not a full recursive/multi-bounce path
   tracer — canonical (frame-independent) per-Gaussian data, re-queried via ray
   tracing against the current frame's deformed BVH; not re-derived or
   re-consistency-checked per frame beyond the geometry motion itself.
4. **`d_scaling` is predicted but explicitly zeroed at output**
   (`utils/time_utils.py:192`) — per-Gaussian scale never actually deforms over
   time despite the network head existing; opacity is likewise never deformed.
5. **No Blender/dataset-generation code published** — the synthetic dataset ships
   pre-rendered via Zenodo; reproducing or extending it (e.g. adding
   indirect-diffuse/glossy AOVs) cannot be done from anything in this repo (§B).
6. Released synthetic-benchmark camera trajectories use one moving camera visiting
   each timestep once (D-NeRF convention), not multi-view-per-timestep — limits
   per-timestep supervision density for the synthetic benchmark specifically (the
   ENeRF/DNA real-capture branches do support genuine multi-view-per-timestep, per
   `LumiMotion_ref/scene/dataset_readers.py:298-478`,
   `readColmapEnerfSceneInfo`/`readCamerasDNARendering`).

---

## Uncertainty flags

- `dynamic_mask/`'s 151-vs-150 file count and the static variant's 300-file
  `roughness/` folder are both noted but not fully resolved from filenames alone —
  would need a check against `LumiMotion_ref/scripts/eval_*.py` for exact semantics
  if precision on these specific counts matters.
- No README limitations section was found; the "does not do" list in the final
  section is derived entirely from code absence in this pass, not author statements
  — a fair characterization for a related-work section, but worth noting the
  authors haven't explicitly claimed these as limitations themselves.
