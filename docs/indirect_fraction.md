# Indirect-illumination fraction of rendered radiance

**Question.** Physics says correct diffuse irradiance should change 8–93% under the
normal rotations present in these scenes (`docs/irradiance_frequency_test.md`), and
`docs/test1_probe_c_reanalysis.md` confirms a real rotation-dependent error in the
frozen stored radiance. Yet LumiMotion's renders and relighting are good
(`docs/test1_probe_d*.md`). One untested explanation: **indirect illumination may
simply be a small fraction of total rendered radiance**, so even a large *relative*
error in it is negligible in the render. This measures that fraction.

**Answer, up front.** Indirect illumination is a **small** component of these
images — mean **2.8%** (jumpingjacks) and **9.6%** (standup) of total linear
radiance under the training light, median 2.1% / 7.0%. It is highly concentrated:
essentially all of it sits at body–floor contact points and concavities, with the
bulk of each image below 3%. Combining this with the measured rotation-dependent
error gives an implied render error of **0.12–0.45%** for jumpingjacks and
**0.9–4.9%** for standup — against a measured overall render-vs-GT error (Probe D)
of 2.4–5.4% and 5.5–13.2% respectively.

**So: for jumpingjacks the answer is a clean "no, it cannot matter" — the implied
error is 6–36× below the reconstruction noise floor, and even the worst-case tail
combination stays below it. For standup the answer is "mostly no, but not
dismissibly so" — typical implied error is 1.4–6× below the noise floor, but in the
high-indirect tail (p90–p99 indirect fraction at p99 rotation) it reaches 8.7–14.4%
against a 5.5% floor, i.e. it exceeds it.** This is a genuine scene-dependent
split, not a uniform null, and it is discussed rather than averaged away below.

---

## Why this required re-rendering

`scripts_local/render_trajectory.py`'s dumps are all still on disk (150 frames ×
2 scenes × 2 lighting conditions, all present and checked first). **They do not
contain the needed quantity.** They store `lind_linear` =
`local_incident_lights.mean(dim=1)` — the raw mean *incident* indirect radiance.
The contribution to final radiance is

```
mean_s[ f · L_local(s) · incident_areas(s) · cos(s) ]        (render_ir.py:538-540)
```

weighted by BRDF, solid angle, and cosine — none of which were saved. The
contribution is therefore not recoverable from the dumps, and a second render pass
was required. Stating this plainly as instructed.

## Method — exact linear split, not an approximation

`render_ir.py:538-540` computes `transport = incident_lights * incident_areas *
n_d_i`, then `diffuse = (f_d * transport).mean(-2)` and `specular = (f_s *
transport).mean(-2)`. `f_d`, `f_s`, `incident_areas` and `n_d_i` are all
independent of `incident_lights`, so **`diffuse + specular` is exactly linear** in
`incident_lights = incident_visibility·global + local`.

The existing `pipe.wo_indirect` ablation (`render_ir.py:527-528`) zeroes *only* the
local term, and does so **after** `pc.trace()` — so visibility, traced geometry and
sample directions are bit-identical between passes (`training=False` ⇒
`sample_incident_rays` uses `random_rotate=False`, i.e. deterministic directions).
Therefore

```
indirect_contribution = full_render_linear − wo_indirect_render_linear
```

holds **exactly**, not approximately. The same argument holds for the relight path
via `pipe.wo_indirect_relight` (`render_ir.py:504-507`).

The subtraction is done on **linear** diffuse/specular images. The pre-existing
`"diffuse"`/`"specular"` result keys are sRGB-encoded *and clipped to [0,1]* by
`rgb_to_srgb()`, so they cannot recover linear radiance for bright pixels; a small
additive `dump_linear_components` hook was added to `render_ir.py` (default off,
outputs bit-for-bit unchanged when unset), matching the established
`dump_light_indirect` pattern on this branch.

**Validated before the full run**: on a test frame, indirect ≥ 0 everywhere and
indirect ≤ total everywhere — both physically necessary and both hold exactly.

Masking: eroded (5px) alpha ∩ `dynamic_mask/`, matching
`docs/test1_probe_d_relight.md`. Per-pixel radiance is channel-mean linear.
Fraction = indirect / total. 150 frames × 2 scenes × 2 lighting conditions.

---

## Results — the distribution

Pooled over dynamic-region pixels, all 150 frames (n = 450,000 sampled pixels per
condition):

