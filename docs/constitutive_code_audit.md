# Constitutive Appearance — LumiMotion Code Audit

**Question.** Does the current `constitutive-appearance` source provide a technically clean substrate for a future deformation-conditioned material experiment, without changing Stage 1?

**Audit scope.** Read-only source inspection on 2026-08-23. Repository root and branch were verified as `/home/fmb/projects/LumiMotion` and `constitutive-appearance`; the initial `git status --short` was empty. Joanna's `.blend` files were not opened, changed, unpacked, rendered, or passed to Blender. Labels below mean: **VERIFIED** = directly established by current source; **INFERRED** = consequence of verified facts; **PROPOSED** = future option, not implemented; **UNKNOWN** = source inspection cannot settle it.

## 1. Executive conclusion

**Verdict: feasible with architectural caveats.**

**VERIFIED.** Stage 2 has one canonical per-Gaussian albedo and scalar roughness tensor, and the same Gaussian row is deformed at each time by additive position/rotation outputs. Stage 2 disables topology-changing Gaussian optimization and freezes the geometry/deformation backbone. Canonical `x_i` and deformed `x_i^t` coexist directly in `render_ir`, so a fixed-canonical-neighbour deformation estimator can be inserted without modifying Stage 1 (`scripts/train_stage2.py:63-98`, `scripts/train_stage2.py:142-168`, `gaussian_renderer/render_ir.py:79-101`).

**Architectural caveats.**

1. **VERIFIED:** no canonical kNN graph is retained. The bundled `simple-knn` call returns only a nearest-neighbour distance used for initial scale; it does not expose neighbour identities to Python (`scene/gaussian_model.py:23`, `scene/gaussian_model.py:219-239`). A fixed graph must therefore be computed and stored separately.
2. **VERIFIED:** learned deformation scale is hard-zeroed, so the model exposes time-varying centers and rotations but no time-varying Gaussian scales (`utils/time_utils.py:125-138`, `utils/time_utils.py:186-204`). Neighbour displacement can still support an estimated `F`, but Gaussian-local scale cannot validate stretch.
3. **VERIFIED:** no tangent, bitangent, UV, or intrinsic material frame exists in the Gaussian state; normals come from the third rotation/covariance axis. Scalar isotropic roughness is therefore a clean first hook, but directional constitutive appearance is not (`scene/gaussian_model.py:60-66`, `scene/gaussian_model.py:144-169`, `scene/gaussian_model.py:648-658`).
4. **VERIFIED:** released dynamic NVS and relighting evaluation build the BVH at the first evaluated frame and never update it, while Stage-2 training builds once then updates every sampled frame (`scripts/eval_nvs_dynamic.py:69-95`, `scripts/eval_relight_dynamic.py:80-107`, `scripts/train_stage2.py:142-168`). Any appearance result using indirect visibility on later frames is silently geometrically stale.
5. **VERIFIED:** intrinsic `get_albedo` and `get_rough` are time-invariant, but appearance is not wholly time-invariant: the time-conditioned Stage-1 color/shadow head modulates the SH/radiance cache used for the reconstruction auxiliary and indirect lighting (`utils/time_utils.py:140-152`, `utils/time_utils.py:172-204`, `gaussian_renderer/render_ir.py:147-166`, `gaussian_renderer/render_ir.py:531-544`). This can compensate for material error.

**INFERRED.** LumiMotion is a viable substrate for an oracle scalar-roughness study only if (a) fixed neighbourhoods are established after the Stage-1 checkpoint is loaded, (b) all dynamic evaluation paths refit the BVH per frame, and (c) comparisons explicitly control the time-conditioned Stage-1 radiance residual. It is not yet a clean substrate for anisotropic/material-frame constitutive appearance.

## 2. Verified material pipeline

### State, initialization, and parameterization

- **VERIFIED:** `GaussianModel` stores `_albedo_dc`, `_albedo_rest`, and `_roughness` as per-row tensors; no metallic or learned specular/F0 tensor is declared (`scene/gaussian_model.py:60-75`). `get_albedo` converts the DC SH coefficient to RGB and clamps it to `[0.03, 0.97]`; `get_rough` applies sigmoid (`scene/gaussian_model.py:159-177`). Roughness initializes to `0.75` in activated space (`scene/gaussian_model.py:70-92`, `scene/gaussian_model.py:219-240`).
- **VERIFIED:** initial albedo SH storage has shape `[N, (degree+1)^2, 3]`; DC and residual SH coefficients are separate trainable parameters (`scene/gaussian_model.py:219-240`). Stage 1 uses their concatenation as radiance features (`scene/gaussian_model.py:172-177`).
- **VERIFIED:** there is no metallic parameter. Direct BRDF Fresnel is a hard-coded scalar `0.04`; a separate function default of `0.02` is overridden by the call chain before `GGX_specular` again hard-codes `0.04` (`gaussian_renderer/render_ir.py:425-458`, `gaussian_renderer/render_ir.py:546-555`, `gaussian_renderer/render_ir.py:581-614`).

