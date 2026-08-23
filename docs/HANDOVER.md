# HANDOVER — Gaussian Splatting Inverse Rendering / Dynamic Light Transport

**Author:** Francesco Mazzone-Bianco, first-year PhD, CUHK MMLab
**Period covered:** June–August 2026 (~2 months)
**Status:** Measurement campaign complete. Direction unresolved. Supervisor meeting pending.
**Repo:** `airframa/RadioGS-public`, branch `audit-notes` (fork of `qbhan/RadioGS-public`)

---

## 0. How to use this document

This condenses a two-month campaign spanning 23 numbered document sections
across a dozen files. It exists because the original conversation grew too long
to hold in context, and because several early framings in it are now **dead by
measurement** and would actively mislead.

**Read §1–§3 for orientation. §4 for what actually happened. §5–§7 are the
results. §8–§11 are operational.**

The single most important thing to understand: **four candidate mechanisms were
proposed and four were excluded by measurement.** What survives is a set of
solid diagnostic findings and no working method framing. That is the honest
state.

**But read §6's strength column before treating any exclusion as final.** They
are not equally strong: two are positive and closed, one rests on a single rung
of a single subject, one holds only outside enclosed scenes, and one is contested
and should be reopened.

Source documents live in `docs/` in the repo. This supersedes their framing but
not their detail; where they conflict, this document is later.

---

## 1. The original question, and how it moved

**Started as:** dynamic scenes deform; light bouncing between surfaces should
change as they do; existing methods freeze it. Make light transport temporally
coherent on deforming Gaussian surfels.

**Became, after Test 1:** that error is real but small (0.19–0.90% render error
at the indirect fractions current benchmarks use). Not a viable target alone.

**Became, after Phase 3b:** the substrate under-recovers indirect light
substantially — up to 39% missing — and that error scales with a measurable
scene property. This looked like a better target.

**Became, after §21–§22:** the mechanism is neither missing bounces nor poor
observation. **No mechanism currently explains the central observation.**

**Where it stands:** a robust diagnostic result with no method attached, and a
decision to make about what to write.

---

## 2. The ecosystem

### 2.1 Static Gaussian inverse rendering — mature and crowded

| Work | Venue | Contribution |
|---|---|---|
| GS-IR | CVPR'24 | First 3DGS inverse rendering; indirect baked to light-probe grid |
| R3DG / Relightable3DGS | ECCV'24 | Point-based ray tracing with BVH; per-Gaussian BRDF |
| Ref-Gaussian | ICLR'25 | Deferred rendering + inter-reflections |
| SVG-IR | CVPR'25 | Spatially-varying BRDF per Gaussian |
| GeoSplatting | ICCV'25 | Mesh/SDF-guided normals |
| **IRGS** | CVPR'25 | **2D Gaussian ray tracing (OptiX BVH). Provides `surfel_tracer`.** |
| GI-GS | ICLR'25 | Indirect via path tracing on deferred G-buffers |
| RTR-GS | ACM MM'25 | Hybrid forward/deferred for reflective objects |
| **RadioGS** | **ICLR'26 Oral** | **Our substrate.** Radiometric consistency loss for unobserved directions |
| **RadiosityGS** | **TOG'25** | Adapted radiosity on Gaussian surfels. Rigorous multi-bounce, static, 5–10 h/scene |
| GOGS | 2026 | Glossy objects, split-sum + MC importance sampling |
| GAINS | 2026 | Sparse-view |
| **PTIR-GS** | **June 2026** | **Splatting-free path-traced IR, explicit multi-bounce** |
| GS-SVIR | 2026 | Multi-bounce via per-Gaussian SH |
| GIR | 2024 | Voxel-based indirect tracing, "approximating multi-bounce" |
| MIRReS | ICLR'25 | Multi-bounce path tracing + reservoir sampling (mesh, not GS) |

**Implication:** "static multi-bounce Gaussian IR" is closed as a contribution.

### 2.2 Dynamic / 4D

| Work | Venue | Relation |
|---|---|---|
| 4DGS (Wu et al.) | CVPR'24 | Deformation field + HexPlane. Standard backbone. |
| **E-D3DGS** (Bae et al.) | ECCV'24 | **Per-Gaussian embedding deformation.** Argues coordinate-based fields fail because GS is a mixture of per-Gaussian fields. Code released. |
| ST-2DGS | 2024 | Deformable 2D surfels. **NO CODE.** Useful design reference (opacity composition scheme, regularizer weights). |
| SGIA | 2024 | 2DGS + LBS + PBR, clothed humans. Approximates occlusion. |
| BEAM | SIGGRAPH'25 | Relightable volumetric video. Per-frame PBR. |
| Disentangled GS | SIGGRAPH Asia'25 | Geometry/appearance disentanglement, dynamic |
| DR-GS | ICLR'26 **reject** | Deformable + relightable 2D Gaussians. **Rejected as "combines existing techniques, no novel technical challenge."** This rejection is why this project exists. |
| **LumiMotion** | **CVPR'26 Highlight** | **Nearest neighbour.** Dynamic 2DGS IR. Motion as supervision for decomposition. Code + dataset released. |
| RTGI for Dynamic 3DGS | TOG'25 | **NOT a competitor.** Forward rendering, non-differentiable, "dynamic" = interactive editing. |