| scene / light | mean | median | p90 | p99 | max |
|---|---|---|---|---|---|
| jumpingjacks, chapel_day (train light) | **2.79%** | 2.11% | 5.17% | 12.6% | 74.6% |
| jumpingjacks, golden_bay (relit) | **3.38%** | 2.67% | 6.04% | 15.2% | 76.9% |
| standup, chapel_day (train light) | **9.56%** | 7.00% | 21.1% | 35.2% | 81.3% |
| standup, golden_bay (relit) | **12.03%** | 8.01% | 30.3% | 47.1% | 94.1% |

Foreground-only (without the dynamic-mask restriction) is within 0.1 percentage
point of the dynamic-restricted numbers in every condition — the restriction
barely matters here. Train and test splits agree to within 0.5 pp throughout.

![distribution, standup chapel_day](indirect_fraction_assets/standup_chapel_day/distribution.png)

The distribution is strongly right-skewed in all four conditions: a large majority
of pixels sit at a few percent, with a thin tail reaching 70–94% in the deepest
contact shadows.

## Where it is highest

![map, jumpingjacks frame 75](indirect_fraction_assets/jumpingjacks_chapel_day/map_frame0075.png)
![map, standup frame 125](indirect_fraction_assets/standup_chapel_day/map_frame0125.png)

Exactly where physics predicts, which is a useful independent sanity check on the
split: the indirect fraction spikes at the **feet–floor contact** (jumpingjacks —
the bright halo around the shoes, ~16%, against ~2% over the rest of the body and
floor) and at **body–floor contact and the concavity under the torso and behind
the prop** (standup, ~30%+). Everywhere with an open view of the environment, it
is near zero. standup's much higher scene-level average is explained by its pose:
the figure lies on the platform for much of the sequence, putting a large part of
both body and floor in mutual contact.

## Variation across frames and with deformation

![per-frame, standup golden_bay](indirect_fraction_assets/standup_golden_bay/per_frame.png)

| condition | per-frame mean range | corr(mean frac, mean \|d_xyz\|) |
|---|---|---|
| jumpingjacks, chapel_day | 2.14% – 3.52% | −0.031 |
| jumpingjacks, golden_bay | 2.71% – 4.61% | −0.281 |
| standup, chapel_day | 5.38% – 12.62% | +0.017 |
| standup, golden_bay | 4.54% – 15.56% | +0.027 |

The indirect fraction varies meaningfully across the sequence (standup's more than
doubles as the figure lies down and stands up) but shows **essentially no
correlation with deformation magnitude** — it tracks *pose configuration* (what is
touching what), not *how far things moved from canonical*. That is the physically
expected behaviour and is worth noting because it means indirect fraction is not
an alternative explanation for any deformation-correlated signal.

---

## The key derived number: implied error contribution to the render

Relative error in the stored radiance is taken from
`docs/test1_probe_c_reanalysis.md` Check 1 (robust median-per-bin,
denominator-stable, dynamic Gaussians), interpolated to the three measured
rotation angles. Implied render error = (relative error in indirect radiance) ×
(indirect fraction of total radiance).

### jumpingjacks

| rotation | rel. error in stored radiance | implied render error @ mean frac | @ p90 frac | @ p99 frac |
|---|---|---|---|---|
| median (8.7°) | 4.3% | **0.12%** | 0.22% | 0.55% |
| p90 (49.6°) | 8.8% | **0.25%** | 0.46% | 1.11% |
| p99 (91.2°) | 13.4% | **0.37%** | 0.69% | 1.69% |

*Probe D measured overall render-vs-GT relative error (the noise floor this would
have to exceed to be detectable): **2.36%** (chapel_day), **5.43%** (golden_bay).*

### standup

| rotation | rel. error in stored radiance | implied render error @ mean frac | @ p90 frac | @ p99 frac |
|---|---|---|---|---|
| median (8.7°) | 9.4% | **0.89%** | 1.97% | 3.30% |
| p90 (49.6°) | 24.3% | **2.32%** | 5.12% | 8.55% |
| p99 (91.2°) | 41.0% | **3.92%** | 8.65% | 14.44% |

*Probe D measured overall render-vs-GT relative error: **5.46%** (chapel_day),
**13.24%** (golden_bay).*

### For intuition, in 8-bit terms

