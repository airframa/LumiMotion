# Constitutive Appearance — Deformation-Regime Characterization Preregistration

**Status:** Frozen before opening or measuring Joanna's source animations  
**Scope:** Descriptive characterization of validated Path-A reference-relative surface deformation  
**Not Gate 1:** No appearance, BRDF, rendering, material-response, or scientific effect-size test is defined here

## 1. Question and purpose

**Question.** What range and spatial prevalence of validated reference-relative surface deformation exists in Joanna's four armature-driven LumiMotion character animations?

**FROZEN.** This measurement is descriptive. It will characterize the deformation support available in the existing animations before any strain-to-reflectance law or Gate 1 appearance test is chosen. It does not ask whether the deformation is “large enough,” whether reflectance changes with deformation, or whether a future constitutive model will succeed.

**VERIFIED.** Path A passed its frozen float64 identity, rigid-motion, known-stretch, degeneracy, area-identity, and Blender 3.6.13 integration gates (`docs/constitutive_strain_extractor_validation.md:1-18`; `docs/constitutive_strain_extractor_validation.md:89-147`). The validation explicitly did not establish topology stability or deformation magnitude in Joanna's animations (`docs/constitutive_strain_extractor_validation.md:155-165`).

**UNKNOWN BEFORE MEASUREMENT.** The resolved mesh-object names, evaluated topology stability, valid-area coverage, and deformation distributions of all four assets remain unknown.

## 2. Frozen assets and scene independence

**FROZEN.** Include all and only these four base character scenes:

| Scene ID | Source asset |
|---|---|
| `hook` | `blend_files/blendfiles_v5_specular32/hook150_v5_specular32.blend` |
| `jumpingjacks` | `blend_files/blendfiles_v5_specular32/jumpingjacks_v5_specular32.blend` |
| `mouse` | `blend_files/blendfiles_v5_specular32/mouse_v5_specular32.blend` |
| `standup` | `blend_files/blendfiles_v5_specular32/standup150_v5_specular32.blend` |

No scene may be removed, substituted with a `_dynamic_mask` or `_roughness` variant, or selected based on observed deformation. `spheres_with_rotations` is not part of this character-regime measurement.

**FROZEN.** Each scene is an independent descriptive unit. Primary and secondary distributions are reported separately per scene. There is no pooled four-scene percentile or area fraction: pooling would weight scenes by their mesh area, face tessellation, and valid-frame coverage without a preregistered scientific reason.

**FROZEN.** The original author-shared files are read-only. The eventual measurement must not save, re-export, rename, move, repackage, or redistribute them.

## 3. Frozen mesh-selection rule

For each scene, select every source object satisfying both conditions:

1. `object.type == 'MESH'`;
2. the object has at least one modifier with `modifier.type == 'ARMATURE'` whose target object exists and has the exact Blender object name `Armature`.

**FROZEN.** Object qualification is determined from the scene/object/modifier state before strain values are computed. The resolved names are sorted by exact object name using Python's default Unicode string ordering, passed explicitly to the validated extractor, and recorded in the manifest in that order.

No qualifying object may be manually added, removed, merged, split, or reordered after strain is seen. Objects with other armature targets do not qualify. An object qualifies once even if it has multiple qualifying modifiers. If no object qualifies, the scene is unusable under this preregistration.

This rule mirrors the author's dynamic-object definition but does not use a rendered dynamic mask as geometry correspondence or weighting.

## 4. Frozen reference and target configurations

All configurations use integer Blender frames with `subframe = 0.0`.

| Scene ID | Reference frame | Target frames |
|---|---:|---|
| `hook` | 1 | every frame 1 through 150 inclusive |
| `jumpingjacks` | 1 | every frame 1 through 150 inclusive |
| `mouse` | 1 | every frame 1 through 150 inclusive |
| `standup` | 75 | every frame 1 through 150 inclusive |

**FROZEN.** Reference frames are reference configurations only. They are not assumed to be stress-free, bind-pose, undeformed, or physical rest states. Path A therefore measures deformation relative to the listed evaluated configuration, exactly as required by the interface (`docs/constitutive_strain_interface_spec.md:93-107`). Results from scenes with different reference frames are not pooled as though they had a common absolute zero.