### 2.3 ⚠️ Temporal GI amortisation — a 35-year-old thread in FORWARD rendering

**This was discovered late and materially changed the novelty picture.** The
"transport the solution, correct periodically" idea is classical:

- Chen 1990, *Incremental radiosity* (SIGGRAPH)
- George/Sillion/Greenberg 1990, *Radiosity redistribution for dynamic environments*
- Tost & Pueyo 1993; Nimeroff/Dorsey/Rushmeier 1995; Besuievsky & Sbert 1996
- Damez et al., *Dynamic Radiosity using Higher Order Function Bases and Temporal Coherence*
- Tawara/Myszkowski/Seidel 2004, *Exploiting temporal coherence in final gathering for dynamic scenes*
- Laine et al. 2007, *Incremental Instant Radiosity*
- Majercik et al. 2019, DDGI
- Müller et al. 2021, *Real-time neural radiance caching* — explicitly for fully dynamic scenes
- RTGI for Dynamic 3DGS 2025 — two-level radiance cache, temporally reused

**A graphics reviewer will know this immediately.** Temporal amortisation of GI
cannot be presented as novel.

### 2.4 Radiance caching for *inverse* rendering — active right now

- Hadadan et al., *Neural Radiosity* (2021); *Inverse GI using a Neural Radiometric Prior* (SIGGRAPH'23)
- **Zhang, Vicini, Winberg, Garbin, Jakob — *Radiance Caching for Differentiable Path Tracing*, TOG, July 2026.** Jakob's group. Spatial blending field interpolating between cache and unbiased estimators.
- *Neural Inverse Rendering from Propagating Light* (2025) — time-resolved neural radiance caching (transient, different sense of "time")
- GLOW (Nov 2025) — dynamic radiance cache for moving near-field lights

### 2.5 The gap that survives

Nothing found combining: **multi-bounce inverse rendering + geometry deforming
over time + reconstructed from real multi-view video.** Every near neighbour
misses one axis. The gap is the intersection, not any single axis — which is
precisely the shape that invites the DR-GS rejection ("combines existing
techniques").

---

## 3. Substrate: what RadioGS actually is

**Verified by direct source diff, not inference:**

- **Inherited from IRGS:** `submodules/surfel_tracer` (OptiX differentiable 2D
  Gaussian ray tracer, verbatim), `build_bvh`/`update_bvh`/`trace`, the
  Ref-Gaussian init stage, most of `utils/`. **Credit IRGS for 2D Gaussian ray
  tracing in any related-work section.**
- **RadioGS-original:** the radiometric consistency loss (headline); the
  persistent per-Gaussian incident-light cache (IRGS re-traces fresh every
  iteration); direct/indirect decomposition of render outputs; a back-culling
  CUDA tweak.

**Architecture, established the hard way (§9 of `phase3a_enclosure_results.md`):**
RadioGS is **object-centric by construction** and depends on three assumptions
simultaneously:
1. a silhouette exists (mask-entropy loss carves geometry; with alpha ≡ 1 it
   inverts to a space-filling force)
2. the environment map is directly observed (with `Env ≡ 0` it is unconstrained
   and absorbs scene radiance — measured 9.79× too bright)
3. alpha isolates the subject (the whole stock eval chain masks on it)

An interior enclosure violates all three. **Do not attempt scene-level or
enclosed captures with unmodified RadioGS.**

**Key code locations:**
- `gaussian_renderer/radiogs.py:578-638` — `rendering_equation_radiosity`
- `radiogs.py:553-554` `render_indirect` (outgoing) vs `:568` `light_indirect` (incident) — **these differ by 2.4–4.8×; `eval_indirect.py:114` compares against the incident one**
- `radiogs.py:136-137,436` — the SH field stores **linear** radiance; `render_sh` PNG is sRGB-wrapped
- `scene/radiogs_gaussian_model.py:845` — `precompute_incidents`, refreshed every 100 iters
- `utils/loss_utils.py:372-531` — `calculate_loss3`

---

## 4. The journey

### 4.1 Direction selection

Four candidates were considered from the outset:

1. **Joint factorization under time-varying capture illumination** — high ceiling, identifiability risk. Deferred.
2. **Temporally coherent indirect illumination on deforming geometry** — chosen.
3. **Motion-from-lighting disentanglement** — subsequently occupied by LumiMotion.
4. **Material change as a first-class temporal quantity** (anisotropy, cloth) — deferred. **Still open. RadioGS's own limitations section names anisotropic materials as their future work, not dynamics.**

### 4.2 Test 1 — the LumiMotion campaign (~2 weeks)

**Question:** LumiMotion rebuilds its BVH per frame (transport *geometry* is
frame-aware) but traced radiance comes from `_albedo_dc_stage1`, a canonical
frame-independent SH bank (transport *content* is frozen). Does that matter?

**Answer: real but negligible, and fully explained.** Four measured links:

| # | Link | Value |
|---|---|---|
| 1 | Relative error in stored radiance is large | 8% / 49% / 93% at median / p90 / p99 observed normal rotation (8.7° / 49.6° / 91.2°); **15–112% under occlusion** |
| 2 | Genuinely present per-Gaussian | 61% (jumpingjacks) / 75% (standup) of dynamic Gaussians |
| 3 | **But indirect light is a small share of those images** | mean 4.37% / 9.60%; **p99 23.7% / 50.8%** |
| 4 | So render error is below the noise floor | 0.19–0.90% vs 2.4–13.2% |

⚠️ Link 3's **p99 is the tail that makes the "small fraction" framing
conditional** — see §6's note on where this exclusion does *not* hold.
(`lumimotion_campaign_summary.md:36-39`.)

**Probes, and what each taught:**
- **Probe B** (visual `L_ind` dump) — the indirect channel *does* brighten as surfaces approach. **Tested the wrong thing:** that is visibility change, which LumiMotion handles correctly.
- **Probe C** (per-Gaussian residual) — initially a clean null. **Wrong, three times over:** between/within-Gaussian variance (13–15×), signed-vs-unsigned correlation (≈0 by construction), small denominators (18–56% of Gaussians below threshold). Corrected: 61–75% positive.
- **Probe D** (render-space) — weak, then weaker after a mask-channel correction. Three published claims retracted.
- **Irradiance-frequency test** — ruled out "the benchmark's 32×16 envmaps are too low-frequency." Relative irradiance change is **flat from 32×16 to 4K** at every angle and occlusion level.
- **Indirect-fraction measurement** — the decisive one, and it came last.

### 4.3 Test 2 — does any realistic configuration matter?

Blender ladder, measured directly via Cycles passes. Pre-committed threshold 25%.

| configuration | mean | p90 |
|---|---|---|
| as shipped (`db=1`) | 6.72% | 16.50% |
| `db=8` | 7.20% | 17.72% |
| corner | 18.20% | 38.28% |
| corner + red wall | 17.70% | 37.13% |
| cloth | 14.72% | 34.71% |
| **enclosed interior** | **33.27%** | **53.45%** |

**Gate passed.** Key finding: **enclosure is the driver (2.7–5×), not the render
setting** (`db` 1→8 is worth only +7%). The benchmark's low indirect fraction is
a consequence of **open-platform scene design**.

Also found: a red wall drives R to 1.58× G/B while the **scalar mean falls** —
channel-mean analysis would report no effect.

### 4.4 The RadioGS gate (Phases 0–3)

- **Phase 0** — TensoIR anchor. Corrected for glossy indirect: the anchor was **wrong by 0.94×–5.24×, and not by a constant — in both directions** (ficus understated 5.24×, lego *over*stated at 0.94×). `phase2_albedo_sweep.md:20,70-74`.
- **Phase 1** — Blender→RadioGS pipeline validated at **~49 dB** against shipped renders. **Blender 2.93.9 is decisive** (3.6.13 gives 40.4 dB; Cycles X shifts brightness ~5%). *Note the source is internally inconsistent: `phase1_blend_pipeline.md:19,237` say 49.1 dB, its version-comparison table at `:247` says 48.90 dB. Quote 48.90 when citing the table.*
- **Phase 2** — albedo sweep, 18 rungs across 3 subjects, F = 1.55–11.63%. **Rendered, validated, and still UNTRAINED.**
- **Phase 2b** — enclosure arm, F = 1.90–56.76%.
- **Phase 3a** — enclosure arm **FAILED OUTRIGHT.** Not degradation — the run produced no recognisable subject, `light_direct` pure white. Diagnosed to the three architectural assumptions in §3. **Retracted; do not retry.**
- **Phase 3b** — object-centric groove ladder. This is where the good results are.

### 4.5 The mechanism hunt (§13–§23)

| § | Claim | Fate |
|---|---|---|
| 13.5 | Attribution declines with indirect fraction F | **Stands** |
| 13 | Bounce leaks into albedo | **Retracted** — persists 3.7× stronger in a no-bounce twin; it was occlusion |
| 15.1 | RadioGS captures ~the first bounce | **Retired** — a groove-specific coincidence of slope ≈1, intercept ≈0 |
| 17 | Attribution tracks authored bounce budget (r = −0.951) | **Dissolved** — tracked a flag, not physics; 3 of 4 TensoIR scenes have no multi-bounce energy |
| 20 | Attribution tracks first-bounce share | **Stands**, but slope is **shape-dependent** (groove +1.062, crosshatch +2.052; `t = +3.66, p = 0.0215` — *not* "non-overlapping CIs", see §5.1) |
| 21 | Architecture (single-bounce limit) explains it | **EXCLUDED** — `xh_a0.85` recovers only 84% of the *first bounce alone* |
| 22 | Observability explains the shape dependence | **EXCLUDED** — mechanism verified, but the crosshatch is **1.52× BETTER** observed |
| 23 | Is §21's number an artifact of wrong render flags? | **No** — bit-identical re-render; and 0.899 even under wrong flags |

---

## 5. What is established

### 5.1 First-bounce share is the right coordinate

Attribution (predicted / true outgoing indirect) tracks first-bounce share
linearly on **both** subjects, r ≥ 0.98. This is the campaign's cleanest
structural result and it generalises across shape.

| subject | slope | 95% CI (t, df=2) | intercept | r |
|---|---|---|---|---|
| groove | +1.062 | [+0.432, +1.693] | +0.101 | +0.982 |
| crosshatch | +2.052 | [+1.075, +3.030] | −0.626 | +0.988 |

**The slope does not generalise.** 1.93× difference, established by a
**difference-of-slopes test: `t = +3.66, df = 4, p = 0.0215`.** Robust to
clipping (9.88% clipped pixels move the slope by 0.001) and to specular
composition (diffuse-only slope **+1.850**).

⚠️ **Do not say "the CIs do not overlap."** They do, on [+1.075, +1.693]. §20.1
of `phase3b_object_centric_highf.md` originally reported normal 1.96σ intervals;
with n = 4 the regression has df = 2 and the correct multiplier is 4.303, so the
normal form understated the width by 2.2×. **The source doc has been corrected**
(§20.1 now carries the correction note). The conclusion survives on the test
above. Slope/r are quoted from `scipy.linregress`, the same fit that produces the
CI; §20 also prints `np.polyfit` values (+1.065 / +0.9815) which differ in the
third decimal.

### 5.2 Coverage → SH error: a subject-independent law

**§22, the strongest positively-verified result in the campaign.**

- Spearman ρ(coverage, SH error) is **negative in all 24 rung×channel cells**
  (−0.085 to −0.355); decile relationship r = −0.88 to −0.97 in every rung
- **Survives a luminance control** — attenuates 35–40%, stays negative in 39 of
  40 bands
- **Passes the healthy-case check** — the groove shows it *more* steeply
- **The sign is mechanistically apt:** poorly-observed Gaussians are **13–35% too
  dark**; well-observed ones sit within 2–7% of GT
- **Subject-independent:** at matched coverage the two subjects agree within ~8%
- High-error Gaussians are spatially concentrated in concavity interiors, all
  eight rungs

**Measured without a render:** the SH evaluation is closed-form
(`eval_sh(deg, sh, d) + 0.5` reproduces the tracer exactly), and for any camera
where a Gaussian is the visible front surface, true radiance *is* the image
pixel. Scored on held-out test views ⇒ generalisation error.

**Caveat:** test cameras sit on the training radius, so this samples the
best-constrained directions, while `rendering_equation_radiosity` gathers along
arbitrary hemisphere directions. **This is a lower bound.**

Lifting it is a **render job only — the analysis path is complete.**
`run_probe_views.sh` renders 240 views/rung at radius 1.4/2.0 (training was
4.031), aimed radially so each looks *down* a channel. **Not yet run.**
`observability.py --probe_src` scores against them; it rebuilds the probe
cameras itself (the probe render writes `train_NNN/` directories, not the layout
`readCamerasFromTransforms` expects) and **gates on reproducing Scene's own test
cameras before scoring — currently exact, max difference 0.00e+00 on both camera
centre and `full_proj_transform` across all 200 test views.** Verified
end-to-end by scoring a model against the training-split renders, which share the
probe layout.

### 5.3 Standard benchmarks cannot detect this

**3 of 4 TensoIR scenes have first-bounce share ≈ 1.0** (1.000 / 0.996 / 0.987),
including one authored at 128 diffuse bounces. Their attributions span 0.452–2.462
at essentially constant x. **You cannot fit a slope through a vertical line.**

Why ficus reads 0.987 despite 128 authored bounces: its indirect is only 20%
diffuse and **44% transmission**, and `--diffuse_bounces` does not touch
transmission. Its light path runs through the leaves under `transmission_bounces`.

**This is a benchmark critique backed by measurement, and it is independent of
every dead framing above.**

### 5.4 A separate chromatic defect

RadioGS over-attributes indirect in **blue by a consistent 25–30%** relative to
red and green. Flat in albedo, flat across both subject geometries, flat against
both 8-bounce and 1-bounce GT (B/R identical within 0.017 in all 8 rungs).
**Not a transport effect.**

But it **is** coverage-sensitive: ρ_B is more negative than ρ_R in all eight
rungs. That is the only handle anyone has on it.

### 5.5 The indirect-fraction ladder itself

A controlled instrument nobody else has: frozen geometry, frozen cameras, one
variable (albedo), spanning first-bounce share 0.45–0.88 on two shapes, plus a
no-bounce twin (F = 0.00% exactly) and a luminance-matched twin. Analytic
subject, so GT normals are exact.

---

## 6. What was excluded — do not relitigate

**Read the strength column.** These rows are not equally dead. Rows marked
*conditional* or *by elimination* **should** be reopened under the right
conditions; only *positive* rows are closed.

| Hypothesis | Strength | Why it's dead |
|---|---|---|
| Low envmap resolution masks the effect | **positive** | Irradiance sensitivity flat 32×16 → 4K, all angles, all occlusion levels |
| Bounce leaks into albedo | **positive** (interpretation only — see below) | Persists **3.7× stronger** in the F = 0 twin. It was occlusion, not bounce absorption |
| Enclosure arm on RadioGS | **positive** | Three architectural assumptions violated simultaneously (§3) |
| TensoIR as a bounce ladder | **positive** | Independent variable doesn't vary (3 of 4 scenes at share ≈ 1.0) |
| Observability explains **shape dependence** | **positive, but narrowly scoped** | Sign reversed — crosshatch is 1.52× better observed (median 33.0 vs 21.8 cameras), 6× fewer near-invisible Gaussians, 12–19% *lower* SH error at matched albedo. ⚠️ **The observability mechanism itself is CONFIRMED (§5.2)** — what is excluded is only its ability to explain the between-subject slope difference |
| Single-bounce architecture | ⚠️ **by elimination, n = 1 subject** | `xh_a0.85` pred/GT₁ = 0.839 — cannot under-predict one bounce if bounce-limited. Robust to render flags (0.899 worst case). **See caveat below** |
| Frozen transport content is a large error | ⚠️ **conditional — one cell clears** | 0.19–0.90% at F = 4–10%. **See exception below** |
| Chromatic effect on TensoIR benchmark | ⚠️ **CONTESTED — do not treat as excluded** | **See below** |

**⚠️ Frozen transport content — the exception matters.** The trustworthy
`mean × median` implied error **clears the noise floor in exactly one cell:
interior + standup-like deformation, 3.13% against a 2.4% floor**
(`lumimotion_campaign_summary.md:86`). That cell is *enclosed scene + substantial
deformation* — precisely the regime a dynamic-transport paper would target. The
hypothesis is dead **in open-platform benchmark scenes**, not everywhere.

**⚠️ Single-bounce architecture — the exclusion rests on one rung.** The groove
**never** drops below 1.0 (1.223 / 1.150 / 1.175 / 1.344). The whole exclusion is
`xh_a0.85 = 0.839`, one rung of one subject, with ~0.10 of headroom. §21.6 says
so in its own words and it should be carried here:

> *"The exclusion of (1) rests on one value below unity (0.839) plus a monotone
> trend of four points. It would be strengthened cheaply, and I would not build
> on it until it is."*

This is the exclusion that killed direction (C). It deserves strengthening before
being relied on further.

**⚠️ Bounce-into-albedo — the interpretation was retracted, the measurement was
not.** §13.1 of `phase3b_object_centric_highf.md`: *"The measurement was correct:
a systematic, monotone, chromatically structured albedo error that tracks
per-pixel indirect fraction, ~19% of true albedo, is really there in
`groove_a0.55`."* Only the causal reading ("bounce light absorbed into albedo")
died. **A real, still-unexplained albedo error remains open.** Separately,
§15.2's "F effect is 89.6% of the gap net of luminance" (`:1322`) says the F
effect **is** real — it is not evidence for this row and has been moved out of it.

**⚠️ Chromatic effect on TensoIR — CONTESTED, previously listed as excluded.**
An earlier draft of this handover recorded this as "an artifact of multiplying by
near-zero-blue albedo; R/B falls 12.2× → 1.65× once glossy indirect is included."
**The value 1.65× does not appear anywhere in `docs/`, and the source records the
opposite conclusion.** `phase0_tensoir_indirect_fraction.md:218-227` is the
*corrected* per-channel table and reports R/B = **12.2× / 4.3× / 5.8× / 3.2×**
(armadillo / ficus / hotdog / lego) as a standing finding: *"Indirect light in
every one of these scenes is strongly red-biased… The scalar column understates
the red channel by 1.25–1.56×."* `:365` then makes per-channel reporting a
**requirement** for the ladder. Until someone reconciles this, **treat the
chromatic effect on TensoIR as live, and report per channel.** (Note this is a
*different* quantity from §5.4's blue over-attribution, which is a model defect,
not a scene property.)

---

## 7. What is open

**§20's shape dependence has no mechanism.** Both candidates excluded.

**Successor hypothesis (unregistered, n = 2, do not build on it):** the
crosshatch has *better* radiance and *worse* geometry — normal MAE 12.63–13.44°
vs the groove's 5.63–5.95°, on **finer** Gaussians.
`rendering_equation_radiosity` samples the hemisphere **around the estimated
normal**, so a 13° error misaims the whole gather. Normal-MAE ratio ≈ 2.2 against
attribution-slope ratio 1.93. **Two matching ratios from n = 2 is not evidence.**
Test is cheap (analytic subject ⇒ exact GT normals, no render) but **must be
pre-registered first.**

**Also open:** whether coverage→error holds for the arbitrary hemisphere
directions the gather actually uses (needs the probe render — **render only, the
scoring path is done**, §5.2); the blue bias mechanism; whether any of this
generalises beyond synthetic purpose-built subjects; **the F-correlated albedo
error itself**, whose *interpretation* was retracted in §13 but whose
measurement stands (~19% of true albedo, §6); and **the chromatic effect on the
TensoIR benchmark**, which §6 lists as contested rather than excluded.

---

## 8. Candidate directions, honestly assessed

### (A) Diagnostic / benchmark paper — most achievable

*"Gaussian inverse rendering under-recovers indirect illumination; the deficit
tracks first-bounce share; SH radiance error falls monotonically with view
coverage; and standard benchmarks structurally cannot detect either."*

**Have:** two verified laws, a benchmark critique, a controlled ladder, a
released instrument, rigorous provenance (pre-registrations, retractions).

**Missing:** breadth. **Only RadioGS has been measured properly.** A diagnostic
about "Gaussian IR methods" that measures one method is a paper about that
method. Needs 4–6 training runs — GI-GS, IRGS, LumiMotion, possibly PTIR-GS — on
the existing ladder. Infrastructure and analysis code already exist.

**Risk:** analysis papers are harder to place at CVPR than method papers, and
some supervisors weight them less.

### (B) Observability / unobserved-radiance — most interesting, least proven

The information-theoretic version: *the regions that generate the most indirect
light are the regions least observed.* And specifically — **RadioGS's entire
published contribution is a loss that supervises indirect radiance in unobserved
directions, and it still under-recovers in unobserved concavities.**

Possible dynamic angle: deformation changes visibility, so a sequence observes
concavity interiors no static capture can. **But this is close to LumiMotion's
existing "motion as supervision" thesis** and is entirely unverified.

### (C) Multi-bounce transport on deforming geometry — framing dead

Excluded by §21. The deficit is not missing bounces, so adding multi-bounce
transport does not fix it. Additionally: temporal GI amortisation is classical
(§2.3), and static multi-bounce Gaussian IR is now crowded (§2.1).

### (D) Direction 4 — anisotropic / deformation-coupled materials

Never tested; deferred at the outset. **RadioGS's own limitations section names
this as their future work.** Anisotropy is strongly normal- and tangent-dependent
— a regime where the low-frequency-lighting argument that weakened Direction 2
does not apply. Cloth is the canonical case and is the stated personal interest.
Genuinely different paper, not a variant.

---

## 9. Methodological lessons — read before designing any measurement

These were each learned by getting something wrong. Eleven silent failures were
caught over the campaign; several would have produced confidently wrong papers.

1. **A probe can test the wrong thing convincingly.** Probe B's brightening was real, visible, and irrelevant.
2. **Pooled correlations across heterogeneous units mask within-unit effects.** Between-unit variance swamped signal by 13–15×.
3. **Correlating a signed quantity against an unsigned one is ≈0 by construction.** Pearson r is invariant to subtracting a per-series constant, so removing an offset alone changes nothing.
4. **Small denominators destroy mean-based relative statistics.** Use medians or filter.
5. **Channel-mean scalarization hides chromatic effects entirely.**
6. **Measure the denominator before chasing the numerator.** Indirect fraction was the cheapest measurement and the decisive one — and it came last.
7. **Verify a restriction actually restricts.** A mask-channel bug made "dynamic-only" a no-op across four probes.
8. **Test whether the mechanism fires in the healthy control.** This caught two wrong diagnoses that were each asserted confidently first.
9. **Check the transfer function of every buffer before comparing two.** An sRGB-vs-linear comparison inflated a result 3.7× and briefly produced a compelling wrong story.
10. **Authored flags are not physical quantities.** `diffuse_bounces = 128` does not mean multi-bounce energy exists.
11. **Pre-register predictions and falsifiers.** Three times this caught a result that "read as confirmation" — including one where the ordering was perfect and the level was wrong by 2.5×.
12. **Verify conservation identities numerically, not visually.** The `MAX_FEATURES` overrun (§10) produced entirely plausible images that summed to **3.66× their own total**. Eyeballing the output and ruling out background compositing both failed; it was caught only by checking two identities that must hold *exactly* — `direct + indirect == diffuse + specular`, both **1.0000**.
13. **A validity gate is defined by its statistic; substituting another invents failures.** `verify_tensoir_gt.py` used **max-absolute** where the real gate was **median-relative**. That reported four scene failures, and the fabricated magnitude was then argued from ("1.92 vs 1e-8 is too large to be a scale convention") — wrong by orders of magnitude *of statistic choice, not of data*. The same wrong metric flags the passing groove at 1.22e-01.
14. **At n = 4, use the t interval, not the normal one.** `t₀.₉₇₅,₂ = 4.303` vs 1.960 — the normal form understates the CI by **2.2×**, and it manufactured a "non-overlapping CIs" claim that §20 and this handover both rested on (§5.1). **Every ladder in this campaign is n = 4.**
15. **Trace the call site before declaring a footgun fired.** §22.8 asserted the whole campaign's renders were mis-flagged, from reading `get_combined_args` alone. `train_rung.sh:91-92` passes the flags explicitly; §23 re-rendered and got **bit-identical** output. Reading a mechanism is not evidence that it executed.
16. **Snapshot before the first edit, not after.** A `radiogs.py` backup taken after the first edit restored the *broken* version; recovery came from `git checkout`.

---

## 10. Environment and footguns

**Git:** conda shadows OpenSSL. Use `gitssh` alias
(`LD_LIBRARY_PATH= GIT_SSH_COMMAND=/usr/bin/ssh git`) for push/pull/fetch; plain
`git` for local ops. **Never `git add .`** — submodules are dirty from compilation.

**Blender — this has bitten twice:**
- **2.93.9** for TensoIR / groove / crosshatch pipeline (~49 dB validation — 48.90 in `phase1:247`'s table, 49.1 in its headline; 3.6.13 gives 40.4)
- **4.4.0** for LumiMotion `.blend` files (authored at 4.4.32)
- Using the wrong one silently produces non-matching ground truth

**`get_combined_args` (`arguments/__init__.py:232-234`):** `PipelineParams`
defaults overwrite trained `cfg_args` because it is built without the sentinel
that protects `ModelParams`. A **bare** `render.py` call silently gets
`back_culling=False, diffuse_sample_num=256` while training used `True, 64`.
`train_rung.sh` passes them explicitly and is safe. **Any new bare call must
too.** Also: an argparse default of `None` never survives the merge.

**Rasterizer channel limit:** `diff-surfel-rasterization/cuda_rasterizer/config.h:16`
defines `MAX_FEATURES 24`; `forward.cu:315` declares `float F[MAX_FEATURES]` as a
fixed stack array. Shipped packing is exactly 23. **Writing more silently
corrupts every channel from index 24 up, including `radiosity`** — no crash,
plausible-looking output.

**Long jobs:** always tmux, launched by hand. `nohup` jobs survive session
termination and are **invisible in a new session** — this caused two concurrent
drivers writing to the same directory. Check `pgrep -af <script>` before any
launch.

**Disk:** all data and outputs on `/data` via symlinks. `/` filled once and
killed a training run mid-flight.

**`update_bvh`** requires fixed triangle topology and only fires when
`lr_scale > 0`.

**`points3d.ply` guard.** `run_rung.sh` and the loader disagreed about whether one
should exist. The guard now checks **contents** (100k points in [−1.3, 1.3],
the loader's auto-generated cube) rather than presence; presence-checking cost a
cycle and rejected legitimate re-runs.

**Envmap path.** The pipeline's sunset HDR is
`data/tensoir_blend/blender_download/light_probes/high_res_envmaps_2k/sunset.hdr`
— not any `assets/envmaps/` path.

### 10.1 Hazards specific to threading time through (from `CLAUDE.md`)

Every one of these is silent. If direction (B) or a dynamic extension is revived,
read this list first.

- **`precompute_incidents` bakes caches for geometry current at call time**
  (`radiogs_gaussian_model.py:845`, every `indirect_update_interval = 100` iters
  via `train.py:109-111`). Once time is threaded, the radiometric consistency loss
  is computed against the **wrong frame's geometry**. No crash, just wrong numbers.
  **This is the single biggest hazard in the codebase.**
- **`Camera` has no `frame_id`.** Thread it via `dataset_readers` → `CameraInfo` →
  `cameraList_from_camInfos`/`loadCam` → `Camera`. **`Camera.uid` is re-enumerated
  densely and *separately per split* — it cannot double as a frame index.**
- **`restore_from_refgs` unpacks `env_1`/`env_2` and never loads them into
  `self.env_map`** — canonical-stage lighting is silently discarded. Pre-existing.
- **`train_init` → `train` handoff resets materials**
  (`radiogs_gaussian_model.py:288-290`).
- **`train.py` never densifies** (`is_densify` hardcoded False, `:135`; the only
  densification is `train_init.py:199,213`). The fixed-topology invariant the
  architecture assumed **already exists** rather than needing to be imposed.
- **`viewpoint_stack` sampler** (`train.py:114-116`) needs frame-aware batching.
- `scene/__init__.py:97-111` builds a pooled `train_rays` nothing reads (dead).

### 10.2 Settled architecture decisions (from `CLAUDE.md`, so they are not re-derived)

Recorded with their reasoning. Mostly moot if direction (C) stays dead, but (B)
and (D) still need the substrate argument:

- **Canonical Gaussian set + deformation field, fixed topology.**
- **Topology freezes at the `train_init` → `train` boundary** — train_init builds
  the canonical frame; train deforms and applies radiometric consistency.
- **Per-Gaussian embedding (E-D3DGS style) over a coordinate-based HexPlane**,
  *because the light-transport cache is indexed by canonical Gaussian identity and
  a per-Gaussian embedding shares that index.* Also an improvement over ST-2DGS
  and LumiMotion, which both use coordinate MLPs.
- **RadioGS, not RadiosityGS** — RadiosityGS has **no persistent per-Gaussian
  radiosity state** (`radiosity = emissions.clone()` fresh every call), so it
  re-solves from scratch each iteration. RadioGS has the persistence primitive.
  *Accepted risk:* RadiosityGS's per-call geometry-agnosticism structurally
  prevents stale-cache bugs; RadioGS keeps that hazard.

---

## 11. Assets

**Trained models:**
- RadioGS on 4 TensoIR scenes (armadillo, ficus, hotdog, lego) — validated against paper
- LumiMotion on hook (reproduced, within ~1 std of paper), jumpingjacks, standup
- Groove ladder ρ ∈ {0.20, 0.40, 0.55, 0.85} + no-bounce twin + luminance-matched twin
- Crosshatch ladder ρ ∈ {0.20, 0.40, 0.60, 0.85}

**⚠️ Incomplete:** the groove's **diffuse arm is 1/4 done** — only `groove_a0.55`
has `render_indirect_diffuse` (the pass was added in §19.2, after the other three
rendered). So §21.4's diffuse-only comparison is **crosshatch-only** and §5.1's
+1.850 has no groove counterpart. Fix is three `render.py` calls on banked
models, which **must carry `--diffuse_sample_num 64 --back_culling`** or they
reproduce the §23 footgun.

**Rendered, validated, NOT trained:**
- **Phase 2 albedo sweep — 18 rungs, 3 subjects, F = 1.55–11.63%, five matched-F cells.** Zero render cost to use.
- Phase 2b enclosure arm, 8 rungs, **F = 10.09–56.76%** (arm invalid; data sound). *The frequently-quoted 1.90% is the open **control**, not the bottom of the arm — `phase2b_high_f_arm.md:25,250`.*

**Ground truth:**
- TensoIR AOV re-renders, 8-bounce and 1-bounce, all four scenes, all passing reconstruction at ~1e-7 and scale 1.000
- Groove/crosshatch 1-bounce probes (20 views each)
- `data_phase3b/probe/` — the shape/albedo selection probes used to choose the crosshatch rungs

**Derived, and NOT in git:**
- `docs/phase3b_assets/obs_*.npz` — 84 MB of per-Gaussian coverage/SH-error arrays, **gitignored**. A fresh clone will not have them. Regenerate with `observability.py` (~10 min for 8 models on 8 GPUs).
- `outputs_phase3b/*/radiogs/test_bcon/` and `test_bcoff/` — §23's flag-check renders. Safe to delete (§13); regenerate in ~5 min.

**Source assets:**
- TensoIR `.blend` files (`data/tensoir_blend/`) — found inside TensoIR's "generate your own dataset" package
- **Joanna's LumiMotion `.blend` files** — 5 scenes + normals/roughness/dynamic-mask variants, author-shared

**Instrumentation:** `scripts_local/phase{0,1,2,2b,3a,3b}/`. The load-bearing ones:

| script | what it does |
|---|---|
| `phase3b/gt1_ladders.py` | pred/GT₈, pred/GT₁, first-bounce share, both ladders. `--split` selects the render dir (`test`, `test_bcon`, …); self-gates on reproducing §15.1's published groove row |
| `phase3b/observability.py` | per-Gaussian coverage + SH error. `--bc` sets `back_culling` explicitly; `--probe_src` scores against probe views with a camera gate |
| `phase3b/obs_analysis.py` | the four pre-registered observability predictions |
| `phase3b/indirect_curve.py` | attribution across groove + TensoIR families |
| `phase3b/assess_rung.py` | the standard §8 per-rung checks; also exports `decompose`, `png`, `srgb_to_linear` used everywhere |
| `phase3b/run_rung.sh` / `train_rung.sh` | render + train one ladder rung. **`train_rung.sh:91-92` is the correct `render.py` invocation — copy its flags** |
| `phase3b/verify_rung.py` | reconstruction gate. **Median relative < 1e-5**, not max-absolute |
| `phase3b/run_probe_views.sh` + `make_probe_cams.py` | the concavity-interior probe render (not yet run) |
| `phase1/render_tensoir.py`, `phase1/exr_io.py` | Blender AOV pipeline; `exr_io.RGB_LAYERS` is a **whitelist** and returns None for absent layers — how the transmission gap hid |

---

## 12. Collaboration and outstanding obligations

**Joanna [surname — NOT RECORDED ANYWHERE IN THIS REPO], first author of
LumiMotion (CVPR'26 Highlight), Warsaw UT.** Searched `docs/`, `CLAUDE.md` and
`data/`: only the given name appears (`project_status_interim.md:259`). There is
no paper PDF, BibTeX entry, or email archive in-tree. **Get it from the email
thread or the CVPR'26 listing — do not guess it into a document that tells you to
email her.**
Responded same-day to a cold email and shared her complete Blender source files
plus detailed notes on colour management and normal conventions. Generous and
responsive.

**Owed to her, and not yet sent:**
1. **A real bug in her released eval scripts:** `eval_nvs_dynamic.py:69,86-88`
   and `eval_relight_dynamic.py:80,97-99` build the BVH once on frame 0 and never
   call `update_bvh`; training does it correctly (`train_stage2.py:155-159`).
   Fails silently. Likely *understates* her published dynamic numbers.
   **Any head-to-head comparison must fix this first.**
2. `dynamic_mask` PNGs: RGB is the segmentation, alpha is the whole-scene
   silhouette (IoU between them 0.18–0.22). Undocumented; cost us four probes.
3. Thanks, and a report of what came of the files.

---

## 13. Immediate next steps

1. **Supervisor meeting.** Overdue. The question is no longer empirical — it is
   "given this evidence, what should I write?" Bring §8's four options with the
   honest assessment attached.
2. **Do not run more measurements before that meeting.** Four mechanisms have
   been excluded; a fifth should not be adopted on two matching ratios.
3. If (A) is chosen: train the untrained Phase 2 sweep and 4–6 competing methods
   on the existing ladder. Weeks, not months, on built infrastructure.
4. If (B): pre-register the normal-error hypothesis, run the probe render
   (`run_probe_views.sh`, then `observability.py --probe_src` — the scoring path
   is implemented and camera-gated, so this is a render job only).
5. Email Joanna regardless.
6. Housekeeping: delete `test_bcon/` and `test_bcoff/` (regenerate in ~5 min);
   reorganise `docs/` into per-campaign folders with an index.

---

## 14. Personal note on the state of things

Two months, four excluded mechanisms, no method framing standing. That reads as
failure and mostly isn't: every exclusion was a real answer obtained cheaply,
and several would have become wrong papers had they gone unchecked. The
diagnostic findings are solid and independent of everything that died.

What is genuinely unresolved is whether there is a *method* here, and that is a
judgment call about scope, ambition and timeline that needs a supervisor rather
than another experiment.

The methodology developed along the way — pre-registration, healthy-case checks,
controlled ladders, the discipline of retracting one's own claims — is itself
worth carrying forward regardless of which direction wins.