A relative change of 0.1% near a mid-tone linear value of 0.2 is **0.06/255**
sRGB levels; 0.5% is 0.29/255; 1% is 0.57/255. **The typical implied error for
jumpingjacks (0.12–0.45%) is well under half of one 8-bit quantization step** —
literally not representable in the rendered image. standup's typical implied error
(0.9–4.9%) reaches ~0.5–2.9/255 levels, which is representable but still small.

---

## Is this consistent with Probe D's null result?

**jumpingjacks: yes, decisively.** The implied error is 6–36× below the measured
reconstruction error, and even the worst-case combination in the table (p99
indirect fraction at p99 rotation, 1.69%) stays below the 2.36% floor. There is no
combination of the measured quantities that would make the frozen-transport error
detectable in this scene's renders. Probe D's null for jumpingjacks is fully
explained: **the indirect term is too small a component for an error in it to
matter.**

**standup: mostly, but with a real caveat.** Typical implied error (0.89–3.92%)
sits 1.4–6× below the 5.46% floor — consistent with a null. But in the
high-indirect tail, the implied error reaches **8.55–14.44%**, which *exceeds* the
overall reconstruction error. So for standup the honest statement is not "too
small to matter" but "**too small to matter across most of the image, and
plausibly detectable in the ~1–10% of pixels at contact points, where it would be
competing with — and likely buried by — the same magnitude of ordinary
reconstruction error**." This is notably the same scene where
`docs/test1_probe_c_reanalysis.md` found the stronger rotation-dependence (75% of
dynamic Gaussians positive vs. 61% for jumpingjacks) and where
`docs/test1_probe_d_relight.md` found its one positive deformation-scaling result.
Those three findings are mutually consistent: standup is the scene with enough
indirect light for the effect to be marginally visible, and it is the scene where
marginal traces of it appear.

**Overall reconciliation of the whole investigation.** All four results now fit
together without contradiction:
- Physics says the *relative* error in stored indirect radiance is large (8–93%) —
  `irradiance_frequency_test`. **True.**
- That error is really present in LumiMotion's per-Gaussian radiance —
  `probe_c_reanalysis`. **True.**
- The renders are nonetheless good — `probe_d`. **True, because** the indirect
  term is only 2.8–12% of total radiance, so a 4–41% relative error inside it
  becomes a 0.1–4% error in the render, at or below the level of ordinary
  reconstruction error.

The frozen-transport error is **real but small in its effect on these images**,
because the images have little indirect light in them. This is a statement about
*these benchmark scenes*, not about the method in general — see the first
limitation.

---

## Limitations

1. **This is a property of these scenes, not a general bound.** Both are a single
   figure on an open platform under distant lighting — geometrically about as
   favourable to direct illumination as a dynamic scene gets. A scene with strong
   interreflection (an interior, a figure in a corner or between walls, brightly
   coloured nearby surfaces producing colour bleeding) would have a far higher
   indirect fraction, and the same relative error would then matter proportionally
   more. **The 2.8–12% measured here should not be assumed to transfer.** That
   standup alone — merely by having the figure lie down against the floor — has
   3–4× jumpingjacks' indirect fraction shows how strongly this depends on
   configuration.
2. **The implied-error calculation is an upper bound**, in two ways that both make
   the true effect *smaller* than the numbers above:
   (i) it assumes the stored-radiance errors of all Gaussians a ray bundle hits
   are perfectly coherent, whereas averaging over 512 sample directions hitting
   many differently-oriented Gaussians will partially cancel them;
   (ii) it applies the *dynamic*-Gaussian rotation error to all traced hits,
   whereas rays that hit static Gaussians (76–78% of the population) pick up no
   rotation error at all.
   Being an upper bound strengthens the "negligible" conclusion for jumpingjacks
   and keeps standup's borderline case honest.
3. **The noise-floor comparison uses Probe D's overall render-vs-GT relative
   error as a proxy for detectability.** That quantity bundles every error source
   (geometry, albedo, roughness, envmap, deformation) and is not a formal
   detection threshold; it is used here as an order-of-magnitude reference for
   "what size of error is already present and would mask this one."
4. **Channel-mean scalarization** of both radiance quantities, consistent with
   prior probes but discarding colour — a colour-selective indirect error (likely,
   since indirect light carries the bouncing surface's colour) could be more
   visible than the scalar number suggests.
5. `spheres_v5_spec32` still has no trained checkpoint — same gap as every prior
   probe in this investigation.
