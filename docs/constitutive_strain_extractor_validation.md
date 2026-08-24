# Constitutive Appearance — Path-A Strain Extractor Validation

## 1. Question and verdict

**Question.** Does the implemented Path-A primitive reproduce the frozen reference-relative surface-strain definition, reject the preregistered invalid fixtures, and operate through a read-only evaluated-mesh Blender wrapper without inspecting Joanna's animation strain?

**Final verdict: PASS — Path A cleared for controlled asset extraction.**

All frozen core gates passed. The Blender 3.6.13 integration smoke test also passed on an in-memory controlled fixture. No Joanna `.blend` file was opened, modified, saved, rendered, or measured. No animation strain distribution was computed.

## 2. Implementation files

- `scripts_local/constitutive/strain/mesh_strain.py`: Blender-independent float64 face-strain primitive, fixed reason-bit schema, and row-preserving invalid output (`scripts_local/constitutive/strain/mesh_strain.py:1-212`). It does not import `bpy`.
- `scripts_local/constitutive/strain/validate_path_a.py`: exact frozen fixtures, statistics, thresholds, and JSON result writer (`scripts_local/constitutive/strain/validate_path_a.py:1-167`).
- `scripts_local/constitutive/strain/blender_extract_path_a.py`: evaluated dependency-graph extraction, deterministic reference triangulation, correspondence checks, object-to-world conversion, hashes, NPZ package, and manifest (`scripts_local/constitutive/strain/blender_extract_path_a.py:55-222`; `scripts_local/constitutive/strain/blender_extract_path_a.py:262-392`).
- `scripts_local/constitutive/strain/validate_blender_smoke.py`: machine-readable verification of the controlled Blender package.
- `scripts_local/constitutive/strain/validation_results.json`: machine-readable frozen core results.
- `scripts_local/constitutive/strain/blender_smoke_results.json`: machine-readable Blender integration result.

## 3. Exact mathematical formulation implemented

For canonical triangle row `f=(a,b,c)`, the implementation constructs

```text
Dm = [Xb-Xa, Xc-Xa]  in R^(3x2)
Ds = [xb-xa, xc-xa]  in R^(3x2)
```

It builds the specified deterministic right-handed reference tangent basis `T=[t1,t2]`, with `t1` along the first nonzero reference edge, then forms `B_ref=T^T Dm`. It solves the transposed linear system for `F_surface` rather than forming an explicit inverse:

```text
F_surface B_ref = Ds
C_surface = sym(F_surface^T F_surface)
```

The ordered eigenvalues of symmetric `C_surface` give

```text
lambda_max = sqrt(mu_max)
lambda_min = sqrt(mu_min)
```

and the authoritative descriptor is

```text
[log(lambda_max),
 log(lambda_min),
 log(lambda_max) + log(lambda_min),
 log(lambda_max) - log(lambda_min)]
```

This is the exact specification at `docs/constitutive_strain_interface_spec.md:143-195`, implemented at `scripts_local/constitutive/strain/mesh_strain.py:117-205`. Translation cancels in relative edges; target rotation cancels in `F^T F`. There is no alignment, recentering, Procrustes fit, spatial rematching, stretch clamp, or alternate strain definition.

## 4. Frozen validation contract

The authoritative contract was `docs/constitutive_strain_validation_prereg.md`, read before implementation. It freezes float64 inputs/outputs and row-preserving NaN invalid records (`docs/constitutive_strain_validation_prereg.md:20-48`), the deterministic two-triangle patch and four positive fixtures (`docs/constitutive_strain_validation_prereg.md:52-138`), absolute `1e-5` stretch and area-identity gates (`docs/constitutive_strain_validation_prereg.md:142-205`), numerical validity rules (`docs/constitutive_strain_validation_prereg.md:209-268`), and three negative fixtures (`docs/constitutive_strain_validation_prereg.md:272-320`). None was changed or supplemented after results were seen.

## 5. Commands actually run

Initial and final repository checks used `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git status --short`, `git diff --check`, and `git diff --stat`. Required documents and implementation were inspected with `sed -n`, `nl -ba`, `rg`, and `ls`.

