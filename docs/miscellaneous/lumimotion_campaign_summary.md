# LumiMotion Investigation — Campaign Summary

**Period:** August 2026 (~2 weeks)
**Repo:** fork of LumiMotion (CVPR 2026 Highlight, arXiv 2604.10994)
**Purpose:** determine whether "temporally coherent light transport for deforming
Gaussian surfels" is a viable PhD paper direction.

**Outcome: CONTINUE, conditionally.** The hypothesised error is real and measured.
It is negligible in the published benchmark, and the reason is fully explained and
quantified. High-indirect configurations where it would matter exist and are
reachable. The binding open risk has moved to whether the intended substrate
(RadioGS) functions in those configurations.

---

## 1. The hypothesis

LumiMotion rebuilds its BVH every training iteration against the currently sampled
frame's deformed geometry, so transport **geometry** is frame-aware. But the radiance
a traced ray picks up comes from `_albedo_dc_stage1` — a canonical, frame-independent
per-Gaussian SH bank. Transport **content** is frozen.

Physically: under fixed lighting with deforming geometry, a surfel's true outgoing
radiance changes — its normal rotates relative to the light, its self-shadowing
changes. A surfel that rotates into shadow should dim and bleed *less* light onto its
neighbours. Its stored radiance says otherwise.

**Question:** does that produce measurable, deformation-scaled error?

---

## 2. The answer, as a causal chain

| # | Link | Measured | Source |
|---|---|---|---|
| 1 | Relative error in stored radiance is **large** | 8% / 49% / 93% at median / p90 / p99 observed rotation (8.7° / 49.6° / 91.2°); 15–112% under occlusion | `irradiance_frequency_test.md` |
| 2 | The error is **genuinely present** per-Gaussian | 61% (jj) / 75% (standup) of dynamic Gaussians show residual magnitude tracking their own rotation | `test1_probe_c_reanalysis.md` |
| 3 | Indirect light is a **small fraction** of these images | mean 4.4% (jj) / 9.6% (standup); p99 23.7% / 50.8% | `indirect_fraction.md` |
| 4 | Therefore render error is **at or below the noise floor** | 0.19% / 0.90% typical vs. 2.4–13.2% reconstruction error | `indirect_fraction.md` |

**Nothing is left unexplained.** LumiMotion's renders are good *because these images
contain little indirect light*, not because the transport model is correct.

**The chain has exactly one free parameter: indirect fraction.** Implied render error
scales linearly with it. That single scene property decides whether the effect
matters anywhere.

---

## 3. Test 2 — does any realistic configuration clear the bar?

Measured directly in Blender via Cycles passes (no Gaussian training). Pre-committed
threshold: ~25% indirect fraction.

| # | configuration | mean | p90 | verdict |
|---|---|---|---|---|
| 1 | as shipped, `db=1` | 6.72% | 16.50% | — |
| 2 | `db=8` | 7.20% | 17.72% | — |
| 3 | corner | 18.20% | 38.28% | p90 clears |
| 4 | corner + red wall | 17.70% | 37.13% | p90 clears |
| 5 | cloth | 14.72% | 34.71% | p90 clears |
| 6 | interior | 33.27% | 53.45% | **both clear** |

**Gate passed.** Methodology validated against the Gaussian-side measurement
(1.02–1.16× after matching definitions; the initial 1.5× gap was diagnosed as glossy
indirect, which Cycles includes at 23.6% of its total and LumiMotion under-models,
plus mask erosion). Camera trajectory verified to reproduce `transforms_train.json`
exactly.

### Three findings beyond the table

**Enclosure is the driver, not the render setting.** `db=1→8` moves indirect only
+7%. Geometry moves it 2.7–5×. So the benchmark's low indirect fraction is a
consequence of its **open-platform scene design**, not its single-bounce GT. That is
a cleaner critique — it is about how dynamic relighting benchmarks are constructed.

**Coloured bounce redistributes rather than raises.** A red wall drives the R channel
to 1.58× G/B while the scalar mean slightly *falls*. **Every probe in this campaign
used channel-mean scalarization and would have reported no effect at all.** There is
a whole class of chromatic bounce error the measurement apparatus was blind to by
construction — and chromatic error is perceptually salient in a way scalar error is
not.