The reference frame remains part of the target set. Its same-configuration result is retained, not discarded, and supplies an extraction-integrity identity check. No frame is ranked, previewed, subsampled, or removed based on strain magnitude.

## 5. Frozen extraction and strain contract

**FROZEN.** Use Path A exactly as specified in `docs/constitutive_strain_interface_spec.md` and implemented/validated in `docs/constitutive_strain_extractor_validation.md`. No formula, dtype, validity rule, threshold, invalid-reason definition, or topology rule may be changed after measurement begins.

In particular:

- evaluated dependency-graph vertices are transformed by the evaluated object-to-world matrix into Blender's right-handed world coordinates; no recentering, alignment, normalization, or Procrustes correction is permitted (`docs/constitutive_strain_interface_spec.md:127-141`);
- reference triangulation and row identity are frozen, and target geometry must preserve vertex, polygon, loop, triangle, winding, and order correspondence (`docs/constitutive_strain_interface_spec.md:109-125`);
- face deformation uses `F_surface = Ds B_ref^{-1}`, evaluated by the validated stable solve, and `C_surface = F_surface^T F_surface` (`docs/constitutive_strain_interface_spec.md:143-173`);
- ordered principal stretches are `lambda_max >= lambda_min > 0`, obtained from the eigenvalues of symmetric `C_surface` (`docs/constitutive_strain_interface_spec.md:175-195`);
- float64 computation and the frozen `q_area`, condition-number, eigenvalue, and nonfinite criteria remain exactly those in `docs/constitutive_strain_validation_prereg.md:209-268`;
- invalid records remain in canonical face-row order with explicit reason bits and NaN strain descriptors; they are never repaired, clamped to identity, spatially rematched, or silently dropped (`docs/constitutive_strain_interface_spec.md:75-89`; `docs/constitutive_strain_extractor_validation.md:123-127`).

**FROZEN.** Use the validated portable executable `/home/fmb/blender-3.6.13-linux-x64/blender`, Blender version `3.6.13`, build hash `791bdfd03f07`, for all four assets. The exact executable path, reported version/build, source-file hash, extractor revision/hash, scene, view layer, object names/order, modifier state, actions/shape keys, frames, transforms, topology hashes, numeric versions, and commands are recorded in each manifest. The validated wrapper and binary are documented at `docs/constitutive_strain_extractor_validation.md:135-147`.

## 6. Frozen analysis population

### 6.1 Authoritative record

The authoritative observation is one valid face at one target frame in one selected object:

```text
(scene_id, object_name, frame, canonical_face_row)
```

For a scene, the distribution population is all such valid observations over every selected object and all 150 target frames. A canonical face therefore appears once per target frame and always retains the same face row and reference area.

Invalid observations are excluded from numeric percentiles and threshold numerators/denominators because their strain values are NaN, but they remain in the archived arrays and validity tables. Topology-failed object/frame configurations are not treated as missing-at-random observations and are never silently omitted; Section 10 governs them.

No face-to-vertex aggregation, mesh-to-Gaussian mapping, temporal smoothing, spatial smoothing, clipping, winsorization, or outlier removal is part of this characterization. Face-level values remain authoritative, as specified at `docs/constitutive_strain_interface_spec.md:215-239`.

### 6.2 Frozen derived quantities

For each valid face/frame observation, use the Path-A fields and define:

```text
abs_log_stretch_max = abs(log_stretch_max)
abs_log_stretch_min = abs(log_stretch_min)
abs_log_area_change = abs(log_area_change)
max_abs_log_stretch = max(abs_log_stretch_max, abs_log_stretch_min)
```

`log_anisotropy` is used without an absolute value because the ordered-stretch definition makes it nonnegative. The underlying descriptor definitions are frozen at `docs/constitutive_strain_interface_spec.md:41-71`.

### 6.3 Frozen percentile convention

For values `x_i`, positive weights `w_i`, and percentile probability `q`, sort observations by ascending `x_i`. The weighted percentile is the smallest observed value `x_(k)` for which

```text
cumulative_sum(w_(1)..w_(k)) / sum_i(w_i) >= q
```

