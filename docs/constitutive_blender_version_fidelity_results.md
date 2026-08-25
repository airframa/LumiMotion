# Constitutive Appearance — Blender-Version Geometry/Strain Fidelity Results

**Status:** COMPLETE  
**Frozen verdict:** **PASS**  
**Authoritative preregistration:** `docs/constitutive_blender_version_fidelity_prereg.md`  
**Comparator:** Blender 3.6.13 (`791bdfd03f07`) vs Blender 4.4.0 (`05377985c527`)

## 1. Why this check existed

The completed 3.6.13 deformation-regime extraction emitted:

```text
Warning: File written by newer Blender binary (404.32), expect loss of data!
```

for all four frozen source assets, contradicting an earlier survey that had reported the warning only for `hook`.

Because the warning could in principle indicate version-dependent evaluated geometry, a preregistered cross-version instrument check was run before using local strain in any constitutive-appearance experiment.

A first attempt (`blender_version_fidelity_v1`) failed at Blender-worker CLI dispatch before geometry extraction and produced **no scientific verdict**. It is preserved as failed-execution provenance. The corrected `v2` run is the canonical comparison.

## 2. Frozen verdict

All four global gates passed:

- structural equality: **PASS**;
- Blender 4.4.0 reference integrity: **PASS**;
- local `p99(d_epsilon) <= 1e-4`: **PASS**;
- complete frozen-summary fidelity: **PASS**.

Therefore the preregistered global verdict is:

# PASS

The completed Blender 3.6.13 deformation characterization is cross-version validated and may be retained.

## 3. The result is exact, not merely within tolerance

| scene | jointly valid | invalid in both | valid only 3.6 | valid only 4.4 | p99 dε | max dε | max raw dx | max summary Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `hook` | 1,706,400 | 0 | 0 | 0 | 0.0e+00 | 0.0e+00 | 0.0e+00 | 0.0e+00 |
| `jumpingjacks` | 8,019,000 | 0 | 0 | 0 | 0.0e+00 | 0.0e+00 | 0.0e+00 | 0.0e+00 |
| `mouse` | 1,826,100 | 0 | 0 | 0 | 0.0e+00 | 0.0e+00 | 0.0e+00 | 0.0e+00 |
| `standup` | 8,060,466 | 234 | 0 | 0 | 0.0e+00 | 0.0e+00 | 0.0e+00 | 0.0e+00 |

Across the full comparison:

- jointly valid face/frame observations: **19,611,966**;
- invalid in both versions: **234**;
- valid in only one version: **0**;
- raw evaluated-world-vertex diagnostic maximum: **0.0e+00**;
- local Path-A strain difference `d_epsilon`: **0 at p50/p95/p99/max for every scene**;
- frozen summary comparisons checked: **288**;
- nonzero frozen summary differences: **0**.

Thus Blender 3.6.13 and 4.4.0 produced **bitwise/numerically identical evaluated world-space vertex positions for the compared packages and exactly identical Path-A strain summaries** for this frozen population.

## 4. Reference integrity under Blender 4.4.0

The worst 4.4.0 same-configuration identity errors across all frozen objects/scenes were:

- max `abs(lambda_max - 1)`: **5.156e-12**;
- max `abs(lambda_min - 1)`: **7.783e-14**;
- max area-identity residual: **5.078e-12**.

All are far below the frozen `1e-5` reference-integrity threshold.

## 5. What the 404.32 warning means after this result

The warning still appears when Blender 4.4.0 opens all four assets, because the files contain content associated with a newer 4.4.32-era binary.

For the **specific quantities tested here**—selected armature-driven evaluated mesh geometry, topology/canonical correspondence, world-space vertices, and Path-A reference-relative strain—the warning has no measurable effect between Blender 3.6.13 and 4.4.0.

Do **not** generalize this result to every Blender subsystem. It does not prove equivalence of:

- rendering;
- shader/material-node evaluation;
- Cycles behavior;
- color management;
- arbitrary linked/appended data;
- future Blender versions.

## 6. Future version policy

Per the pre-result decision in the fidelity preregistration:

> **Future quantitative Blender constitutive-appearance experiments use Blender 4.4.0 for both geometry evaluation and rendering**, assuming the experiment-specific internal checks pass.

The reason is consistency with the LumiMotion quantitative pipeline and removal of version mixing. The existing 3.6.13 deformation characterization is nevertheless accepted as canonical because this comparison validated it exactly.

## 7. Consequence for the research program

The Blender-version concern is closed.

No further geometry/version experiment is warranted before the material-response question. Reopening this checkpoint would require a new concrete inconsistency, not general caution.

The next phase is independent material-response calibration followed by a frozen Gate-1 signal/observability preregistration. Path B and LumiMotion material/training changes remain deferred.
