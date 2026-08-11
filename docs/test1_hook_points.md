# Instrumentation Hook Points for Test 1

Read-only trace, no modifications made. Builds directly on `docs/lumimotion_eval.md`
(method/audit) and `docs/lumimotion_repro.md` (validated baseline run) — their
findings (no temporal coherence anywhere, `render_ir.py` shading path, per-Gaussian
canonical state in `GaussianModel`, `hook150` being a weak scene for occlusion) are
taken as given and not re-derived here. All citations are `file:line` against the
repo root (what the eval doc calls `LumiMotion_ref/`).

## Corrections / additions to the prior docs

These aren't contradictions of anything the eval doc claimed, but they're new
findings the eval doc didn't need for its question and this task does:

1. **The two "already loop over 150 frames" scripts don't actually give you 150
   frames with real per-frame cameras.** `scripts/render_stage1_insights.py` and
   `scripts/render_materials.py` loop over `scene.all_timesteps` (150 unique `fid`
   values) but hold **one single camera fixed** across all of them
   (`cameras = scene.getTestCameras()[:1]`, then the fid loop reuses that one `view`
   for every timestep — `render_stage1_insights.py:52,80`,
   `render_materials.py:50,70`). That's a "bullet-time" render (camera frozen, scene
   animates), not the dataset's actual 150-frame sequence (which is one camera pose
   *per* timestep, per the eval doc's Part C). For a true per-frame dump you want the
   camera that actually goes with each `fid`, not a fixed one.
2. **The only script that pairs each frame with its own camera and its own `fid`
   loops over just 15 cameras, not 150** — `scripts/eval_nvs_dynamic.py:71`
   (`cameras = scene.getTestCameras()`), because `dataset.eval` is left governing the
   split. See §1 "which script" below for how to get all 150 without editing the
   camera-reading code.
3. **New finding, not in the eval doc: the eval-time ray tracer's BVH is built once
   and never rebuilt across the frame loop**, in both `eval_nvs_dynamic.py` and
   `eval_relight_dynamic.py`:
   ```
   build_bvh = True
   for render_idx, view in enumerate(...):
       ...
       if build_bvh:
           gaussians.build_bvh(d_rotation=d_rotation, d_xyz=d_xyz, d_scaling=d_scaling)
           build_bvh = False
       render_pkg_relight = render_ir(...)   # uses gaussians.gaussian_tracer internally
   ```
   (`eval_nvs_dynamic.py:69,86-88`; `eval_relight_dynamic.py:80,97-99` — same
   pattern). Contrast with training (`train_stage2.py:155-159`): `build_bvh` once,
   then `update_bvh` **every iteration** against that iteration's sampled frame. In
   eval, the BVH is frozen at frame 0's deformed geometry for the rest of the
   sequence. `pc.trace()` (called inside `rendering_equation()`,
   `render_ir.py:482,512`) queries `self.gaussian_tracer`, which holds whatever
   geometry was last built/updated (`gaussian_model.py:624-632`) — **not** whatever
   `xyz`/`scales`/`rotation` you pass into `trace()` for shading. Passing the current
   frame's deformed `xyz`/`scales`/`rotation` into `trace()` only affects the
   returned normals/color-space math (`gaussian_model.py:648-658`); the actual
   ray-triangle intersection happens against the possibly-stale BVH. **This means: if
   you dump `L_ind` (or per-Gaussian visibility) for frames 1-149 by running
   `eval_nvs_dynamic.py`/`eval_relight_dynamic.py` unmodified, every frame after
   frame 0 will report visibility/indirect-light computed against frame 0's pose**,
   not that frame's actual deformed pose. Any instrumentation script for this task
   must call `gaussians.update_bvh(d_rotation, d_xyz, d_scaling)` (or `build_bvh`)
   every frame, before calling `render_ir`/`pc.trace()`. This is likely also worth
   flagging as a correctness bug in the reference eval numbers for dynamic scenes
   generally (NVS/relight dynamic eval currently effectively evaluates against a
   frozen BVH), independent of Test 1.