### Stage transition and optimization

- **VERIFIED:** Stage 2 loads the Stage-1 PLY and deformation checkpoint at the selected iteration (`scripts/train_stage2.py:49-61`, `scene/__init__.py:35-40`, `scene/__init__.py:87-95`). `load_ply` restores canonical geometry, activated-space logits for roughness, albedo DC/rest, a Stage-1 DC copy, opacity, scale, rotation, and binary feature in PLY row order (`scene/gaussian_model.py:353-422`).
- **VERIFIED:** Stage-2 `training_setup` initially registers all Gaussian groups including albedo, roughness, geometry and Stage-1 DC (`scene/gaussian_model.py:246-278`), then Stage 2 retains only `albedo_dc`, `albedo_dc_stage1`, `albedo_rest`, `roughness`, and `opacity`. Position, rotation, scale, and binary feature are removed from the optimizer (`scripts/train_stage2.py:63-80`).
- **VERIFIED:** the deformation optimizer is reduced to `mlp_color` (`scripts/train_stage2.py:83-94`), but the entire `deform.step` is executed under `torch.no_grad()` (`scripts/train_stage2.py:142-153`). **INFERRED:** its color head receives no Stage-2 gradients despite remaining in the optimizer; the residual is effectively frozen in Stage 2. This is a silent optimizer/configuration mismatch.
- **VERIFIED:** Stage 2 updates Gaussian material/opacity and the environment light every fourth iteration (`scripts/train_stage2.py:249-281`). It has image loss, Stage-1 SH auxiliary loss, optional roughness/base-color smoothness, and light regularizers (`scripts/train_stage2.py:170-240`).

### Serialization and restoration

- **VERIFIED:** Gaussian state is checkpointed as PLY, not as an optimizer/model-state bundle. `Scene.save` delegates to `save_ply` (`scene/__init__.py:108-110`). PLY attributes include canonical xyz, placeholder zero normals, current albedo DC, `_albedo_dc_stage1`, albedo-rest SH, opacity, raw roughness logits, two scale components, quaternion, and optional binary feature (`scene/gaussian_model.py:289-340`).
- **VERIFIED:** load restores those attributes as new `nn.Parameter`s in file row order; if roughness is absent it falls back to `0.75`, and if Stage-1 DC is absent it copies current DC (`scene/gaussian_model.py:353-422`). These permissive fallbacks can silently change checkpoint semantics.
- **VERIFIED:** deformation weights are saved/restored separately as a state dict (`scene/deform_model.py:38-53`); environment lighting is also separately saved by Stage 2 (`scripts/train_stage2.py:265-269`). Gaussian optimizer state is not restored by `Scene`.

### Rasterization and BRDF consumption

- **VERIFIED:** `render_ir` computes deformed centers but obtains base color solely from `pc.get_albedo`, converts it from sRGB to linear, and independently rasterizes it (`gaussian_renderer/render_ir.py:79-105`, `gaussian_renderer/render_ir.py:122-133`). Roughness is independently rasterized from `pc.get_rough.repeat(1,3)` (`gaussian_renderer/render_ir.py:135-166`). Alpha-composited pixel-space base color and roughness are returned in material-only mode (`gaussian_renderer/render_ir.py:234-256`).
- **VERIFIED:** pixel-space albedo, roughness, rasterized normal, surface point, and view direction enter `rendering_equation` in both training and evaluation (`gaussian_renderer/render_ir.py:258-300`). Diffuse uses `base_color/pi`; specular uses isotropic GGX with scalar/rasterized roughness (`gaussian_renderer/render_ir.py:546-555`, `gaussian_renderer/render_ir.py:581-614`).
- **VERIFIED:** relighting traces `[pc.get_albedo, pc.get_rough]` at secondary hits and uses traced roughness in the environment-map specular lookup (`gaussian_renderer/render_ir.py:492-529`). Therefore an oracle field must affect both primary roughness rasterization and the secondary-hit feature tensor if indirect relighting is included.

### Learned residuals and material-error compensation