This is the left-continuous inverse of the weighted empirical CDF; no interpolation is used. Ties do not affect the value. Unweighted percentiles use the identical rule with `w_i = 1`. Percentile probabilities are frozen per quantity below. Upper-tail summaries use subsets of `0.50`, `0.75`, `0.90`, `0.95`, and `0.99`; the lower-tail summary for `lambda_min` uses subsets of `0.01`, `0.05`, `0.10`, `0.25`, and `0.50`.

## 7. Primary characterization: reference-area-weighted scene distributions

**FROZEN PRIMARY WEIGHT.** Each valid face/frame observation receives its canonical reference-face area:

```text
w(scene, object, frame, face) = area_reference(object, face)
```

The same canonical face has the same weight at every frame. Deformed area is not a weight. Because every scheduled frame is present exactly once when a scene is usable, this defines an area-weighted space–time prevalence measure rather than a “largest frame” statistic.

For each scene separately, report the following reference-area-weighted percentiles.

For `lambda_max`, which represents extension in the larger principal-stretch direction, report:

```text
p50, p75, p90, p95, p99
```

For `lambda_min`, where stronger compression appears in the **lower** tail, report:

```text
p01, p05, p10, p25, p50
```

For each of the following deformation-magnitude quantities, report:

```text
p50, p75, p90, p95, p99
```

for:

1. `abs(log_stretch_max)`;
2. `abs(log_stretch_min)`;
3. `abs(log_area_change)`;
4. `log_anisotropy`;
5. `max_abs_log_stretch`.

The asymmetric percentile convention for `lambda_max` and `lambda_min` is intentional. Large `lambda_max` values describe the extension tail, whereas small `lambda_min` values describe the compression tail. Reporting only upper percentiles of `lambda_min` would not characterize strong compression.

The denominator for each percentile is the sum of reference-area weights over valid observations for that quantity. Since all seven quantities share Path-A validity, their valid population must be identical; any difference is an analysis error.

## 8. Secondary characterization

### 8.1 Unweighted face-level distributions

For each scene separately, report the following unweighted face/frame percentiles.

For `lambda_max`, report:

```text
p50, p90, p95, p99
```

For `lambda_min`, report:

```text
p01, p05, p10, p50
```

For each of:

```text
abs(log_stretch_max)
abs(log_stretch_min)
abs(log_area_change)
log_anisotropy
max_abs_log_stretch
```

report:

```text
p50, p90, p95, p99
```

Each valid face/frame observation has weight one.

These summaries are secondary to the reference-area-weighted distributions and are included to expose sensitivity to mesh tessellation density.

The asymmetric treatment of `lambda_min` is intentional: its lower tail, rather than its upper tail, captures increasing compression.

### 8.2 Descriptive reference-area fractions

For each scene separately, report the reference-area-weighted fraction of valid face/frame observations satisfying each condition:

```text
lambda_max >= 1.02
lambda_max >= 1.05
lambda_max >= 1.10
lambda_max >= 1.20

lambda_min <= 0.98
lambda_min <= 0.95
lambda_min <= 0.90
lambda_min <= 0.80
```

For condition `E`, compute

```text
fraction(E) = sum_i(area_reference_i * 1[E_i])
              / sum_i(area_reference_i)
```

over valid face/frame observations in that scene. Report numerator weighted area, denominator weighted area, and the fraction. These are space–time reference-area fractions: a region satisfying a condition for ten frames contributes ten times its reference area.

**DESCRIPTIVE ONLY.** These thresholds are reporting bins, not success/failure criteria, deformation sufficiency thresholds, exclusions, clipping bounds, or inputs to scene/frame selection.

## 9. Validity, coverage, and extraction-integrity reporting

For every scene/object/frame combination, including reference configurations, report:

- total canonical face count;
- valid face count and invalid face count;
- valid reference-area numerator;
- finite reference-area denominator;
- `valid_reference_area_fraction = valid reference area / finite reference area`;
- count for every invalid-reason bit independently (bit counts may overlap and need not sum to invalid face count);
- number of roundoff-eigenvalue projection events;
- topology/correspondence status and, upon failure, the exact failed check and observed/reference counts or hashes.

