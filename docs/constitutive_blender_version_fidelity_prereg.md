# Constitutive Appearance — Blender-Version Geometry/Strain Fidelity Preregistration

**Status:** Frozen before any Blender 4.4.0 asset evaluation or fidelity result  
**Scope:** Blender 3.6.13 versus 4.4.0 evaluated-character-geometry and Path-A strain fidelity  
**Baseline:** Completed immutable Blender 3.6.13 deformation-regime packages  
**Not Gate 1:** No appearance, BRDF, rendering, training, or constitutive-material hypothesis is tested here

## 1. Question and purpose

**QUESTION.** Does evaluated character geometry, and therefore Path-A
reference-relative strain, change materially when the exact Joanna assets are
evaluated with Blender 4.4.0 instead of the Blender 3.6.13 binary used for the
completed deformation-regime characterization?

**FROZEN.** The purpose of this comparison is to decide whether the already
completed 3.6.13 deformation characterization can be retained. The current
3.6.13 packages under
`outputs_constitutive/deformation_regime_v1/` are immutable baseline evidence.
They must not be regenerated, modified, repaired, or overwritten during the
future comparison.

**FROZEN.** A future 4.4.0 run must use the same source assets, evaluated-world-
coordinate convention, object-selection rule, frame schedule, Path-A
mathematics, float64 computation, validity rules, and non-interpolated analysis
convention as the baseline. Path A uses evaluated vertices transformed by the
evaluated object-to-world matrix, with no alignment or normalization
(`docs/constitutive_deformation_regime_prereg.md:62-75`), and canonical face-row
correspondence is authoritative (`docs/constitutive_deformation_regime_prereg.md:79-91`).

## 2. Read-only forensic audit of the completed 3.6.13 run

### 2.1 Mechanical parsing rule

**FROZEN EVIDENCE PROCEDURE.** `full_run.log` was partitioned at the exact lines
`Launching frozen scene extraction: <scene>`. Within each scene segment, exact
substring counts were computed for the three named warnings. Frame completion
was parsed only from full-line matches of `Completed frame NNN`; the audit
required the set `{1,...,150}`, no duplicates, and 150 records. All remaining
lines were checked mechanically for `warning`, `error`, `failed`, `exception`,
or `traceback`, case-insensitively.

### 2.2 Observed warning and completion record

| Scene | `404.32` warning | Count | Region type 14 | Region type 15 | Other Blender warnings/errors | Frames completed | Source asset SHA-256 |
|---|---|---:|---:|---:|---|---|---|
| `hook` | yes | 1 | 14 | 14 | none in the scene log segment | exactly 1–150; 150 unique records | `bb3949b4849661fa3df64eb149896978fe124f109b921e94850207788881e084` |
| `jumpingjacks` | yes | 1 | 14 | 14 | none in the scene log segment | exactly 1–150; 150 unique records | `d9b58009bf55594edd204b7ee2627f342b89c43891b6f453fd50e1227f97cf82` |
| `mouse` | yes | 1 | 14 | 14 | none in the scene log segment | exactly 1–150; 150 unique records | `db554ac925521769312b659397614c1e0920ac7ce1d8467f97caa652126bee78` |
| `standup` | yes | 1 | 14 | 14 | none in the scene log segment | exactly 1–150; 150 unique records | `ff7a7d6f78255ee6f4996fa717ea6a54ca19788b80e5254d65be4ffb667985b5` |

**VERIFIED.** The hook warning block and newer-binary warning occupy
`outputs_constitutive/deformation_regime_v1/full_run.log:4-32`; frame 150 is
recorded at line 182. The corresponding newer-binary warnings occur for
jumpingjacks, mouse, and standup at lines 214, 396, and 578, with their frame-150
records at lines 364, 546, and 728. Each scene manifest independently records
`status: complete`, `completed_frame_count: 150`, target endpoints `[1,150]`,
and the source hashes above
(`outputs_constitutive/deformation_regime_v1/scenes/hook/scene_manifest.json:10-10`,
`:155-170`; `outputs_constitutive/deformation_regime_v1/scenes/jumpingjacks/scene_manifest.json:10-10`,
`:395-410`; `outputs_constitutive/deformation_regime_v1/scenes/mouse/scene_manifest.json:10-10`,
`:95-110`; `outputs_constitutive/deformation_regime_v1/scenes/standup/scene_manifest.json:10-10`,
`:515-530`). Each manifest also records that the source blend was not saved or
modified.