- **VERIFIED:** the deformation MLP is directly conditioned on embedded time and canonical xyz. When `pred_color` is enabled, it predicts six values: a three-channel shadow modulation plus a nominal dynamic-color residual; only the shadow modulation is used downstream (`utils/time_utils.py:92-123`, `utils/time_utils.py:140-152`, `utils/time_utils.py:172-204`).
- **VERIFIED:** Stage 1 modulates its SH DC color with this time-conditioned shadow output before rasterization (`gaussian_renderer/__init__.py:108-134`). Stage 2 repeats that modulation for `render_sh` (`gaussian_renderer/render_ir.py:147-166`) and, in the non-relight rendering equation, traces those modulated SH features as local indirect radiance (`gaussian_renderer/render_ir.py:531-544`).
- **INFERRED:** even though intrinsic albedo and roughness are static, the time-conditioned radiance/shadow pathway can absorb deformation-correlated appearance changes. An oracle roughness comparison that leaves this head active tests incremental benefit over a strong compensator, not a pure fixed-material baseline.

## 3. Verified deformation pipeline

### Compact data flow

```text
JSON frame["time"] (or idx/len fallback)
  dataset_readers.py:164-173,207-209
        ↓ Camera.fid
  cameras.py:18-46
        ↓ expand to [N,1]
  train_stage2.py:138-150 / eval_*_dynamic.py
        ↓ DeformModel.step(canonical xyz, time, binary feature)
  deform_model.py:24-25
        ↓ embed canonical xyz + time → MLP hidden
  time_utils.py:172-188
        ↓ d_xyz, d_rotation; d_scaling := predicted_scaling * 0
  time_utils.py:186-204
        ↓
  x_t = pc.get_xyz + d_xyz
  s_t = pc.get_scaling + d_scaling (= canonical scale)
  q_t = normalize(pc._rotation + d_rotation)
  render_ir.py:79-97; gaussian_model.py:144-161
        ↓ rasterizer → alpha-weighted normal/depth/material G-buffers
  render_ir.py:122-232
        ↓ pixel BRDF + deformed-geometry tracer
  render_ir.py:258-300,425-578
```

- **VERIFIED:** for synthetic Blender-format datasets, JSON frames are sorted by filename; `frame['time']` is used when present, otherwise `idx/len(frames)` (`scene/dataset_readers.py:156-173`). Camera pose and time are stored in the same `CameraInfo` entry (`scene/dataset_readers.py:177-209`) and copied to `Camera.fid` (`scene/cameras.py:18-46`, `utils/camera_utils.py:44-60`).
- **VERIFIED:** the deformation network consumes canonical xyz and embedded time, with the learned binary feature multiplying only `d_xyz`, `d_rotation`, and the unused dynamic-color half (`utils/time_utils.py:172-204`). The returned hidden embedding is not consumed by current trainers/renderers.
- **VERIFIED:** rotations are additive in raw quaternion coordinates followed by normalization, not quaternion composition (`scene/gaussian_model.py:147-153`). In the standard rasterizer path, deformed scales and rotations are passed explicitly (`gaussian_renderer/__init__.py:88-106`, `gaussian_renderer/render_ir.py:79-97`).
- **VERIFIED:** `d_scaling` has two components because Gaussians are 2D surfels; it is always zero in the learned MLP (`utils/time_utils.py:125-138`, `utils/time_utils.py:186-194`). No deformation feature directly represents a deformation gradient, stretch, or shear.

## 4. Gaussian identity and topology

- **VERIFIED:** Stage 1 changes topology. Densification appends cloned/split rows and copies their material, geometry, and binary feature; splitting then removes selected parents, and pruning boolean-filters every optimized tensor (`scene/gaussian_model.py:442-477`, `scene/gaussian_model.py:479-532`, `scene/gaussian_model.py:534-602`). Stage-1 training invokes this through `densify_until_iter` (`scripts/train_stage1.py:229-241`). Thus Gaussian identity is not stable during Stage 1.
- **VERIFIED:** these operations preserve row alignment across all Gaussian attributes, but parent identity is not serialized. PLY has no immutable Gaussian ID field (`scene/gaussian_model.py:289-340`). A split child cannot later be related to its parent from a checkpoint alone.
- **VERIFIED:** Stage 2 loads one completed PLY, removes xyz/scale/rotation/feature from the optimizer, never calls densification/pruning, records a fixed `N`, and queries one deformation output per canonical row (`scripts/train_stage2.py:61-98`, `scripts/train_stage2.py:138-168`). Checkpoint saves/loads retain PLY row order (`scene/gaussian_model.py:311-340`, `scene/gaussian_model.py:353-422`).
- **VERIFIED:** deformed coordinates and rotations are elementwise additions to canonical tensors without indexing, sorting, resampling, or recreation (`gaussian_renderer/render_ir.py:79-97`). BVH bounding geometry assigns `gs_id = arange(N)` in the same order (`scene/gaussian_model.py:610-632`).