**The honest reading is narrower than "four of six clear."** The trustworthy column
is `mean × median` implied error, and exactly one cell clears there: **interior +
standup-like deformation, 3.13%** against a 2.4% floor. Everything else clears only
via tail×tail products, which multiply two independently estimated tails and assume
the highest-indirect pixels are fed by the most-rotated Gaussians — not established.
**The effect becomes real in enclosed scenes with substantial deformation, and
remains marginal elsewhere.**

---

## 4. What each probe actually established

### Probe B — visual `L_ind` dump ❌ *tested the wrong thing*
The indirect channel *does* brighten as arms approach the torso. This looked like a
refutation and was uninformative: the brightening comes from **visibility** change
(which surfel a ray hits), which LumiMotion handles correctly. It would look
identical whether stored radiance were frozen or perfectly updated.
**Lesson: the error is second-order — the magnitude of the bounce, not its presence.**

### Probe C — per-Gaussian transport residual ✅ *the load-bearing result*
Initially reported a clean null (pooled r = −0.008 / +0.016). **That was wrong**,
for three independent statistical reasons, each of which alone would have killed the
direction:

1. **Between- vs. within-Gaussian variance.** `residual_i(t) = C_i + Δ_i(t)`;
   `std(C_i)` is **13–15×** the within-Gaussian spread of `Δ_i(t)`. Pooling buries it.
   (`C_i` is our own probe's artifact: `L_stored` encodes full appearance including
   specular, `L_true` is pure diffuse.)
2. **Signed vs. unsigned.** Rotation is an angular distance (≥0); the residual is
   signed. Correlating them is ≈0 *by construction* for a symmetric effect. Pearson r
   is invariant to subtracting a per-series constant, so removing `C_i` alone changes
   nothing — **both corrections are required together**.
3. **Small denominators.** 18% (jj) / 56% (standup) of dynamic Gaussians have
   `|L_true(canonical)| < 0.05`, so relative-change means were denominator-dominated
   (r = +0.60 with 1/denominator within a low-rotation bin).

**Corrected:** `|Δ_i(t)|` vs. rotation = +0.169 / +0.135 pooled; per-Gaussian
within-trajectory median +0.202 / +0.488; 61.3% / 75.2% of dynamic Gaussians
positive. standup tracks the independently derived physics curve closely to ~100°.

### Probe D — render-space error ❌ *weak, then weaker*
Confound-dominated throughout. The RGB-mask correction (below) **weakened every
conclusion and strengthened none**. Three published claims are retracted:
- "99–100% of jj frames positive" → 63% at training light, near chance
- standup/golden deformation correlation +0.099 → **+0.011** (it was the floor)
- "the checkerboard prop is classified as dynamic" → it is **static** (no Armature
  modifier); it was included only because the mask was whole-foreground

**One thing survives and is cleaner after correction:** the L_ind correlation is
consistently stronger under the **held-out** light than the training light in both
scenes, with a proportionally larger gap than published. That is the compensation
hypothesis's prediction — LumiMotion's learned `pred_color` shadow-modulation head
absorbing transport error at the training light and mis-generalising under a novel
one. It remains subject to albedo error out-predicting L_ind by 1.9–12.7×.

### Irradiance-frequency test ✅ *closed off an escape route*
Tested whether the null was caused by the benchmark's 32×16 envmaps. **It was not**:
relative irradiance change under normal rotation is flat from 32×16 to 4K (128×
linear resolution) at every angle and occlusion level. Occlusion amplifies
small-angle sensitivity ~5× but introduces no resolution dependence. This created the
contradiction that forced the Probe C re-analysis.

### Indirect-fraction measurement ✅ *the decisive one, and it came last*
Exact linear split via `wo_indirect` (valid: `diffuse + specular` is exactly linear
in `incident_lights`, and the flag zeroes only the local term *after* `pc.trace()`,
so both passes share bit-identical visibility and deterministic sample directions).

---

## 5. Bugs and data issues found

### In LumiMotion's released code
**BVH built once, never updated, in the eval scripts.** `eval_nvs_dynamic.py:69,86-88`
and `eval_relight_dynamic.py:80,97-99` set `build_bvh=True` on frame 0 then `False`,
and never call `update_bvh`. Training does it correctly
(`train_stage2.py:155-159`). **Fails silently** — passing deformed geometry into
`trace()` affects returned normals and colour math, but ray–triangle intersection
still uses the stale frame-0 BVH. Likely *understates* their published dynamic
numbers. **Any head-to-head comparison must fix this first**, or we would be beating
a handicapped baseline.