4. Confirmed detail the eval doc didn't need: the deform MLP's `forward()`
   (`utils/time_utils.py:172-179`) takes `camera_center` only via `**kwargs` and
   **never uses it** — `d_xyz`/`d_rotation`/`d_scaling` are a pure function of
   canonical `xyz` and `fid`, with no camera dependence at all. This is what makes a
   camera-free standalone script for Q3 possible.

---

## (1) Dumping `L_ind` (`local_incident_lights`, `render_ir.py:517`)

### Shape / dtype / space
- Computed inside `rendering_equation()` (`render_ir.py:435-555`), specifically the
  `else` branch (`relight=False`) at `:510-517`.
- Shape: `(P, S, 3)` where `P` = number of **masked pixels** entering
  `rendering_equation` for this call (from `render_ir.py:280-297`: for `training=True`
  a random ray-subset of `render_alpha>0` pixels gated by `opt.train_ray`; for
  `training=False`, i.e. eval, **all** pixels with `render_alpha[0] > 0`, chunked
  through `rendering_equation_chunk` at `chunk_size=2**20 // (diffuse_sample_num +
  light_sample_num)` — `render_ir.py:404-410`), and `S` = `pipe.diffuse_sample_num`
  (512 per the repro doc's config; `sample_incident_rays`, `utils/relight_utils.py:
  36-44`, confirms output shape `[N, S, 3]`).
- dtype: `torch.float32`, CUDA.
- Color space: **linear RGB**. It's `srgb_to_rgb(trace_outputs['color'])` — the raw
  traced value is the Stage-1-optimized SH-decoded color (itself trained/stored as if
  sRGB, per the eval doc §A2), converted to linear here before use in the rendering
  equation.
- Per-pixel or per-sampled-ray: **per-sampled-ray**, i.e. it has the hemisphere-sample
  axis (`S`) still intact. It has *not yet* been reduced. The only place a
  per-pixel version is exposed externally is `results["light_indirect"]`
  (`render_ir.py:391`, only populated when `training=False`), which is
  `local_incident_lights.mean(dim=1)` (`render_ir.py:552` inside `rendering_equation`,
  `"light_indirect": local_incident_lights.mean(dim=1)`), then srgb-re-encoded
  (`rgb_to_srgb`) and scattered back from the `P`-length masked list into the full
  `(3,H,W)` image raster (`render_ir.py:376-378`) and multiplied by `render_alpha`.
  If you only need the per-pixel, sample-averaged, sRGB, full-image version, that
  already exists at `results["light_indirect"]` for free from any `training=False`
  call with `relight=False` — no new code needed. If you need the raw
  per-sampled-ray, linear-space, un-scattered tensor (i.e. exactly the `(P,S,3)`
  value at line 517), you need to intercept inside `rendering_equation`, see below.

### Relation to the final image
`local_incident_lights` is one additive term of `incident_lights` (`:523`), which
feeds `transport = incident_lights * incident_areas * n_d_i` (`:529`), which is
Monte-Carlo-averaged over the `S` samples into `diffuse`/`specular` (`:530-531`),
which become `rendered_diffuse`/`rendered_specular` → `rendered_full` →
`final_image` (`render_ir.py:303-311`) — several linear→sRGB and masking steps removed
from the actual displayed/supervised image. It is a genuine intermediate, not a
renamed final output.

### Where to intercept
`rendering_equation` is a **plain module-level function**, not an `nn.Module`, so
there's no forward-hook mechanism. Two options, in order of preference:

- **(A) Recommended — additive return-dict field.** Add one line inside
  `rendering_equation` (both the `training` and non-`training` result dicts,
  `render_ir.py:537-544` and `:546-554`) exposing the raw tensor, e.g.
  `"light_indirect_raw": local_incident_lights`. This changes zero existing tensors
  or control flow — purely additive to the returned dict — so it doesn't alter any
  numerical output anywhere else in the codebase; every existing caller that doesn't
  ask for the new key is unaffected. This is the cleanest true "instrumentation point"
  because it's one line, at the exact place the value already exists, with no
  duplicated computation.
- **(B) Fully zero-modification alternative** (if even an additive line is
  undesirable): install a `sys.settrace`/`sys.setprofile` local-variable snapshot
  keyed on `rendering_equation`'s code object, reading
  `frame.f_locals['local_incident_lights']` on a `'return'` event. This requires no
  edits to `render_ir.py` at all, at the cost of being a slower, less standard
  technique confined to the analysis script. Only worth it if "no modifications to
  the training/render code, ever" is a hard constraint; otherwise (A) is simpler and
  safer.
- Reconstructing `local_incident_lights` by re-deriving it outside
  `rendering_equation` (calling `pc.trace()` yourself with the same args) is **not**
  clean: it requires exactly reproducing the masked pixel positions/normals/roughness
  that `render_ir()` computes internally (`render_ir.py:216-297`), which is
  substantial duplicated logic prone to drifting out of sync with the real code path.
  Prefer (A) or (B).

### Script to run for all 150 frames
None of the existing scripts do this out of the box; the closest is
`scripts/eval_nvs_dynamic.py`, which already has the right per-frame structure
(loads `deform`, builds `gaussians`, loops cameras, computes `d_xyz`/`d_rotation`
from each camera's own `.fid`, calls `render_ir(..., relight=False, training=False)`
— the exact branch that computes `local_incident_lights`) but:
- loops `scene.getTestCameras()` (`eval_nvs_dynamic.py:71`) = **15** frames, not 150.
  Fix: since the script already sets `dataset.eval = False`
  (`eval_nvs_dynamic.py:33`, with the comment "gather all possible cameras"), and
  `readNerfSyntheticInfo` does `if not eval: train_cam_infos.extend(test_cam_infos)`
  (`scene/dataset_readers.py:229-230`), `scene.getTrainCameras()` under that flag
  already contains all 150 cameras in file order (`readCamerasFromTransforms` sorts
  frames by the numeric filename suffix at `dataset_readers.py:164`, so index order
  is frame order 0001..0150). Loop `scene.getTrainCameras()` instead of
  `getTestCameras()` to get all 150 real per-frame cameras with their own `fid`.
- has the frozen-BVH bug from finding (3) above — needs `update_bvh` called every
  iteration, not `build_bvh` once.
- doesn't currently expose `local_incident_lights` itself (only the reduced
  `light_indirect`) — needs the (A)/(B) hook above if the raw per-sample tensor is
  required.

So: **yes, a script with the right frame-loop skeleton already exists
(`eval_nvs_dynamic.py`)**, but as-shipped it (a) only visits 15 of 150 frames, (b)
reuses a stale BVH after frame 0, and (c) doesn't surface the raw tensor you want —
three small, independent, well-localized changes on top of an otherwise-correct
per-frame loop, not a rewrite.

---

## (2) Per-Gaussian outgoing radiance at frame *t*

Confirming the eval doc's framing: Stage-2 shading in `render_ir.py` is computed
*after* rasterization, over masked **pixels** (each pixel already a blend of
possibly-multiple overlapping Gaussians via alpha compositing), not per-surfel. None
of `base_color`, `roughness`, `normal_map`, `position`, `w_o` passed into
`rendering_equation` (`render_ir.py:281-288`) are per-Gaussian tensors — they're all
`(pixels, ...)`-shaped, post-rasterizer. So a genuinely per-Gaussian version requires
calling the same physics (`pc.trace()` + BRDF weighting) with per-Gaussian inputs
instead, not extracting anything from the existing pixel-space call.

### What already exists as per-Gaussian tensors (no computation needed)
- **Albedo**: `pc.get_albedo` (`gaussian_model.py:167-169`) — sRGB,
  `clamp(SH2RGB(_albedo_dc), 0.03, 0.97)`. Canonical/frame-independent (confirmed by
  eval doc §A5: albedo is never deformed). Convert to linear via `srgb_to_rgb` before
  using in a diffuse BRDF term, exactly as `render_ir.py:100` does.
- **Roughness**: `pc.get_rough` (`gaussian_model.py:159-161`) —
  `sigmoid(_roughness)`. Also canonical/frame-independent, same reasoning.
- Neither needs the frame index at all — they're the same tensor for every `t`.

### What needs computing per-frame
- **Deformed normal**: not stored anywhere as a tensor; it's only ever computed
  transiently inside `pc.trace()` (`gaussian_model.py:648-658`) from whatever
  `xyz`/`scales`/`rotation` you pass in. To get it standalone: build the rotation
  matrix from the *deformed* quaternion
  (`gaussians.get_rotation_bias(d_rotation)` — normalizes `_rotation + d_rotation`,
  `gaussian_model.py:151-153`) via `utils.general_utils.build_rotation`, then take
  its **third column** (`R[:, :, 2]`) — this is exactly what `trace()` does
  internally: `splat2world = self.get_covariance(...)`, `normals_raw =
  splat2world[:, 2, :3]` (`gaussian_model.py:652-653`), which reduces to the
  rotation's z-axis because the 2DGS surfel's third scale component is hardcoded to
  `1` in `build_covariance_from_scaling_rotation`
  (`gaussian_model.py:47`: `torch.ones_like(scaling)` padding) and
  `build_scaling_rotation` only reads `s[:,0], s[:,1], s[:,2]`
  (`utils/general_utils.py:169-178`) — so scale never actually enters the normal
  direction, only rotation does. **Design decision needed, not resolvable from code
  alone**: `trace()` optionally flips this normal to face a `camera_center`
  (`flip_align_view`, `gaussian_model.py:654-656`) — i.e. the "normal" used
  everywhere else in this codebase is view-dependently sign-resolved, because a 2D
  Gaussian disk has no intrinsic front/back. A per-Gaussian, camera-independent
  outgoing-radiance dump needs its own convention for which side is "outward" (e.g.
  flip away from a scene-center heuristic, or simply carry the ambiguity and report
  unsigned/two-sided values) — `camera_center=None` in `trace()` skips the flip
  entirely (`gaussian_model.py:654`: `if camera_center is not None:`), so this is a
  parameter you control, not a hidden default to fight.
- **Visibility toward the environment**: needs a `pc.trace()` call with **origins at
  the deformed Gaussian centers** and **directions hemisphere-sampled around the
  per-Gaussian deformed normal** — see next section for exact inputs. Not available
  anywhere as a stored tensor; the only existing visibility computation
  (`incident_visibility = 1 - trace_outputs['alpha']`, `render_ir.py:487,516`) is
  per-pixel, driven by rasterized surface points, and is discarded after
  `rendering_equation` returns except for the pixel-space `results["visibility"]`.
- **Outgoing radiance**: needs the same BRDF combination as
  `rendering_equation` (`render_ir.py:523-531`), but with per-Gaussian
  `base_color`/`roughness`/`normal` and the per-Gaussian trace outputs above.
  **Second design decision**: `f_s` (`GGX_specular`, `render_ir.py:558-591`) needs an
  outgoing/view direction `viewdirs` — meaningful for a rasterized pixel (camera
  ray), not intrinsically defined for a surfel in isolation. Options: (i) diffuse-only
  exitant radiance (Lambertian, view-independent — skip specular entirely, matches
  what "outgoing radiance under the optimized envmap" most naturally means for a
  BRDF decomposition dump), or (ii) pick a specific `w_o` per Gaussian (e.g. toward
  that frame's training camera, if there is a canonical one, or straight along the
  normal as a proxy for "viewed head-on"). This isn't answerable from the code —
  it's a modeling choice for what "outgoing radiance" should mean here.

### What `pc.trace()` needs for per-surfel (not per-pixel) visibility
Signature: `trace(self, rays_o, rays_d, features=None, camera_center=None, xyz=None, scales=None, rotation=None, opacity=None, back_culling=False, shs=None, use_zeros=False)`
(`gaussian_model.py:634-636`). The pixel-space call in `rendering_equation`
(`render_ir.py:512-514`) passes:
```
rays_o = position.unsqueeze(1) + incident_dirs * pipe.light_t_min   # (P,S,3): per-pixel surface point
rays_d = incident_dirs                                              # (P,S,3): hemisphere samples per pixel
xyz, scales, rotation, opacity = <the whole deformed Gaussian cloud>  # (N,...): scene geometry for the tracer, same regardless of query count
shs = sh_features   # (N, sh_coeffs, 3): per-Gaussian, used by the tracer for whatever surfel a ray hits
```
The **scene-geometry args** (`xyz`, `scales`, `rotation`, `opacity`, `shs`) are
already per-Gaussian and full-length (`N` = Gaussian count) — you don't change these
for a per-surfel query, you reuse exactly what you'd pass for a pixel-space call:
`means3D = pc.get_xyz + d_xyz`, `scales = pc.get_scaling + d_scaling`,
`rotation = pc.get_rotation_bias(d_rotation)`, `opacity = pc.get_opacity` (or `+
d_opacity`, always `None` per the eval doc). The only thing that changes for
per-surfel visibility is the **query** args: `rays_o`/`rays_d`, which for per-Gaussian
queries should be `(N, S, 3)` — origin at each Gaussian's own deformed center
(`means3D.unsqueeze(1) + normal_dirs * pipe.light_t_min`, using the small offset the
existing code already uses to avoid self-intersection) and directions from
`sample_incident_rays(deformed_normals, training=False, pipe.diffuse_sample_num)`
where `deformed_normals` is the per-Gaussian normal computed above — instead of
`(P, S, 3)` driven by rasterized pixel positions/normals. `camera_center` should
probably be `None` here (no view-dependent flip for an intrinsic per-surfel quantity)
given the normal-orientation decision above. **Also required, per finding (3)**: the
BVH (`self.gaussian_tracer`) must be built/updated for frame *t*'s deformed geometry
(`gaussians.update_bvh(d_rotation, d_xyz, d_scaling)`) before this call — same
requirement as Q1.

### Cleanest place to add this
Not inside `render_ir.py`/`rendering_equation` at all — those are pixel-space by
construction (rasterizer output in, BRDF-shaded pixels out) and retrofitting a
per-Gaussian path into them would mean threading a `per_gaussian` flag through
rasterizer-shaped code that doesn't need a rasterizer. Cleanest is a **new, standalone
function** (own module, e.g. alongside the analysis script) that:
1. calls `deform.step(...)` for the frame's `fid` (see Q3) to get `d_xyz`,
   `d_rotation`, `d_scaling`,
2. builds/updates the BVH for that frame,
3. computes the deformed normal per-Gaussian (small snippet, ~4 lines, mirroring
   `gaussian_model.py:648-656`),
4. calls `sample_incident_rays` + `pc.trace()` directly with the per-Gaussian
   origins/directions described above,
5. combines `envlight(...)`, `trace_outputs`, albedo, roughness into
   diffuse(+specular) using the same formulas as `rendering_equation`
   (`render_ir.py:523-531`), reusing `GGX_specular` (`render_ir.py:558-591`) only if
   you decide specular is in scope.
This reuses every piece of existing machinery (`GaussianTracer`, `EnvLight`,
`GGX_specular`, `sample_incident_rays`) without touching or duplicating
`render_ir.py`'s pixel-space control flow — it's a sibling code path at the same
level of abstraction as `rendering_equation`, just with Gaussian centers as the query
points instead of rasterized pixels.

---

## (3) Deformed per-Gaussian state for a given frame, outside the training loop

This is already exactly what `render_stage1_insights.py` and `render_materials.py`
do inside their frame loops (`render_stage1_insights.py:82-89`,
`render_materials.py:72-79`), minus the rendering call — and per finding (4) above,
it needs **no camera at all**, since `DeformNetwork.forward` never reads
`camera_center` from its `**kwargs`. Standalone recipe:

1. `gaussians = GaussianModel(sh_degree, no_binary_separation=..., fea_dim=...)`;
   `scene = Scene(dataset, gaussians, load_iteration=<ckpt>)` — loads canonical
   `_xyz`, `_rotation`, `_scaling`, `feature`, etc. from the saved `.ply`
   (`scene/gaussian_model.py:353-422`, invoked via `Scene.__init__`,
   `scene/__init__.py:87-93`).
2. `deform = DeformModel(deform_type=dataset.deform_type, is_blender=dataset.is_blender, hyper_dim=dataset.hyper_dim, pred_color=dataset.pred_color)`;
   `deform.load_weights(dataset.model_path, iteration=<ckpt>)`
   (`scene/deform_model.py:43-53`).
3. Get the target `fid` as a scalar CUDA tensor. Two equivalent sources:
   - `scene.all_timesteps` (`scene/__init__.py:99-104`): a `{fid_tensor: idx}` dict
     built from the sorted unique `fid` values across train+test cameras — `idx` here
     is a fid-sort-order index, 0-149, not necessarily tied to a specific camera
     object.
   - A specific camera's own `.fid` (`scene/cameras.py:46`,
     `self.fid = torch.Tensor(np.array([fid])).to(self.data_device)`) — preferred if
     you also need that frame's real camera pose (e.g. for Q1's rasterized path, or
     for picking a `w_o` in Q2), since `scene.getTrainCameras()` (with
     `dataset.eval=False`) is already in frame-index order (finding 2 above).
4. `N = gaussians.get_xyz.shape[0]`; `time_input = fid.unsqueeze(0).expand(N, -1)`.
5. `d_values = deform.step(gaussians.get_xyz.detach(), time_input, feature=gaussians.get_binary_feature())`
   (`camera_center` kwarg is accepted but ignored — safe to omit).
6. `d_xyz, d_rotation, d_scaling = d_values['d_xyz'], d_values['d_rotation'], d_values['d_scaling']`
   (`d_scaling` will be all-zero — `utils/time_utils.py:192` — deformed scale equals
   canonical scale always, per the eval doc).
7. Deformed position: `gaussians.get_xyz + d_xyz`.
8. Deformed rotation quaternion: `gaussians.get_rotation_bias(d_rotation)`
   (`gaussian_model.py:151-153`) — normalized `_rotation + d_rotation`.
9. Deformed normal: `build_rotation(gaussians.get_rotation_bias(d_rotation))[:, :, 2]`
   (`utils/general_utils.py:145-166`), then optionally
   `flip_align_view`/`safe_normalize` per whatever orientation convention you settle
   on for Q2.

All of this runs under `torch.no_grad()`, needs no rasterizer, no `Scene` camera
iteration beyond reading one `.fid`, and needs no ray tracer either (tracer/BVH only
enter once you go on to compute visibility, i.e. Q1/Q2, not for the deformed state
itself).

---

## Open decisions for the user (not resolvable from code alone)

1. **Normal-flip convention** for per-Gaussian normals (Q2/Q3 §9): `trace()`'s
   default flips toward a `camera_center`; a per-surfel, camera-independent quantity
   needs its own convention.
2. **Whether "outgoing radiance" (Q2) includes specular**: if yes, need to pick a
   `w_o` per Gaussian since `GGX_specular` is view-dependent and surfels have no
   intrinsic view direction.
3. **Confirm scene choice for Test 1**: per `docs/lumimotion_repro.md`'s own caveat,
   `hook150` has limited self-occlusion/inter-reflection and was flagged as the wrong
   choice for this investigation (`standup150`/`jumpingjacks150` recommended instead)
   — worth deciding before investing in instrumentation, since occlusion/visibility
   is central to both Q1 and Q2.