**Answer.** **VERIFIED:** after a specific Stage-1 checkpoint is loaded for Stage 2, canonical Gaussian `i` deterministically maps to deformed Gaussian `i` at every timestep in that Stage-2 run. **Caveat:** this identity is checkpoint-local; it is not stable across earlier Stage-1 densification checkpoints, and no persistent semantic ID exists across independently written/reordered PLY files.

## 5. Canonical/deformed state availability

- **VERIFIED:** `scripts/train_stage2.py:142-168` has canonical `gaussians.get_xyz`, `time_input`, and all `d_*`; `render_ir` then has `pc.get_xyz` and `means3D = pc.get_xyz + d_xyz` simultaneously (`gaussian_renderer/render_ir.py:79-97`). This is the narrowest shared train/render location with explicit canonical and deformed positions.
- **VERIFIED:** canonical scale/rotation and their deformed values coexist at `gaussian_renderer/render_ir.py:86-97`. Canonical raw quaternion plus delta also coexist in `get_rotation_bias` (`scene/gaussian_model.py:147-153`).
- **VERIFIED:** no normal tensor is stored. The rasterizer derives per-Gaussian normals from the deformed rotation/scale representation and emits an accumulated normal G-buffer (`gaussian_renderer/render_ir.py:122-180`). The tracer explicitly derives its normal from the third row/axis of the splat-to-world transform and view-flips it (`scene/gaussian_model.py:648-658`).
- **INFERRED:** canonical/deformed normals can be derived side by side from `pc.get_rotation` and `pc.get_rotation_bias(d_rotation)`, but this is not currently done in the core path. Canonical/deformed scales are available, but learned `d_scaling=0` makes them identical.

## 6. Deformation-gradient feasibility

### Verified source facts

- **VERIFIED:** Stage-2 row identity and topology are fixed; deformed coordinates preserve indexing (Section 4).
- **VERIFIED:** current core code has no neighbourhood-index tensor, graph, adjacency, or kNN query. `simple_knn._C.distCUDA2` is called only once during point-cloud initialization to obtain a scalar squared nearest-neighbour distance for each point and initialize scale (`scene/gaussian_model.py:23`, `scene/gaussian_model.py:219-239`).
- **VERIFIED:** the deformation network returns per-row `d_xyz`, `d_rotation`, a hidden vector, and zero scale delta; it does not return Jacobians, neighbour correspondences, deformation gradients, or strain (`utils/time_utils.py:172-207`).
- **VERIFIED:** canonical and deformed coordinates coexist before material rasterization (`gaussian_renderer/render_ir.py:79-101`). Stage 2 invokes deformation under no-grad, so deformation descriptors computed from these outputs would not backpropagate to Stage 1 (`scripts/train_stage2.py:142-153`).

### Inferred design consequences

- **INFERRED:** a local least-squares `F_i,t` is technically derivable from fixed canonical neighbours because both point sets have stable row correspondence in Stage 2. It must use neighbour displacement, not the predicted Gaussian scale, to infer stretch/shear.
- **INFERRED:** canonical neighbourhoods should be built once after loading the exact Stage-1 PLY used for Stage 2 and persisted with checkpoint identity/row count. Recomputing kNN in deformed space would change material identity and confound strain with neighbourhood swapping.
- **INFERRED:** a full unconstrained 3D affine `F` may be ill-conditioned for locally surface-like 2D Gaussians. A tangent-plane fit needs a robust canonical surface basis, which current state does not explicitly store. The Gaussian rotation axes are a possible proxy, not verified material coordinates.
- **INFERRED:** because Stage-2 geometry is detached, an oracle/read-only `F` can be computed without altering Stage 1. A future learned appearance law could still receive gradients through `F` to its own parameters while treating `F` as fixed input.

### Proposed future option

- **PROPOSED:** compute a fixed canonical neighbour index immediately after `Scene(..., load_iteration=...)` and before Stage-2 optimization (`scripts/train_stage2.py:57-98`), then evaluate `F_i,t` immediately after `d_values` is unpacked (`scripts/train_stage2.py:142-159`) or inside `render_ir` after `means3D` is formed (`gaussian_renderer/render_ir.py:79-97`). The latter is shared by training and evaluation but should accept precomputed neighbourhoods explicitly rather than hide mutable state in `GaussianModel`.
- **PROPOSED:** use a dedicated PyTorch/CUDA kNN implementation that returns indices, or extend/wrap the bundled utility only after verifying its API. The current Python binding is not evidence that neighbour IDs are available.