The validation commands were:

```bash
/home/fmb/miniconda3/envs/lumimotion/bin/python \
  scripts_local/constitutive/strain/validate_path_a.py \
  --output scripts_local/constitutive/strain/validation_results.json

/home/fmb/blender-3.6.13-linux-x64/blender --version

/home/fmb/blender-3.6.13-linux-x64/blender \
  --background --factory-startup \
  --python scripts_local/constitutive/strain/blender_extract_path_a.py -- \
  --self-test --output-dir /tmp/lumimotion_path_a_blender_smoke_v4

/home/fmb/miniconda3/envs/lumimotion/bin/python \
  scripts_local/constitutive/strain/validate_blender_smoke.py \
  --package /tmp/lumimotion_path_a_blender_smoke_v4 \
  --output scripts_local/constitutive/strain/blender_smoke_results.json

/home/fmb/miniconda3/envs/lumimotion/bin/python -m py_compile \
  scripts_local/constitutive/strain/mesh_strain.py \
  scripts_local/constitutive/strain/validate_path_a.py \
  scripts_local/constitutive/strain/blender_extract_path_a.py
```

Three earlier wrapper smoke invocations used the same controlled fixture with output directories `/tmp/lumimotion_path_a_blender_smoke`, `/tmp/lumimotion_path_a_blender_smoke_v2`, and `/tmp/lumimotion_path_a_blender_smoke_v3` while the package manifest was being finalized. They did not open a source `.blend` file. The authoritative recorded smoke result is `v4`.

## 6. Positive fixture results

All values below are the frozen maximum absolute per-face statistics; every positive fixture had `invalid_fraction=0`.

| Fixture | max `lambda_max` error | max `lambda_min` error | Stretch gate |
|---|---:|---:|---|
| Identity | 0 | 0 | PASS |
| Rigid rotation + translation | `1.1102230246251565e-16` | `1.1102230246251565e-16` | PASS |
| 1.10x uniaxial stretch | 0 | 0 | PASS |
| 1.10x stretch, then rigid motion | 0 | `1.1102230246251565e-16` | PASS |

Identity produced exactly `[1,1]` stretches and zero log strain on both faces. The rigid fixture produced unity stretches to floating-point roundoff. Both uniaxial fixtures produced `lambda_max=1.10`, `lambda_min=1.00`, `log_area_change=log(1.10)`, and `log_anisotropy=log(1.10)` to float64 roundoff.

## 7. Area-identity residuals

The frozen statistic is `max(abs(area_deformed/area_reference - lambda_max*lambda_min))`.

| Fixture | Maximum absolute residual | Gate (`<=1e-5`) |
|---|---:|---|
| Identity | 0 | PASS |
| Rigid rotation + translation | `1.1102230246251565e-16` | PASS |
| 1.10x uniaxial stretch | 0 | PASS |
| 1.10x stretch, then rigid motion | `2.220446049250313e-16` | PASS |

## 8. Negative and degeneracy results

| Fixture | Invalid fraction | Required reason present | All lambda/log descriptors NaN | Gate |
|---|---:|---|---|---|
| Collinear reference | 1.0 | `reference_degenerate` | yes | PASS |
| Collapsed target | 1.0 | `target_collapsed` | yes | PASS |
| Nonfinite target coordinate | 1.0 | `nonfinite_target` | yes | PASS |

The collinear fixture also carries `target_collapsed`, because the target supplied by the frozen fixture is the same collinear geometry. This does not repair, obscure, or replace the required reference-degeneracy reason.

## 9. Invalid-reason and row-order behavior

The core preallocates every output at canonical face count and only fills strain fields after all validity checks (`scripts_local/constitutive/strain/mesh_strain.py:69-100`; `scripts_local/constitutive/strain/mesh_strain.py:103-205`). Invalid faces are never removed or reordered. `F_surface`, `C_surface`, both stretches, and all four log-strain quantities remain NaN. A `uint32` bitmask distinguishes nonfinite reference/target input, zero reference scale, reference degeneracy, reference ill-conditioning, target collapse, eigensolver failure, materially negative eigenvalue, nonpositive stretch, and a counted roundoff projection (`scripts_local/constitutive/strain/mesh_strain.py:25-43`).