**VERIFIED HISTORICAL DISAGREEMENT.** The historical survey states that only
`hook150_v5_specular32.blend` emitted the `404.32` warning
(`docs/miscellaneous/blend_files_survey.md:21-25`). The completed measurement
log instead records that warning once for every one of the four frozen base
scenes. The current log therefore does not reproduce the historical warning
pattern. The available evidence establishes the disagreement but not its cause;
no causal explanation is adopted by this preregistration.

**UNKNOWN.** Warning text and successful extraction alone do not establish
whether Blender 3.6.13 and 4.4.0 produce identical evaluated geometry. That is
the question of the frozen comparison below.

## 3. Comparator environment

**VERIFIED.** The exact comparator executable
`/home/fmb/blender-4.4.0-linux-x64/blender` exists and is executable. Running
only `--version` reported:

```text
Blender 4.4.0
build date: 2025-03-18
build time: 03:01:40
build commit date: 2025-03-17
build commit time: 17:00
build hash: 05377985c527
build branch: blender-v4.4-release
build platform: Linux
build type: Release
```

No `.blend` file was opened with this binary while preparing this document.

## 4. Frozen assets and selection rule

**FROZEN.** Compare all and only these exact source assets:

| Scene ID | Asset |
|---|---|
| `hook` | `blend_files/blendfiles_v5_specular32/hook150_v5_specular32.blend` |
| `jumpingjacks` | `blend_files/blendfiles_v5_specular32/jumpingjacks_v5_specular32.blend` |
| `mouse` | `blend_files/blendfiles_v5_specular32/mouse_v5_specular32.blend` |
| `standup` | `blend_files/blendfiles_v5_specular32/standup150_v5_specular32.blend` |

**FROZEN.** In each scene, select every object for which:

1. `object.type == 'MESH'`; and
2. at least one modifier has `modifier.type == 'ARMATURE'` and a non-null target
   object whose exact object name is `Armature`.

Resolved names are sorted by Python's default Unicode string order, exactly as
in the completed characterization (`docs/constitutive_deformation_regime_prereg.md:34-45`).
No object may be manually added, removed, substituted, merged, or reordered.

**FROZEN BASELINE IDENTITIES.** The 4.4.0 run must reproduce the source SHA-256
values in Section 2.2 before evaluation. A source mismatch is structural
failure, not a new comparison dataset.

## 5. Frozen configuration schedule

All configurations use integer frames and `subframe = 0.0`:

| Scene | Reference | Targets |
|---|---:|---|
| `hook` | 1 | every frame 1–150 inclusive |
| `jumpingjacks` | 1 | every frame 1–150 inclusive |
| `mouse` | 1 | every frame 1–150 inclusive |
| `standup` | 75 | every frame 1–150 inclusive |

**FROZEN.** All 150 target frames are used. No frame is selected, ranked,
excluded, or subsampled using the existing strain results. Reference
configurations remain reference-relative zeros and are not asserted to be
stress-free (`docs/constitutive_deformation_regime_prereg.md:47-60`).

## 6. Frozen prediction

If the Blender 3.6.13 compatibility warnings are harmless for evaluated
geometry, the following are predicted:

1. selected object names and order match exactly;
2. evaluated topology and canonical triangle rows match exactly at every frame;
3. both versions pass the existing reference-identity gates;
4. cross-version Path-A strain is numerically equivalent;
5. the frozen deformation-regime summaries are unchanged within the tolerances
   in Section 10.

These are predictions to test, not conclusions from the warning audit.

## 7. Structural gate

**FROZEN GATE.** Require exact equality between the immutable 3.6.13 baseline
and the future 4.4.0 package for:

- selected object names and order;
- source asset SHA-256;
- reference frame, subframe, and complete target-frame schedule;
- vertex count per corresponding scene/object/frame;
- polygon count per corresponding scene/object/frame;
- loop count per corresponding scene/object/frame;
- triangle count per corresponding scene/object/frame;
- canonical triangle vertex-index arrays must have exactly identical integer
  values, shape, winding, and row order. Integer storage dtype/width is recorded
  diagnostically but does not itself constitute a structural mismatch when the
  represented index values and shape are exactly identical.