The finite reference-area denominator is the sum of finite, nonnegative canonical reference-face areas for that object. Nonfinite reference areas are not silently treated as zero: their face counts and invalid reasons are reported separately. If the denominator is zero, the object and therefore the scene are unusable.

Also report per scene:

- resolved selected-object list and stable order;
- scheduled frame count (`150`), successfully correspondence-checked frame count, and failed frame list;
- total face/frame observation count expected from the frozen object topology;
- valid and invalid observation counts;
- total valid reference-area weight and total finite reference-area weight across the scheduled space–time population;
- scene-wide valid reference-area fraction;
- invalid-reason counts across the scene, preserving overlapping-bit semantics.

**FROZEN INTEGRITY CHECK.** At each scene's reference frame, every otherwise valid face must satisfy the already-frozen identity and area gates: both stretch errors from one and the area-identity residual must be `<= 1e-5` (`docs/constitutive_strain_validation_prereg.md:142-205`). Any violation is an extraction/integration failure, not observed deformation, and makes the scene unusable pending diagnosis under a new recorded run.

No minimum acceptable valid-area fraction is defined here. Coverage is reported descriptively unless one of the explicit unusability conditions in Section 17 holds.

## 10. Topology/correspondence failures and missingness

Every selected object's evaluated target configuration must match its frozen reference vertex, polygon, loop, deterministic triangle, winding, and row order. Hash and count checks follow the validated wrapper. There is no spatial rematching, nearest-surface matching, retessellation repair, object substitution, or frame deletion.

If any selected object fails correspondence at any scheduled frame:

1. preserve and report the scene/object/frame failure and exact reason;
2. do not write a strain record pretending that configuration is valid;
3. do not replace the frame or object;
4. do not compute or present the incomplete scene's primary/secondary distributions as though they represented the preregistered 150-frame scene;
5. label the scene **unusable under the current extractor and preregistration**.

Diagnostics and any already-produced per-face arrays may be retained with explicit incomplete status, but they are not a valid substitute characterization. Other scenes remain independently reportable; a failure in one scene does not remove or invalidate a different scene.

## 11. Eventual outputs and provenance

The later measurement run must preserve immutable, face-authoritative arrays and manifests consistent with `docs/constitutive_strain_interface_spec.md:241-272`:

- canonical triangle rows, reference positions/bases/areas, and topology hashes;
- evaluated target positions and Path-A face outputs for every scheduled frame;
- `valid` and `invalid_reason` arrays, including failed/incomplete status rather than omissions;
- per-object/frame coverage and topology tables;
- machine-readable scene summaries containing all frozen percentiles, weighted fractions, numerators, denominators, and sample counts;
- a human-readable result document that reports all four scenes, including unusable/null outcomes.

Manifests must record source hashes without embedding source asset content, extractor/code revision and hashes, exact commands, Blender/Python/NumPy versions, scene/view-layer state, selected objects and qualifying modifiers, reference/target frames, transforms, triangulation policy, topology/position hashes, dtype/tolerances, and validation-suite PASS provenance.

No source `.blend` content is included in an output package. No appearance image, render pass, material measurement, face-to-vertex field, or Gaussian strain estimate is an output of this characterization.

## 12. Interpretation boundary

This measurement can establish only the range and spatial/temporal prevalence of reference-relative deformation in the four existing animations. It cannot establish:

- absolute physical strain relative to a stress-free material rest state;
- whether the animation deformation is physically realistic;
- whether any material's reflectance responds at these deformation levels;
- the sign or magnitude of a strain-to-roughness response;
- observability in images or superiority over a time-invariant material model;
- suitability of Gaussian-neighbour estimated strain;
- a Gate 1 success threshold or kill criterion.

No appearance, BRDF, lighting, rendering, literature effect size, or material parameter may enter the analysis. Observed values may inform the support over which a later independently justified material-response law is tested, but they cannot by themselves define “enough deformation.”

## 13. Commands used to prepare this preregistration

Only read-only repository commands were used before writing this file: `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git status --short`, `sed -n`, and `nl -ba`. Blender was not launched; no `.blend` file was opened; no strain, render, training, or asset statistic was computed.

## 14. Frozen choices

