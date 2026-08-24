# Constitutive Appearance — Path-A Strain Extractor Validation Preregistration

**Status:** Frozen before Path-A implementation/validation  
**Scope:** Numerical and integration validation of the reference-relative mesh strain extractor only  
**Not a scientific Gate 1 test:** No strain-to-BRDF law, appearance rendering, or Joanna animation strain distribution is authorized by this document.

---

## 1. Purpose

The purpose of this validation is to establish that the Path-A extractor implements the deformation definition in `docs/constitutive_strain_interface_spec.md` correctly and is invariant to rigid motion.

No threshold or fixture in this document may be changed after validation results are inspected in order to turn a failure into a pass.

If a frozen gate fails, diagnose the implementation first.

---

## 2. Authoritative numeric convention

All authoritative strain computation and validation uses:

```text
float64
```

The core strain implementation is Blender-independent and consumes:

```text
reference_positions : [V,3]
target_positions    : [V,3]
triangles           : [F,3]
```

The authoritative quantities are:

```text
lambda_max
lambda_min
log_stretch_max
log_stretch_min
log_area_change
log_anisotropy
valid
invalid_reason
```

Invalid records remain in canonical face-row order and all numerical strain descriptors for them are `NaN`.

---

## 3. Positive validation fixtures

Use the deterministic planar reference patch:

```text
v0 = (0, 0, 0)
v1 = (1, 0, 0)
v2 = (1, 1, 0)
v3 = (0, 1, 0)

triangles:
(0, 1, 2)
(0, 2, 3)
```

No random geometry is used for the primary validation gates.

### 3.1 Identity fixture

Target positions equal the reference positions exactly.

Expected for every valid face:

```text
lambda_max = 1
lambda_min = 1
log_strain = [0, 0, 0, 0]
```

### 3.2 Rigid-motion fixture

Apply:

```text
R = Rz(37 degrees) @ Ry(-23 degrees) @ Rx(19 degrees)

translation = (0.37, -1.20, 2.50)
```

to every reference vertex.

Expected for every valid face:

```text
lambda_max = 1
lambda_min = 1
log_strain = [0, 0, 0, 0]
```

No alignment, recentering, or Procrustes correction is permitted.

### 3.3 Uniaxial-stretch fixture

Apply the authored deformation:

```text
x' = 1.10 * x
y' = 1.00 * y
z' = z
```

Expected ordered stretches for every valid face:

```text
lambda_max = 1.10
lambda_min = 1.00
```

Expected:

```text
log_area_change = log(1.10)
log_anisotropy  = log(1.10)
```

### 3.4 Uniaxial stretch followed by rigid motion

First apply the exact deformation from §3.3, then apply the exact rigid transform from §3.2.

Expected ordered stretches remain:

```text
lambda_max = 1.10
lambda_min = 1.00
```

This fixture verifies that the recovered strain is independent of world-space orientation and translation.

---

## 4. Frozen positive-gate statistics and thresholds

Positive fixtures must contain:

```text
invalid_fraction = 0
```

### 4.1 Identity and rigid-motion gates

Primary statistics:

```text
max(abs(lambda_max - 1.0))
max(abs(lambda_min - 1.0))
```

Pass iff:

```text
max(abs(lambda_max - 1.0)) <= 1e-5
max(abs(lambda_min - 1.0)) <= 1e-5
invalid_fraction == 0
```

### 4.2 Uniaxial and uniaxial-plus-rigid gates

Primary statistics:

```text
max(abs(lambda_max - 1.10))
max(abs(lambda_min - 1.00))
```

Pass iff:

```text
max(abs(lambda_max - 1.10)) <= 1e-5
max(abs(lambda_min - 1.00)) <= 1e-5
invalid_fraction == 0
```

### 4.3 Area identity

For every valid positive fixture, verify:

```text
area_ratio   = area_deformed / area_reference
stretch_area = lambda_max * lambda_min
```

Primary statistic:

```text
max(abs(area_ratio - stretch_area))
```