The comparison must account for every selected object and every frame. No
spatial rematching, nearest-neighbour correspondence, retessellation,
reordering, winding correction, topology repair, or partial-scene summary is
permitted. Any structural mismatch is **FAIL**.

## 8. Blender 4.4.0 reference-integrity gate

**FROZEN GATE.** Independently under Blender 4.4.0, at each scene's frozen
same-configuration reference frame, require across every otherwise valid face:

```text
max abs(lambda_max - 1.0) <= 1e-5
max abs(lambda_min - 1.0) <= 1e-5
max area-identity residual <= 1e-5
```

Invalidity, accounting, and the area residual retain the existing frozen Path-A
definitions. These thresholds are the existing extraction-integrity gates
(`docs/constitutive_deformation_regime_prereg.md:230-250`) and must not change.
Any reference-integrity failure is **FAIL**.

## 9. Local strain-fidelity gate

For each corresponding face/frame observation valid in both versions, define

```text
d_epsilon = max(
    abs(log_stretch_max_44 - log_stretch_max_36),
    abs(log_stretch_min_44 - log_stretch_min_36)
)
```

**FROZEN POPULATION.** Correspondence is by exact
`(scene_id, object_name, frame, canonical_face_row)` after the structural gate;
no spatial association is allowed. Report the number of observations valid in
both versions, valid only in 3.6.13, valid only in 4.4.0, and invalid in both.
The latter three are diagnostic accounting and are not silently discarded.

**FROZEN WEIGHT.** Weight each jointly valid observation by its immutable
3.6.13 canonical `area_reference` value. Using one fixed baseline weight avoids
allowing version-dependent reference areas to change the definition of the
cross-version local-error distribution. Weights must be finite and positive.

**FROZEN STATISTICS.** For each scene separately, report the reference-area-
weighted `p50`, `p95`, `p99`, and `max` of `d_epsilon`. Percentiles use the same
left-continuous, non-interpolated inverse empirical CDF as the deformation-
regime preregistration (`docs/constitutive_deformation_regime_prereg.md:106-114`).
The maximum is diagnostic and must be reported.

**FROZEN PRIMARY LOCAL GATE.** For every scene:

```text
p99(d_epsilon) <= 1e-4
```

No other local statistic may replace this gate after results are observed.

## 10. Frozen-summary fidelity gate

**FROZEN PROCEDURE.** Recompute the exact preregistered deformation-regime
analysis separately from the complete Blender 4.4.0 packages. Do not reuse
3.6.13 summary values as 4.4.0 inputs. Preserve the existing per-scene
populations, Path-A validity, reference-area weighting, asymmetric
`lambda_max`/`lambda_min` tails, and non-interpolated inverse empirical CDF
(`docs/constitutive_deformation_regime_prereg.md:117-190`). There is no pooled
four-scene statistic.

For every scene compare every preregistered:

- primary reference-area-weighted percentile;
- secondary unweighted percentile;
- descriptive `lambda_max` and `lambda_min` reference-area fraction;
- scene-wide valid-reference-area fraction.

**FROZEN GATES.** Require all of the following:

```text
every strain/log-strain percentile absolute difference <= 1e-4
every descriptive area-fraction absolute difference <= 1e-4
scene valid-reference-area-fraction absolute difference <= 1e-6
```

“Every strain/log-strain percentile” includes every frozen percentile of
`lambda_max`, `lambda_min`, `abs(log_stretch_max)`,
`abs(log_stretch_min)`, `abs(log_area_change)`, `log_anisotropy`, and
`max_abs_log_stretch`, under both weighted and unweighted summaries. A failed
summary comparison makes the verdict **FAIL**.

The comparison output must preserve, for each statistic, the 3.6.13 value,
4.4.0 value, signed difference, absolute difference, tolerance, and Boolean
gate result, together with all numerator, denominator, weight-sum, and sample-
count provenance available from each separately computed summary.

## 11. Raw evaluated-geometry diagnostic

For corresponding evaluated world-space vertices define