1. All four named base character assets are included and treated as separate scene units.
2. Meshes are selected mechanically as every `MESH` with an `ARMATURE` modifier targeting the exact object name `Armature`; resolved names are sorted, recorded, and never edited after strain is seen.
3. Reference frames are hook 1, jumpingjacks 1, mouse 1, and standup 75, all at subframe 0.0; they are reference-relative zeros, not claimed stress-free states.
4. Every integer target frame 1 through 150 inclusive is included once.
5. The validated Path-A formulation, float64 implementation, topology contract, validity rules, thresholds, invalid reasons, and Blender 3.6.13 evaluated-world-coordinate path are unchanged.
6. Face/frame records are authoritative; invalid records remain present and no spatial repair, smoothing, clipping, vertex aggregation, or frame selection is allowed.
7. Primary scene summaries use reference-face-area weighting over all valid face/frame observations. `lambda_max` is reported at `p50/p75/p90/p95/p99`; `lambda_min` is reported at `p01/p05/p10/p25/p50`; the five deformation-magnitude quantities are reported at `p50/p75/p90/p95/p99`.
8. Secondary scene summaries use equal face/frame weights. `lambda_max` is reported at `p50/p90/p95/p99`; `lambda_min` is reported at `p01/p05/p10/p50`; the five deformation-magnitude quantities are reported at `p50/p90/p95/p99`. The eight frozen reference-area threshold fractions in Section 8.2 are also reported.
9. Percentiles use the non-interpolated inverse empirical-CDF convention in Section 6.3.
10. Scenes are never pooled, and an incomplete 150-frame correspondence population is not silently summarized as complete.

## 15. Quantities intentionally descriptive only

1. Every reported primary or secondary percentile.
2. Every valid-count and valid-reference-area coverage measure.
3. The area fractions in the eight `lambda_max`/`lambda_min` bins.
4. Invalid-reason prevalence and roundoff-event counts, except where they expose an explicit extraction failure.
5. Differences among scenes, objects, frames, or weighted versus unweighted summaries.
6. Any observed extreme valid value retained by the frozen Path-A rules.

None is a success criterion, kill threshold, physical-material effect size, or justification for excluding data.

## 16. Decisions explicitly deferred until after deformation characterization

1. How much deformation is scientifically sufficient for an appearance experiment.
2. Any constitutive mapping from stretch, area change, or anisotropy to roughness or another BRDF parameter.
3. Material class, literature-derived response magnitude/sign, and independent material-physics evidence.
4. Gate 1 hypotheses, primary appearance statistic, effect-size threshold, falsifiers, controls, and exclusions.
5. Gate 1 scene/frame/deformation support, camera views, illuminations, and held-out split.
6. Strong time-invariant and matched-capacity time-conditioned material controls.
7. Any normalization, clipping, binning beyond the descriptive bins above, or sampling based on the observed deformation distribution.
8. Path-B Gaussian-neighbour strain, mesh-to-Gaussian association, and any LumiMotion training/material modification.
9. Anisotropic BRDFs, principal-direction use, and intrinsic material tangent frames.

## 17. Conditions that would make a scene unusable for this measurement

A scene is unusable under the current extractor and this preregistration if any of the following occurs:

1. the source asset cannot be opened read-only by the frozen Blender 3.6.13 binary, or its identity/hash does not match the run manifest;
2. the exact object `Armature` is absent, or no `MESH` object has a qualifying `ARMATURE` modifier targeting it;
3. any qualifying object cannot be evaluated at the frozen reference or any target frame;
4. any qualifying object's vertex/polygon/loop/triangle count, index array, winding, object identity, or row order differs from its frozen reference at any target frame;
5. required evaluated coordinates, transforms, topology, hashes, or provenance cannot be recorded without modifying or spatially rematching the asset;
6. the selected object's finite reference-area denominator is zero;
7. the same-configuration reference-frame identity or area-identity check exceeds the already-frozen `1e-5` tolerance;
8. the complete scheduled 150-frame population cannot be preserved and explicitly accounted for.

Ordinary face-level invalidity under the frozen degeneracy/conditioning rules does not by itself make a scene unusable, provided correspondence remains intact, finite reference-area coverage is nonzero, invalid rows/reasons are preserved, and the complete schedule is reported. No post-hoc valid-area threshold may be introduced to rescue or reject a scene.