## 7. Normals and material-frame analysis

- **VERIFIED:** initialization sets each quaternion to identity and stores only two in-plane log-scales (`scene/gaussian_model.py:225-240`). PLY `nx,ny,nz` fields are always written as zeros and are not loaded as model state (`scene/gaussian_model.py:289-340`, `scene/gaussian_model.py:353-422`).
- **VERIFIED:** deformed quaternion is `normalize(_rotation + d_rotation)` (`scene/gaussian_model.py:147-153`). Rasterization uses that quaternion and scale; it returns accumulated normals which are transformed from view to world coordinates (`gaussian_renderer/render_ir.py:86-97`, `gaussian_renderer/render_ir.py:179-187`). The BRDF normal is the alpha-normalized rasterized normal (`gaussian_renderer/render_ir.py:229-232`, `gaussian_renderer/render_ir.py:281-300`).
- **VERIFIED:** tracer normals are the normalized third axis of the covariance transform, optionally flipped to face relative to the camera (`scene/gaussian_model.py:648-658`). This is a geometric surfel frame, not an intrinsic material frame.
- **VERIFIED:** no tangent/bitangent/UV/material-axis tensor is declared or serialized (`scene/gaussian_model.py:60-75`, `scene/gaussian_model.py:289-340`). GGX is isotropic and consumes no tangent (`gaussian_renderer/render_ir.py:581-614`).

**Answer.** **VERIFIED:** current representation can express orientation changes of the surfel normal. **VERIFIED:** it cannot distinguish physical stretch/shear from rigid rotation using `d_rotation` alone, especially because `d_scaling` is zero. **INFERRED:** neighbour-derived `F` can separate rigid rotation from stretch, but intrinsic directional response additionally requires a stable material frame absent from current source.

## 8. Oracle material-hook candidates

### Candidate A — primary per-Gaussian roughness input to `render_ir` (recommended)

- **Location:** `gaussian_renderer/render_ir.py:26-33`, consumed at `gaussian_renderer/render_ir.py:135-145`.
- **Available tensors:** canonical `pc`, `d_xyz`, `d_rotation`, `d_scaling`, camera, deformed `means3D`, scales, rotations, opacity, and `N` implicitly from `pc` (`gaussian_renderer/render_ir.py:40-101`).
- **PROPOSED:** add an optional `[N]`/`[N,1]` activated roughness argument, shape/range-check it, and substitute it for `pc.get_rough` in the roughness rasterization.
- **Gradients:** oracle evaluation can detach it; future learned material experiments would preserve gradients. Train/eval share this core function.
- **Invasiveness:** low in the core, but every intended caller must pass the same frame-aligned tensor.
- **Hazards:** this alone does not update secondary-hit roughness in relighting; shape broadcasting from `[N]` must be prohibited; distinguish activated roughness from raw logits; keep per-frame tensor row order tied to the loaded PLY.

### Candidate B — pass a unified per-Gaussian material feature through primary and secondary paths

- **Locations:** primary rasterization at `gaussian_renderer/render_ir.py:100-145`; relight secondary features at `gaussian_renderer/render_ir.py:492-511`.
- **Available tensors:** same as Candidate A, plus the rendering-equation call receives full deformed xyz/scale/rotation/opacity (`gaussian_renderer/render_ir.py:281-300`, `gaussian_renderer/render_ir.py:425-458`).
- **PROPOSED:** resolve `roughness_gaussian` once near `render_ir.py:100-101`, use it both for `colors_precomp` in the roughness rasterizer and in the traced `[albedo, roughness]` feature tensor.
- **Gradients:** relevant if indirect-light gradients should train the future law; tracer backward supports feature gradients (`submodules/surfel_tracer/surfel_tracer/raytracer.py:5-66`).
- **Invasiveness:** moderate, because the resolved tensor must be threaded into `rendering_equation` rather than reread from `pc`.
- **Hazards:** omitting the secondary substitution creates inconsistent primary/indirect BRDFs. Relight and non-relight branches use different indirect representations.

### Candidate C — caller-side temporary mutation/override

- **Location:** after deformation unpacking in Stage 2/evaluators, e.g. `scripts/train_stage2.py:142-168`, `scripts/eval_nvs_dynamic.py:76-95`, `scripts/eval_relight_dynamic.py:87-107`.
- **PROPOSED:** caller computes the tensor and passes it as an explicit argument. Do **not** replace `pc._roughness` or monkey-patch `get_rough`.
- **Gradients:** caller controls detachment; train/eval do not share a single caller.
- **Invasiveness:** many call-site edits but explicit data provenance.
- **Hazards:** a stateful mutation could leak one frame into another, serialize oracle values, mismatch activated/logit conventions, or silently miss reporting/material-only/rotating-envmap paths.