Out-of-range topology or malformed global array shapes raise an error before computation rather than being spatially repaired (`scripts_local/constitutive/strain/mesh_strain.py:50-65`). Blender correspondence changes likewise fail before an output package is created (`scripts_local/constitutive/strain/blender_extract_path_a.py:154-170`; `scripts_local/constitutive/strain/blender_extract_path_a.py:300-314`).

## 10. Numerical roundoff events

No negative-eigenvalue projection occurred in any frozen core fixture or in the Blender smoke fixture. The largest core numerical deviation was `2.220446049250313e-16` in the area identity.

The Blender smoke fixture recovered maximum stretch errors of `2.6260073004991114e-08` and `3.6087413057828144e-09`; its maximum area residual was `4.440892098500626e-16`. The larger stretch error is consistent with Blender mesh coordinates being exposed at mesh precision before conversion into authoritative float64 computation. It is reported rather than rounded away and remains roughly 380 times below the frozen `1e-5` tolerance.

## 11. Blender wrapper implementation and status

**Status: validated.** The located portable binary reports Blender `3.6.13`, build hash `791bdfd03f07`.

The wrapper:

- requires explicit object names and explicit reference/target frame and subframe for non-self-test use (`scripts_local/constitutive/strain/blender_extract_path_a.py:262-298`);
- evaluates each object through the dependency graph and converts evaluated vertices with the evaluated `matrix_world` (`scripts_local/constitutive/strain/blender_extract_path_a.py:55-130`);
- uses deterministic polygon-index fan triangulation, freezes reference rows, and requires identical vertex/polygon/loop/triangle counts and arrays (`scripts_local/constitutive/strain/blender_extract_path_a.py:76-87`; `scripts_local/constitutive/strain/blender_extract_path_a.py:154-170`);
- writes reference and per-configuration NPZ data in canonical row order plus SHA-256 hashes for source assets, topology, positions, triangles, and extractor code (`scripts_local/constitutive/strain/blender_extract_path_a.py:173-222`; `scripts_local/constitutive/strain/blender_extract_path_a.py:322-384`);
- never calls a Blender save operator and refuses to overwrite an existing output directory.

The integration fixture was created entirely in memory under `--factory-startup`: the frozen two-triangle patch, a 1.10x X shape-key deformation, and the frozen nontrivial rigid transform. It exercised reference frame 1 and target frame 2 through the complete evaluated-geometry/export/load/compute path. Both faces were valid and all smoke thresholds passed. This validation did not inspect topology or strain from Joanna's assets.

## 12. Specification and preregistration discrepancies

**Interface specification discrepancy: none found.** The implementation uses the defined reference-relative face map, common log descriptor, world-coordinate convention, row-preserving invalid semantics, face-authoritative outputs, and manifest provenance. The wrapper makes the triangulation convention explicit and geometry-independent so target deformation cannot silently choose another diagonal.

**Frozen preregistration discrepancy: none found.** Fixture geometry, transform order and angles, translation, dtype, thresholds, validity criteria, required statistics, and verdict meanings were retained unchanged.

## 13. Unexpected observations and scientific boundary

The only unexpected runtime observation was a harmless PulseAudio `pa_write()` warning from background Blender; Blender completed normally with exit code zero and a valid package. The controlled Blender mesh path introduced the small coordinate-precision error reported in Section 10; it did not threaten a gate.

No strain histogram, percentile, visualization, ranking, frame selection, or deformation-regime measurement was computed for hook, jumpingjacks, mouse, standup, or spheres-with-rotations. No strain-to-roughness law was selected and no appearance hypothesis was tested.

## 14. Final verdict

**PASS**

Path A cleared for controlled asset extraction. This verdict establishes implementation and integration correctness on the frozen fixtures only. It does not establish Joanna-scene topology stability, select an asset/reference configuration, claim that the reference is stress-free, or authorize inspection of an animation strain distribution.