```text
d_x = norm(x_44 - x_36) / reference_bbox_diagonal
```

**FROZEN DENOMINATOR.** `reference_bbox_diagonal` is the Euclidean diagonal of
the axis-aligned world-space bounding box of the immutable 3.6.13 reference
positions for the corresponding object. The same nonzero denominator is used
for all 150 frames of that object.

**FROZEN DIAGNOSTIC.** For each scene/object, pool all corresponding scheduled
frame/vertex values and report `median`, `p95`, `p99`, and `max`. Use the
non-interpolated inverse empirical-CDF convention for the three quantiles. Also
report frame count, vertex count per frame, total sample count, denominator,
and any nonfinite count.

This diagnostic is not a primary verdict gate because Path A is invariant to a
shared rigid transformation. No translation removal, rotation alignment,
Procrustes correction, rescaling, or other alignment is permitted in the
authoritative comparison. A zero or nonfinite reference bounding-box diagonal
makes this diagnostic undefined and must be reported; it does not authorize a
replacement normalization.

## 12. Required future comparison record

**FROZEN.** The future implementation/run must preserve:

- immutable references to the existing 3.6.13 run and scene manifests and
  their SHA-256 hashes;
- exact 4.4.0 binary path, version, build hash, platform, command line, and code
  hashes;
- source asset paths, sizes, and SHA-256 values;
- selected object names/order and qualifying modifiers;
- all reference/target geometry, topology counts/hashes, face-row arrays,
  validity masks/reasons, and Path-A outputs needed to reproduce every gate;
- per-scene structural, reference-integrity, local-strain, summary-fidelity,
  and raw-geometry records, including null/failure outcomes;
- an explicit assertion that no source `.blend` was saved or modified.

The 4.4.0 outputs must use a new private output root. They must never overwrite
or be written inside the immutable 3.6.13 baseline tree. Source assets and
evaluated geometry packages remain private and untracked.

## 13. Frozen verdict

Exactly one verdict is emitted across all four scenes.

### PASS

- structural gate passes;
- Blender 4.4.0 reference-integrity gate passes;
- local `p99` strain gate passes for every scene;
- all frozen-summary gates pass.

**Interpretation:** the completed 3.6.13 deformation characterization is
cross-version validated and may be retained.

### PARTIAL

- structural gate passes;
- Blender 4.4.0 reference-integrity gate passes;
- all frozen scene-summary gates pass;
- but the local `p99` strain gate fails for at least one scene.

**Interpretation:** the existing descriptive characterization may be retained,
but 3.6.13 per-face strain must not be used for later local
constitutive/material coupling. Future quantitative work uses Blender 4.4.0
geometry.

### FAIL

- any structural mismatch; or
- any Blender 4.4.0 reference-integrity failure; or
- any frozen scene-summary fidelity gate failure.

**Interpretation:** the completed 3.6.13 characterization is not accepted as
canonical and must be recomputed/replaced with Blender 4.4.0 output before
proceeding.

The local gate cannot downgrade a condition already defined as FAIL. No
threshold may be relaxed after observing 4.4.0 results without preserving the
original verdict and creating a new preregistration version.

## 14. Future Blender-version policy

**FROZEN PRE-RESULT DECISION.** Assuming Blender 4.4.0 is locally available and
passes its internal reference-integrity checks, future quantitative Blender
constitutive-appearance experiments will use Blender 4.4.0 for both geometry
evaluation and rendering. This comparison decides only whether the already
completed 3.6.13 deformation characterization can be retained.

## 15. Scientific and execution boundaries

This is a version-fidelity check, not Gate 1 and not an appearance experiment.
It does not choose a strain-to-reflectance law, establish whether deformation is
scientifically sufficient, test material response, alter Path A, implement Path
B, render, or train. Existing deformation-regime results cannot be used to
subsample the version comparison.

While preparing this preregistration, no Joanna asset was opened, no geometry
was extracted, no new strain was computed, and no comparison implementation was
created. The only Blender invocation was:

```bash
/home/fmb/blender-4.4.0-linux-x64/blender --version
```

Read-only evidence inspection used `sed`, `nl`, `rg`, `find`, `wc`, and Python
JSON/text parsing. Existing private outputs and preregistrations were not
modified.
