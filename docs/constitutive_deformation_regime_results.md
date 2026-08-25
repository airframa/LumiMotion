# Constitutive Appearance — Deformation-Regime Characterization Results

**Status:** COMPLETE  
**Result type:** preregistered descriptive characterization  
**Authoritative preregistration:** `docs/constitutive_deformation_regime_prereg.md`  
**Canonical result:** the completed Blender 3.6.13 characterization is retained; its evaluated geometry and Path-A strain were subsequently cross-version validated exactly against Blender 4.4.0 by `docs/constitutive_blender_version_fidelity_results.md`.

## 1. Question

What range and spatial prevalence of validated reference-relative surface deformation exists in Joanna's four armature-driven LumiMotion character animations?

This measurement characterizes the deformation support available for a later constitutive-appearance signal test. It does **not** establish stress-free physical strain, material realism, deformation-dependent reflectance, or image observability.

## 2. Frozen population

All four frozen scenes were evaluated at every scheduled integer frame:

- `hook`: reference frame 1, targets 1–150;
- `jumpingjacks`: reference frame 1, targets 1–150;
- `mouse`: reference frame 1, targets 1–150;
- `standup`: reference frame 75, targets 1–150.

The authoritative unit is a valid face × target-frame observation, with canonical reference-face-area weighting for primary prevalence summaries.

Across all scenes:

- expected observations: **19,612,200**;
- valid observations: **19,611,966**;
- invalid observations: **234**;
- all invalid observations were the preregistered `target_collapsed` case in `standup`;
- no scene failed the frozen topology/correspondence schedule.

## 3. Primary deformation support

| scene | weighted p95 λmax | weighted p99 λmax | weighted p05 λmin | weighted p01 λmin | area λmax ≥ 1.10 | area λmin ≤ 0.90 | invalid obs. |
|---|---:|---:|---:|---:|---:|---:|---:|
| `hook` | 1.152427 | 1.372028 | 0.875007 | 0.772781 | 8.16% | 7.12% | 0 |
| `jumpingjacks` | 1.117700 | 1.316147 | 0.809415 | 0.557303 | 6.23% | 10.06% | 0 |
| `mouse` | 1.201530 | 1.529021 | 0.793389 | 0.626324 | 12.31% | 12.19% | 0 |
| `standup` | 1.040374 | 1.112822 | 0.957829 | 0.899170 | 1.24% | 1.02% | 234 |

Scene-wide valid reference-area fractions were numerically 1 to floating-point precision:
`hook=0.999999999999996`,
`jumpingjacks=1.000000000000002`,
`mouse=1.000000000000004`,
`standup=0.999999999703607`.

## 4. Interpretation

### Established

1. **The available animation set contains nontrivial localized deformation.**
   `hook`, `jumpingjacks`, and `mouse` all have substantial area-weighted extension/compression tails. This is not explained only by dense tessellation because the primary statistic is canonical reference-area weighted.

2. **The deformation is spatially/time localized rather than globally stretching the whole character.**
   The medians remain near identity while upper/lower tails are substantial. This is useful for a later signal test because the same animations contain low- and high-deformation states.

3. **The four-scene extraction is operationally usable.**
   All 150 scheduled frames completed for every scene, topology/canonical-row correspondence remained stable, and only 234 of 19,612,200 observations were invalid (`standup`, `target_collapsed`).

4. **The deformation-support concern is cleared for the next scientific gate.**
   There is enough measured reference-relative deformation in the sandbox to ask whether an independently justified deformation→reflectance response would be observable.

### Not established

This result does **not** show that:

- Mixamo/skinning strain is a stress-free physical material strain;
- the animation is a faithful cloth simulation;
- real materials exhibit a particular reflectance response over these ranges;
- any deformation-dependent reflectance signal is visible in the LumiMotion capture regime;
- Path-B/Gaussian strain estimation is ready or necessary.

The references are configuration-relative, not guaranteed stress-free states.

## 5. Consequence for the project

The next question is no longer “do the available animations deform enough to test the idea?”

The next question is:

> **What deformation-dependent reflectance response is independently supported by material physics, and would that response be large enough to survive a strong time-invariant material baseline under the intended imaging conditions?**

Do not implement Path B or modify LumiMotion training/material code on the basis of this characterization alone.

## 6. Provenance

Primary machine-readable evidence remains private under:

```text
outputs_constitutive/deformation_regime_v1/
```

with the compact summary:

```text
deformation_regime_summary.json
```

The later Blender-version validation established exact evaluated-geometry/strain equivalence between the retained 3.6.13 baseline and Blender 4.4.0 for the frozen four-scene population.