**Recommendation.** Candidate B is the narrowest scientifically correct oracle hook when relighting/indirect light matters; Candidate A is sufficient only for a deliberately direct/primary-only oracle. Candidate C should be used only to construct and pass the field, never to mutate model state.

## 9. Training/evaluation consistency and hazards

### BVH consistency

- **Training — VERIFIED:** Stage 2 builds the BVH on its first sampled frame and calls `update_bvh` on every later training iteration (`scripts/train_stage2.py:142-168`). `update_bvh` refits vertices while asserting unchanged triangle topology (`submodules/surfel_tracer/surfel_tracer/raytracer.py:74-82`).
- **NVS evaluation — VERIFIED:** dynamic NVS builds once inside the loop, flips `build_bvh=False`, and has no update call (`scripts/eval_nvs_dynamic.py:69-95`). Later frames trace against first-frame BVH bounding triangles while passing current Gaussian tensors to shading.
- **Relighting evaluation — VERIFIED:** dynamic relighting has the same stale-BVH pattern (`scripts/eval_relight_dynamic.py:80-107`).
- **Material evaluation — VERIFIED:** it uses `material_only=True` and returns before tracing, so it builds no BVH (`scripts/eval_material_dynamic.py:70-90`, `gaussian_renderer/render_ir.py:238-256`). This is internally adequate for rasterized material maps.
- **Training report — VERIFIED:** Stage-2 report calls `update_bvh` for each sampled validation view after training has already built it (`utils/train_report_utils.py:264-303`).

This confirms the historical stale dynamic-evaluation BVH claim against current source; current source has not fixed it.

### Other silent hazards

- **Frame/camera coupling — VERIFIED:** synthetic camera and `fid` come from the same JSON frame record, but fallback time is list index based (`scene/dataset_readers.py:156-173`, `scene/dataset_readers.py:177-209`). **UNKNOWN:** source cannot verify that every generated image filename, animation frame, and JSON time in local/private datasets are aligned.
- **Static-control mismatch — historical context, current-code consequence:** the reader blindly trusts varying JSON `time`; it has no concept of a mesh frozen at one authored frame (`scene/dataset_readers.py:164-173`). A static-timestep dataset with varying camera-index time can still drive different learned deformation.
- **Coordinate convention — VERIFIED:** canonical xyz is in the normalized reconstruction/world coordinates loaded into the Gaussian model; camera transforms are also normalized through scene loading. No explicit canonical-to-Blender mesh transform or mesh vertex correspondence exists (`scene/__init__.py:79-104`, `scene/dataset_readers.py:177-209`).
- **Detach boundary — VERIFIED:** Stage 2 freezes deformation outputs via `torch.no_grad()` (`scripts/train_stage2.py:142-153`). This is desirable for an oracle geometry control but must be explicit in any later learned strain module.
- **Scale semantics — VERIFIED:** Gaussian scale is two-dimensional and activated by `exp`; `d_scaling` is an additive value in activated scale space but is currently zero (`scene/gaussian_model.py:143-153`, `gaussian_renderer/render_ir.py:86-97`, `utils/time_utils.py:186-194`). It must not be mistaken for principal stretch.
- **Rotation semantics — VERIFIED:** additive quaternion coefficients followed by normalization are not a physical incremental rotation parameterization (`scene/gaussian_model.py:147-153`). Do not derive strain magnitude from `d_rotation`.
- **Normal sign — VERIFIED:** tracer normals may flip with camera center (`scene/gaussian_model.py:653-658`), while rasterizer normal handling is a separate path (`gaussian_renderer/render_ir.py:179-187`). A material frame must not inherit view-dependent sign.
- **Stage reset/topology — VERIFIED:** Stage 2 reloads a serialized PLY and reconstructs parameters; it does not inherit optimizer state (`scene/__init__.py:87-95`, `scene/gaussian_model.py:408-422`). Canonical neighbours must be associated with the loaded checkpoint, not a pre-densification cloud.
- **Serialization omission — VERIFIED:** no neighbour graph, immutable ID, normal, tangent, deformation descriptor, or oracle material field is serialized (`scene/gaussian_model.py:289-340`).
- **Residual compensation — VERIFIED/INFERRED:** time-conditioned Stage-1 shadow modulation affects `render_sh` and indirect local radiance (Section 2), potentially masking fixed-roughness error.
- **Relight inconsistency — VERIFIED:** primary roughness is rasterized into pixels; secondary roughness is separately ray-traced from per-Gaussian material. Any hook applied at only one site silently produces two material definitions (`gaussian_renderer/render_ir.py:135-165`, `gaussian_renderer/render_ir.py:492-529`).
- **Evaluation override — VERIFIED:** dynamic relighting multiplies base color by a dataset/model-level scale loaded from JSON, but this does not alter roughness (`scripts/eval_relight_dynamic.py:30-35`, `scripts/eval_relight_dynamic.py:101-107`, `gaussian_renderer/render_ir.py:234-237`).
- **Mask semantics — VERIFIED from current evaluator:** NVS/relighting metrics read alpha channel from held-out renders as the foreground mask (`scripts/eval_nvs_dynamic.py:100-128`, `scripts/eval_relight_dynamic.py:112-140`). These scripts do not consume the `dynamic_mask/` RGB segmentation at all.