Pass iff:

```text
max(abs(area_ratio - stretch_area)) <= 1e-5
```

These are absolute tolerances on dimensionless quantities.

---

## 5. Frozen numerical validity criteria

The implementation must use stable float64 linear algebra.

For each reference triangle define:

```text
L = max(norm(edge_1), norm(edge_2))
```

and the dimensionless reference-area quality:

```text
q_area_ref = norm(cross(edge_1, edge_2)) / L^2
```

when `L > 0`.

A reference face is invalid if:

```text
L == 0
q_area_ref <= 1e-12
condition_number(B_ref) > 1e8
```

or if any required quantity is nonfinite.

For the target configuration, define:

```text
q_area_target =
    norm(cross(target_edge_1, target_edge_2)) / L^2
```

using the frozen reference `L`.

The target face is invalid if:

```text
q_area_target <= 1e-12
```

or if any required quantity is nonfinite.

The symmetric tensor used for principal stretches must be treated explicitly as symmetric numerically.

A negative eigenvalue is considered a numerical-roundoff candidate only when:

```text
mu >= -1e-12 * max(1, mu_max)
```

Such an event must still be counted and reported.

A materially more negative eigenvalue is an implementation/numerical failure.

Any resulting non-positive principal stretch is invalid because log strain is undefined.

No empirical threshold may be selected from Joanna's animation data.

---

## 6. Negative / degeneracy fixtures

### 6.1 Degenerate reference triangle

Use:

```text
v0 = (0, 0, 0)
v1 = (1, 0, 0)
v2 = (2, 0, 0)
```

The three vertices are collinear.

Expected:

```text
invalid_fraction = 1.0
```

No finite `lambda` or log-strain descriptor may be emitted.

The invalid reason must identify reference degeneracy/rank failure.

### 6.2 Collapsed target triangle

Use a valid nondegenerate reference triangle, then make two target vertices coincident so the target triangle has zero area.

Expected:

```text
invalid_fraction = 1.0
```

No finite `lambda` or log-strain descriptor may be emitted.

The invalid reason must identify target collapse/rank failure.

### 6.3 Nonfinite coordinate fixture

Inject one `NaN` into a required target vertex coordinate.

Expected:

```text
invalid_fraction = 1.0
```

for every affected face, with a nonfinite-input invalid reason.

---

## 7. Blender integration convention

Path A separates:

```text
Blender geometry extraction
from
Blender-independent strain computation
```

For the geometry-only Blender wrapper, the intended binary is:

```text
Blender 3.6.13
```

because this is the known-safe reader for the author-shared main `.blend` files.

The exact executable path, reported Blender version/build hash, platform, and dependency-graph evaluation state must be recorded by the wrapper manifest.

The wrapper must:

- evaluate the dependency-graph mesh;
- use explicit object names;
- apply the evaluated object-to-world matrix;
- preserve/freeze reference triangulation and vertex correspondence;
- never save or modify the source `.blend`;
- fail rather than spatially rematch changed topology.

If Blender 3.6.13 is not locally available, the core-math validation may still run, but the integration verdict must remain `PARTIAL`.

---

## 8. Joanna-asset boundary

No Joanna animation strain distribution may be inspected during this validation task.

The Path-A implementation must be asset-independent.

Before the first extraction from Joanna's assets, separately freeze:

- exact source `.blend` asset;
- evaluated mesh object(s) and order;
- reference frame/subframe;
- target frame set;
- topology hashes.

Those choices must be made without inspecting strain magnitude.

The reference configuration is a reference state, not assumed to be a stress-free physical rest state.

---

## 9. Validation verdict

The implementation report must end with exactly one of:

### PASS

Path A cleared for controlled asset extraction.

### PARTIAL

Core numerical gates pass, but required Blender integration remains unvalidated.

### FAIL

At least one frozen validation gate fails. Do not inspect Joanna animation strain.

No threshold in this document may be relaxed after seeing the validation result without recording the original failure and creating a new version of the validation contract.