### In our own analysis (found and fixed)
**`dynamic_mask` channel.** `load_dynamic_mask()` thresholded ALPHA. Alpha is the
whole-scene silhouette (IoU 0.999 with the beauty render's own alpha); **RGB** is the
dynamic/static segmentation. IoU between them 0.18–0.22; alpha selected 4.4–5.3× more
pixels. The "dynamic" restriction was a no-op. Corrected; indirect-fraction and Probe
D re-run. **Probe C unaffected** — it uses `get_binary_feature()`, LumiMotion's own
learned per-Gaussian split, and never reads these PNGs.

### Benchmark properties that suppress indirect light
Three independent mechanisms, all pushing the same way:
- **Open-platform geometry** (dominant — enclosure multiplies indirect 2.7–5×)
- **`diffuse_bounces = 1`** (minor — worth only +7%)
- **`sample_clamp_indirect = 10.0`** — an authored clamp bounding indirect energy,
  present identically in every scene

### Blender version
Files are authored at version **4.4.32**; both 3.6.13 and 4.4.0 emit
"expect loss of data". Verified empirically that **no scene content is lost** —
206/264 resolved keys identical, geometry byte-identical, all Cycles and
colour-management settings preserved; the 58 diffs are Blender 4.0 renames with
values intact. Measured render difference ≤5.8% relative, attributable to the
Principled BSDF v2 rewrite shifting energy from diffuse-indirect to glossy-direct.
**No Test 2 threshold verdict flips.** Prefer 4.4.0 going forward — the author's GT
PNGs were rendered under 4.4.x.

Colour management confirmed as the author described: `view_transform = Standard` (not
Filmic), exposure 0, gamma 1, envmap in `Linear`.

---

## 6. Methodological lessons

1. **A probe can test the wrong thing convincingly.** Probe B's brightening was real,
   visible, and irrelevant.
2. **Pooled correlations across heterogeneous units mask within-unit effects.**
   Between-unit variance swamped within-unit signal by 13–15×.
3. **Correlating a signed quantity against an unsigned one is ≈0 by construction.**
   Check the sign structure of both variables before trusting a null.
4. **Small denominators destroy mean-based relative statistics.** Use medians or
   filter unstable denominators.
5. **Channel-mean scalarization hides chromatic effects entirely.** The red-wall
   configuration would have read as "no effect."
6. **Measure the denominator before chasing the numerator.** The cheapest measurement
   in the campaign — indirect fraction — was the decisive one, and it came last.
7. **Verify a restriction actually restricts.** The dynamic mask was a no-op for four
   probes before anyone checked.

---

## 7. Where this leaves the research direction

**Established:** the mechanism is real and measured. The benchmark's null is fully
explained. Configurations where the effect matters exist, are reachable, and have
been rendered.

**Not established, and now the binding risk:** whether RadioGS — the intended
substrate — actually functions under strong inter-reflection. Inverse rendering gets
*harder* at high indirect fraction: more observed radiance is ambiguous between
"bright material" and "light bounced from a neighbour." **If RadioGS degrades badly
at 33% indirect fraction, this is a problem statement with no solution.**

The interior scene in `scripts_local/test2/` is directly reusable as that test.

**Next:** render the interior as a static multi-view capture, train RadioGS on it,
compare decomposition quality against the TensoIR baselines.

**Also open:** chromatic bounce error (§3) is unexplored and the apparatus was blind
to it by construction.

---

## 8. Document index

| document | content |
|---|---|
| `lumimotion_eval.md` | code audit — the frozen-content finding |
| `lumimotion_repro.md` | validated baseline reproduction |
| `test1_hook_points.md` | read-only code trace for instrumentation |
| `test1_probe_c.md` | ⚠️ **superseded** — see re-analysis |
| `test1_probe_c_reanalysis.md` | corrected per-Gaussian result |
| `test1_probe_d.md`, `test1_probe_d_relight.md` | ⚠️ **superseded** — see corrected |
| `test1_probe_d_corrected.md` | RGB-mask re-run; three claims retracted |
| `irradiance_frequency_test.md` | standalone physics; resolution independence |
| `indirect_fraction.md` | the decisive measurement (+ RGB-mask correction) |
| `test1_conclusion.md` | Test 1 causal chain |
| `test2_indirect_fraction_ladder.md` | the six-configuration ladder |
| `test2_blender_version_check.md` | 3.6.13 vs 4.4.0 fidelity |
| `blend_files_survey.md` | Blender scene survey |
| **this document** | campaign summary |