## 10. Relationship to the Blender source assets

- **VERIFIED:** repository-wide current-code search finds no training/evaluation reference to `blend_files/`, `blendfiles_v5_specular32`, or the `.blend` filenames. `Scene` accepts a generated Blender/D-NeRF-style dataset only when `transforms_train.json` exists (`scene/__init__.py:45-58`). The reader consumes transforms, rendered images, and `points3d.ply`, not `.blend` state (`scene/dataset_readers.py:156-220`, `scene/dataset_readers.py:214-293`).
- **VERIFIED:** the local asset directory contains the five named base files, their `_dynamic_mask` and `_roughness` variants, four HDRs, and the normal-example ZIP. Git reports no tracked files under `blend_files/`.
- **INFERRED:** the `.blend` files are dataset-generation sources, not training inputs. Historical embedded-script survey maps them to generated scene families such as `hook150_v5_spec32`, `jumpingjacks150_v5_spec32`, `standup150_v5_spec32`, and static-timestep variants under a `d-nerf-relight-spec32` dataset layout (`docs/miscellaneous/blend_files_survey.md:50-258`, `docs/miscellaneous/lumimotion_eval.md:256-305`). Those generated data directories are not present in this worktree at audit time, so their current contents cannot be reverified here.
- **VERIFIED:** current LumiMotion evaluation separately reads generated albedo PNGs and RGBA render alpha (`scripts/eval_material_dynamic.py:53-55`, `scripts/eval_material_dynamic.py:96-115`); core dataset loading reads beauty RGBA and camera/time JSON (`scene/dataset_readers.py:156-209`). Core training does not load generated roughness, depth, dynamic-mask, mesh geometry, animation state, or normals.
- **VERIFIED:** existing repository-local Blender helper scripts under `scripts_local/test2/` inspect or modify copies for the prior indirect-light campaign. `render_config.py` queries evaluated object bounds and armature-driven membership and renders AOVs, but it does not export per-vertex evaluated geometry/topology, deformation gradients, exact mesh normals, or animation metadata (`scripts_local/test2/render_config.py:1-24`, `scripts_local/test2/render_config.py:62-81`, `scripts_local/test2/render_config.py:115-139`). `dump_settings.py` records static file/settings counts and raw mesh totals, not per-frame evaluated mesh state (`scripts_local/test2/dump_settings.py:1-12`, `scripts_local/test2/dump_settings.py:57-104`).
- **UNKNOWN:** without opening the assets (forbidden here), current source cannot establish exact object names/topology stability, modifier evaluation order, per-frame evaluated normals, mesh-to-render transform, or which original source mesh corresponds to learned Gaussian rows. The historical survey is context, not current code ground truth.

## 11. Contradictions with CONSTITUTIVE_APPEARANCE_DIRECTION.md

