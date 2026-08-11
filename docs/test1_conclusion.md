# Test 1 — Conclusion

**Status:** Complete. Question answered.
**Verdict:** The hypothesised error is **real and quantified**, but its effect on
rendered images is **negligible in these benchmark scenes** — because those scenes
contain very little indirect light. This is a measurement about *the benchmark*, not
a refutation of the mechanism.

---

## 1. What Test 1 asked

LumiMotion (CVPR'26 Highlight) rebuilds its BVH per frame, so transport *geometry*
is frame-aware. But the radiance a traced ray picks up comes from
`_albedo_dc_stage1` — a canonical, frame-independent per-Gaussian SH bank. Transport
*content* is frozen.

**Hypothesis:** under fixed lighting with deforming geometry, a surfel's true
outgoing radiance changes (its normal rotates w.r.t. the light, its self-shadowing
changes). Freezing it should therefore produce measurable, deformation-scaled error.

---

## 2. The causal chain (all four links measured)

| # | Claim | Measured | Status |
|---|---|---|---|
| 1 | Relative error in stored radiance is **large** | 8% @ median rotation (8.7°), 49% @ p90 (49.6°), 93% @ p99 (91.2°); 15–112% under occlusion | ✅ TRUE |
| 2 | That error is **genuinely present** per-Gaussian | 61% (jumpingjacks) / 75% (standup) of dynamic Gaussians show residual magnitude tracking their own rotation | ✅ TRUE |
| 3 | Indirect light is a **small fraction** of these images | mean 2.8% (jumpingjacks) / 9.6% (standup) of total linear radiance | ✅ TRUE |
| 4 | Therefore render error is **below the noise floor** | implied 0.12–0.45% (jj) / 0.89–4.92% (standup) vs. measured reconstruction error 2.4–5.4% / 5.5–13.2% | ✅ TRUE |

**Nothing is left unexplained.** The renders are good *because* the images have
little indirect light in them, not because the transport model is right.

**The chain has exactly one free parameter: indirect fraction.** Implied render
error scales linearly with it. That single number determines whether the effect
matters in any given scene.

---

## 3. How we got there (four probes, two of which were wrong)

### Probe B — visual (`L_ind` dump, bullet-time camera)
Instrumented `render_ir.py:517` to dump `local_incident_lights`; rendered all 150
frames from a fixed camera with per-frame `update_bvh`.

**Result:** the indirect channel *does* brighten as arms approach the torso and fade
as they separate. **This looked like a refutation but was not informative** — the
brightening is produced by *visibility* change (which surfel a ray hits), which
LumiMotion handles correctly. It would look identical whether stored radiance were
frozen or perfectly updated. The probe tested the part they get right.

**Lesson:** the error is second-order — about the *magnitude* of the bounce, not its
presence.

### Probe D — signed render error vs. GT
Correlated signed render-vs-GT residual against `L_ind` magnitude, at the training
light and then at the held-out relight.

**Result:** weak and confound-dominated. r(residual, L_ind) = +0.051 / +0.104 at the
training light; albedo error correlated 4–6× more strongly. Under novel illumination
the correlation strengthened (+53% / +123%) and the albedo gap narrowed
(3.0×→2.2×, 4.5×→2.5×) — the one result not explained by measurement artifact,
consistent with LumiMotion's learned `pred_color` shadow-modulation head absorbing
the error at the training light and mis-generalising under a novel one.

A suspected brightness/epsilon artifact was tested and **ruled out** (scale-relative
ε moved every number by ≤0.01).

**Lesson:** render-space error sits downstream of albedo error, learned
compensation, envmap error, and MC noise. Too indirect to isolate a small term.

### Probe C — per-Gaussian transport residual
Computed, per Gaussian per frame, `L_true(t)` (diffuse outgoing radiance from the
deformed normal, current visibility, optimized envmap) vs. `L_stored`
(`_albedo_dc_stage1`).

**Initial result:** flat. Pooled correlation with normal rotation −0.008 / +0.016
over ~650–700K Gaussian×frame pairs. Reported as a clear negative.

**This was wrong**, for two compounding statistical reasons found on re-analysis:
1. **Between- vs. within-Gaussian variance.** `residual_i(t) = C_i + Δ_i(t)`, where
   `C_i` is a large per-Gaussian constant offset (from `L_stored` encoding full
   appearance incl. specular vs. `L_true` being pure diffuse — a definitional
   mismatch in our probe, not LumiMotion's error). `std(C_i)` is **13–15×** the
   within-Gaussian spread of `Δ_i(t)`. Pooling buries the signal.
2. **Signed vs. unsigned.** `rotation_deg ≥ 0` always; `Δ_i(t)` is signed (a normal
   can rotate toward brighter *or* darker light). Correlating signed against
   unsigned is ≈0 *by construction* for a symmetric effect. The physics comparison
   itself measures `|ΔE|/E`.

**Both corrections are required together.** Removing only `C_i` still gives ≈0
(Pearson r is invariant to subtracting a per-series constant). Removing only the
sign issue gives ≈0 too, since `|C_i + Δ_i| ≈ |C_i|` when `|C_i| ≫ |Δ_i|`.

**Corrected result:** `|Δ_i(t)|` vs. rotation = **+0.169** (jj) / **+0.135**
(standup) pooled; per-Gaussian within-trajectory median **+0.202** / **+0.488**,
with **61.3%** / **75.2%** of dynamic Gaussians positive.

A third artifact was also diagnosed: 18% (jj) / 56% (standup) of dynamic Gaussians
have `|L_true(canonical)| < 0.05`, so relative-change means were denominator-
dominated (within a low-rotation bin, relative change correlated +0.60 with
1/denominator). Median-per-bin or denominator-filtering recovers a monotonic curve
that tracks the independently-derived physics prediction closely for standup,
partially (~2–4× flatter mid-range) for jumpingjacks.

**Lesson:** three separate statistical artifacts each independently produced a
spurious null. Any one of them alone would have killed the direction.

### Irradiance-frequency test — standalone physics
Hypothesis under test: was the null caused by the benchmark's very low-frequency
32×16 envmaps?

**Result: no.** Relative irradiance change under normal rotation is **flat across
32×16 → 4K** (128× linear resolution) at every angle and every occlusion level.
Magnitudes are substantial at every resolution (8%/49%/93% unoccluded at the three
measured angles, 15–112% under occlusion). Occlusion amplifies small-angle
sensitivity ~5× but introduces no resolution dependence.

This **closed off** the lighting-resolution explanation and created the contradiction
that motivated the Probe C re-analysis.

### Indirect-fraction measurement
Exact linear split via `wo_indirect` (valid because `diffuse + specular` is exactly
linear in `incident_lights`, and the flag zeroes only the local term *after*
`pc.trace()`, so both passes share bit-identical visibility and deterministic sample
directions).

| scene / light | mean | median | p90 | p99 |
|---|---|---|---|---|
| jumpingjacks, chapel_day | 2.79% | 2.11% | 5.17% | 12.6% |
| jumpingjacks, golden_bay | 3.38% | 2.67% | 6.04% | 15.2% |
| standup, chapel_day | 9.56% | 7.00% | 21.1% | 35.2% |
| standup, golden_bay | 12.03% | 8.01% | 30.3% | 47.1% |

Spatially it lands exactly where physics predicts — a sharp halo at feet–floor
contact (jumpingjacks), the body–floor concavity (standup) — near zero everywhere
with an open view of the environment. It tracks **pose configuration** (what touches
what), not deformation magnitude (r = −0.03 to +0.03), which also rules it out as an
alternative explanation for any deformation-correlated signal.

---

## 4. Scene dependence is the headline

standup has **3–4× jumpingjacks' indirect fraction purely by lying down against the
floor.** One configuration change, one order of magnitude in the parameter that
governs everything.

And the three findings line up rather than conflict: standup is the scene with the
higher indirect fraction, the stronger per-Gaussian rotation signal (75% vs. 61%),
*and* the one positive deformation-scaling result in Probe D's relight run. In
standup's high-indirect tail the implied error reaches 8.6–14.4%, which **exceeds**
the reconstruction noise floor.

**Both benchmark scenes are a single figure on an open platform under distant
lighting — about as unfavourable to inter-reflection as a dynamic scene gets.**

---

## 5. What this establishes for future work

**Do not generalise the null.** The measured 2.8–12% is a property of these scenes.
Implied render error scales linearly with indirect fraction, so a configuration at
30–40% would put the error at 3–15% — above the noise floor.

**The decisive next measurement is indirect fraction in realistic configurations**,
and it needs no Gaussian training at all: Cycles renders the indirect diffuse pass
as a separate AOV, so it can be read as ground truth directly in Blender.

**Pre-committed threshold:** if no realistic configuration (interior, corner,
contact-rich pose, cloth, coloured bounce) exceeds ~25% indirect fraction, the
effect is marginal everywhere and the direction should be abandoned.

**Open risk if it does exceed:** inverse rendering is harder under strong
inter-reflection. Verify RadioGS itself behaves on a high-indirect static scene
before committing.

---

## 6. Incidental findings

**Bug in LumiMotion's released eval scripts.** `eval_nvs_dynamic.py:69,86-88` and
`eval_relight_dynamic.py:80,97-99` build the BVH once on frame 0 and never call
`update_bvh` — so visibility for every subsequent frame is traced against frame-0
geometry. Training does it correctly (`train_stage2.py:155-159`). Fails silently:
passing deformed geometry into `trace()` affects the returned normals and colour
math, but the ray–triangle intersection still uses the stale BVH.

This likely *understates* their published dynamic numbers. **Any future head-to-head
comparison must fix their eval first** — otherwise we would be beating a handicapped
baseline, which is not a real result. Reported to the author.

---

## 7. Methodological lessons worth carrying forward

1. **A probe can test the wrong thing convincingly.** Probe B's brightening was
   real, visible, and irrelevant.
2. **Pooled correlations across heterogeneous units mask within-unit effects.**
   Between-subject variance swamped within-subject signal by 13–15×.
3. **Correlating a signed quantity against an unsigned one is ≈0 by construction.**
   Check the sign structure of both variables before trusting a null.
4. **Small denominators destroy mean-based relative statistics.** Use medians or
   filter unstable denominators.
5. **Measure the fraction before chasing the error.** The single cheapest,
   most decisive measurement in this entire investigation was the last one.

---

## Artifacts

- `docs/test1_hook_points.md` — read-only code trace
- `docs/test1_probe_c.md` — original per-Gaussian probe (**superseded** — see re-analysis)
- `docs/test1_probe_c_reanalysis.md` — corrected analysis
- `docs/test1_probe_d.md`, `docs/test1_probe_d_relight.md` — render-space probes
- `docs/irradiance_frequency_test.md` — standalone physics
- `docs/indirect_fraction.md` — the decisive measurement
- `scripts_local/` — all instrumentation