1. **WEAKENED, not refuted:** the direction says LumiMotion Stage 2 keeps albedo/roughness constant across timesteps. This is **verified for intrinsic tensors** (`pc.get_albedo`, `pc.get_rough`), but appearance is not wholly time-invariant because a time-conditioned shadow/radiance residual remains active in reconstruction and indirect-light paths (`utils/time_utils.py:172-204`, `gaussian_renderer/render_ir.py:147-166`, `gaussian_renderer/render_ir.py:531-544`).
2. **WEAKENED:** the direction implies canonical neighbours may be cheaply accessible. Row-stable points are accessible, but no stored canonical neighbourhood identities exist; bundled `simple-knn` is used only for nearest-distance scale initialization (`scene/gaussian_model.py:23`, `scene/gaussian_model.py:219-239`).
3. **WEAKENED:** the direction discusses canonical/deformed rotations/scales as potential deformation evidence. Rotation is available, but scale deformation is explicitly zero (`utils/time_utils.py:186-194`), so current deformation outputs alone do not expose stretch/shear.
4. **WEAKENED:** the direction's eventual material-frame extension is not directly supported. No tangent/bitangent/material frame is stored or serialized, and current GGX is isotropic (`scene/gaussian_model.py:60-75`, `scene/gaussian_model.py:289-340`, `gaussian_renderer/render_ir.py:581-614`).
5. **CONTRADICTED historical prose, already anticipated by the direction/AGENTS:** historical `lumimotion_eval.md` stated training rebuilt the BVH from scratch each iteration; current source actually builds once and refits via `update_bvh` (`scripts/train_stage2.py:155-159`). The important train/eval discrepancy remains: released dynamic evaluators never refit after frame one.
6. **VERIFIED:** the central substrate assumption is not contradicted: one checkpoint-local canonical Gaussian topology maps deterministically to all Stage-2 deformations, and static scalar material tensors have a narrow pre-rasterization hook.

No stop-condition-level contradiction makes the planned scalar oracle hook non-viable. The caveats above must be resolved before interpreting results as constitutive appearance evidence.

## 12. Unknowns

- **UNKNOWN:** whether nearest-neighbour fits on the learned Gaussian cloud are numerically well-conditioned or physically track mesh strain.
- **UNKNOWN:** whether a Gaussian's geometric rotation axes align consistently with an intrinsic material direction.
- **UNKNOWN:** exact row-order stability under third-party PLY processing; the repository's own writer/reader preserves it but serializes no ID.
- **UNKNOWN:** whether the local generated datasets (not present here) exactly match the inspected asset filenames and historical folder/count descriptions.
- **UNKNOWN:** exact authored mesh topology, canonical frame, modifier stack, evaluated normals, and coordinate transform in Joanna's assets; establishing these requires a later authorized Blender-level read-only extraction.
- **UNKNOWN:** effect size and identifiability of deformation-conditioned reflectance. Code inspection cannot answer the scientific signal question.
- **UNKNOWN:** whether published evaluation numbers were produced with exactly these released stale-BVH scripts.
- **UNKNOWN:** the practical gradient behavior and memory cost of a unified oracle feature through the custom rasterizer/tracer without an implementation test.

## 13. Recommended NEXT READ-ONLY step

**PROPOSED — one step only:** write a pre-implementation **strain-extraction interface specification** (no code and no Blender execution) that freezes: the exact Stage-2 checkpoint identity; canonical-neighbour graph inputs/outputs and row-ID manifest; canonical/deformed coordinate convention; tangent-plane least-squares definition and degeneracy criteria; rigid/identity/known-stretch numerical invariants; activated roughness shape/range convention; and the requirement that oracle roughness be used consistently at both primary rasterization and secondary tracer hits. This closes the remaining architectural ambiguities before any extractor or oracle hook is implemented.

## Audit record

### Commands actually run

Read-only commands used: `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git status --short`, `git ls-files`, `rg`, `rg --files`, `find` (names/directories only), `wc -l`, `sed -n`, and `nl -ba`. No Python, Blender, renderer, trainer, GPU process, package manager, or dataset mutation was invoked.

### Files read

- Instructions/direction: `AGENTS.md`; `docs/CONSTITUTIVE_APPEARANCE_DIRECTION.md`.
- Core source: `scene/gaussian_model.py`; `scene/deform_model.py`; `scene/__init__.py`; `scene/dataset_readers.py`; `scene/cameras.py`; `utils/time_utils.py`; `utils/camera_utils.py`; `utils/train_report_utils.py`; `gaussian_renderer/__init__.py`; `gaussian_renderer/render_ir.py`; `scripts/train_stage1.py`; `scripts/train_stage2.py`; `scripts/eval_nvs_dynamic.py`; `scripts/eval_relight_dynamic.py`; `scripts/eval_material_dynamic.py`; `scripts/render_materials.py`; `submodules/simple-knn/simple_knn.cu`; `submodules/simple-knn/ext.cpp`; `submodules/surfel_tracer/surfel_tracer/raytracer.py`.
- Historical/context and local helpers: `docs/miscellaneous/lumimotion_eval.md`; `docs/miscellaneous/lumimotion_campaign_summary.md`; `docs/miscellaneous/test1_hook_points.md`; `docs/miscellaneous/blend_files_survey.md`; `scripts_local/test2/render_config.py`; `scripts_local/test2/dump_settings.py`.
- Filename-only inventory: `blend_files/blendfiles_v5_specular32/` (no file contents opened).

### File created/modified

- `docs/constitutive_code_audit.md` only.
