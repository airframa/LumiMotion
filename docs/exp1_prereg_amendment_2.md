# Experiment 1 — pre-registration, amendment 2

**Supersedes §2 of `exp1_coverage_under_deformation_brief.md`.**
Made after Stage 0 (read-only) and **before any coverage array exists.**
Once committed, this is not to be renegotiated. Any further change is post-hoc.

Basis: `docs/exp1_stage0_findings.md`.

---

## 0. Why an amendment, and the test I applied to each change

Stage 0 found two properties of the asset that were not known when the original
registration was written:

- **Q3** — the cameras are a **frontal cap** (98.3° / 134.8° azimuth, all 135
  within a ~55° / ~72° half-angle cone). The subject's back is never observed in
  either arm.
- **Q6b** — **78% of Gaussians have identically zero self-displacement** at every
  *t* (`d_xyz = raw_d_xyz * binary_feature`, `utils/time_utils.py:190`; dynamic
  fraction 22.0% / 23.7%, 0.1% ambiguous).

Three amendments follow. All three make a pass *more likely*, which is a pattern
worth distrusting, so each was required to pass this test:

> **Is the change defined without reference to any outcome, and does it correct a
> defect in the instrument rather than a disappointing result?**

No outcome data exists, so the second half is guaranteed; the first half is checked
per amendment below. **Francesco should audit these three arguments specifically.**

---

## 1. Amendment A — the primary adjudication is the dynamic set, not the pooled set

**Change.** P1 and P2 are adjudicated on Gaussians with `binary_feature > 0.5`.
The pooled result is computed and reported as a declared secondary.

**This overrides Stage 0's recommendation, which was to adjudicate on the pooled
arm "so the pre-registration is not weakened."** The reason is arithmetic, not
preference:

P1 is a **median** ratio. 78% of Gaussians have identically zero self-displacement,
so their C_seq/C_rigid is 1.0 except through occluder motion — and only 22% of the
scene moves to provide that. Concavity interiors and torso-adjacent regions are
plausibly *more* static than average, so the bottom C_rigid decile is likely well
over 78% static. **If more than half the decile sits at exactly 1.0, the median is
1.0 and P1 fails regardless of whether the hypothesis is true.**

A test that cannot pass is not a conservative test — it is a broken instrument.
`HANDOVER.md` §9.13 is directly on point: a validity gate is defined by its
statistic, and choosing one that cannot fire is the same error class as
substituting max-absolute for median-relative. §9.2 is on point too, and Stage 0
cited it while recommending pooling anyway.

**Outcome-independence check:** `binary_feature` is a trained model parameter read
from the PLY, fixed before any coverage is computed, and 0.1% ambiguous. It is a
covariate, not an outcome. A Gaussian that cannot move is outside the hypothesis's
scope by construction — including it is a category error, not caution. **Passes.**

---

## 2. Amendment B — the inert falsifier is removed and replaced

**Removed.** `C_rigid ≈ C_single`. Stage 0 showed it cannot fire: C_single ∈ {0,1}
while C_rigid spans 0–135, over 135 genuinely distinct viewpoints (median pairwise
separation 40.3° / 57.8°). Reporting it as a test that passed would be false.

**Replaced by a stated non-degeneracy fact**, not a test: distinct-viewpoint count
and angular spread, reported as measured in Stage 0.

**Added — P3, which the ratio design was structurally excluding.** A Gaussian at
C_rigid = 0 that reaches C_seq > 0 is the *most direct possible* evidence that
deformation exposes what static capture cannot — and a ratio is undefined at zero,
so the original design discarded exactly the strongest cases. P3 is a proportion:

> **P3.** Let *rescue rate* = the fraction of Gaussians with C_rigid = 0 that reach
> C_seq ≥ 3. Then
> **rescue_rate(dynamic) ≥ 2 × rescue_rate(static)**.

**The static set is the control, not the contaminant.** Static Gaussians can be
rescued only by occluder motion; dynamic ones by self-motion *and* occluder motion.
If the two rates are equal, self-motion contributes nothing and the hypothesis is
false. This is `HANDOVER.md` §9.8 — test whether the mechanism fires in the healthy
control — and it repurposes the 78% that Amendment A excludes.

Using a ratio of rates rather than an absolute threshold is deliberate: an absolute
bar would have to be invented without data, and the frontal cap depresses both
rates by adding structurally unrescuable back-side Gaussians to both denominators.

⚠️ **Known weakness, stated in advance:** this assumes the back-side proportion is
similar in the dynamic and static populations. It is not verified. Report the
C_rigid = 0 count in each population so the assumption is auditable.

`C_seq ≥ 3` rather than `≥ 1` avoids counting single grazing hits.

**Outcome-independence check:** both populations and both thresholds are fixed
here, before any array exists. **Passes.**

---

## 3. Amendment C — C_rigid = 0 handling, fixed in writing

Stage 0 correctly escalated this from footnote to registration item.

- **P1, P2:** computed on `C_rigid > 0` only. Division by zero is not a choice.
  Report the excluded count.
- **P3:** computed on `C_rigid = 0` only. The two populations are disjoint and
  jointly exhaustive; nothing is silently dropped.
- **Report both counts, per scene, per dynamic/static stratum**, before any verdict.

---

## 4. The pre-registration, as it now stands

**Population.** Gaussians of one trained LumiMotion model, canonical index.
jj N = 146,400; standup N = 156,893.

**Arms.** Identical cameras (135 train), identical frame indices, identical
Gaussian set:
- **C_rigid** — `d_xyz = d_rotation = 0` exactly (reading (a); see §5)
- **C_seq** — deformation field evaluated at each frame's own `fid`

**Statistic.** `coverage(i) = ((vis > 0.5) & infr & face).sum(1)`, an integer camera
count, per `RadioGS: observability.py:160-161`.

**Predictions.** Deciles defined on C_rigid. Primary stratum
`binary_feature > 0.5`.

> **P1.** Median C_seq/C_rigid in the bottom C_rigid decile > **1.5×**
> **P2.** Median gain in the bottom decile ≥ **1.3×** the median gain in the top decile
> **P3.** rescue_rate(dynamic) ≥ **2 ×** rescue_rate(static), where rescue = C_rigid 0 → C_seq ≥ 3

**Secondary, reported without thresholds:** all of the above on the pooled set;
the `t_scale = 3.0` arm (`n_views_t3`); per-decile medians, all ten.

**Falsifiers.** Any of P1, P2, P3 failing is a failure of the primary test.

---

## 5. Fail-branch, declared now so it cannot become a post-hoc rescue

If the primary test fails, the result is **"not established under frontal-cap
capture,"** not "direction dead" — because the cap cannot distinguish *deformation
does not expose concavity interiors* from *the cameras cannot see the exposure*.

**Exactly one follow-up is permitted, and it is specified here in full:** re-run
the identical measurement with a **synthetic full-orbit camera set** — same camera
count, same radius, same statistic, both arms, no retraining, no new renders.
Coverage is a geometric quantity and nothing requires it to be evaluated only from
the dataset's cameras.

If that also fails, **the direction is abandoned** and the fallback is (D),
per `direction_proposal.md` §10.

No third attempt. No other follow-up. If the orbit re-run is reached, this
paragraph is the authority for what it may be, not a fresh judgement made after
seeing a null.

---

## 6. Canonical pose — decision

**Reading (a): `d_xyz = d_rotation = 0` exactly.** It is the structural definition
of canonical, it needs no MLP call in the control arm, and it makes the two arms
differ in exactly one thing.

**Required check, and a stop condition.** Report the distribution of `‖d_xyz(t)‖`
across all 135 train times. This doubles as brief §4's "verify the deformation
deforms." **If the canonical set is geometrically degenerate — collapsed,
self-intersecting, or otherwise not a plausible pose — stop and report rather than
reinterpreting the result.** A static capture of a configuration the sequence never
contains is not a meaningful baseline.

---

## 7. Port parameters — declared before running, per the model-actual doctrine

The coverage measured must be the coverage the model actually had
(`RadioGS: observability.py:11`). LumiMotion's values, not RadioGS's:

| parameter | value | why |
|---|---|---|
| `back_culling` | **False** | No caller in LumiMotion ever passes it; `render_ir.py:503-505` omits it. RadioGS's `--bc 1` default does not transfer |
| `light_t_min` | **0.1** | `arguments/__init__.py:92` |
| `alpha_min` | **1/100** | `scene/gaussian_model.py:106` |
| `thr` | 0.5 | unchanged; never overridden in RadioGS either |
| `t_scale` arms | 1.0 and 3.0 | reproduce both, per `observability.py:320-322` |

**BVH:** build on the first frame, `update_bvh` every frame thereafter, per
`scripts/train_stage2.py:155-159` and the four correct `scripts_local/` precedents.
**Do not copy from `scripts/eval_nvs_dynamic.py` or `scripts/eval_relight_dynamic.py`.**
Guard: assert the BVH-build arguments match the geometry handed to `trace()` on
that frame, in **both** arms — an unconditional "must update every frame" assertion
would fire falsely in the C_rigid arm, where building once is correct.

**Data path:** pass `-s` explicitly. Both models' `cfg_args` record
`source_path='/home/fmb/projects/LumiMotion/data/...'` — **the sibling worktree.**

---

## 8. Declared deviations from §5.2, to be carried into the write-up

Not blockers. They must appear as limitations rather than being discovered by a
reader.

1. **Different subjects, method and codebase.** §5.2's law was measured on RadioGS
   models of groove/crosshatch. The link to "13–35% too dark" is by analogy, not
   measurement.
2. **Per-Gaussian vs per-pixel visibility.** RadioGS's own visibility is
   per-Gaussian (`radiogs_gaussian_model.py:846-848`); LumiMotion's is per-pixel
   from a depth-reprojected buffer (`render_ir.py:217,503-505`). The port traces
   from deformed Gaussian centres — the correct analogue of the RadioGS
   construction, but **a deviation from LumiMotion's own render path.**
3. **Different culling regime.** §5.2's coverage was computed at
   `back_culling=True`; this is computed at `False`. Stage 0 established the alpha
   accumulation is character-for-character identical across the two vendored
   tracers and that the kernel differences touch only returned normal and colour —
   so this should not affect the statistic, but it is asserted from a source diff,
   not measured.
4. **Frontal-cap capture.** §5.2's cameras were a full training layout; these span
   ~98°/135° of azimuth.
5. **`.so` provenance.** The installed `surfel_tracer` binary predates both
   worktree checkouts. Tracer source is branch-invariant, which bounds the risk;
   it does not eliminate it.
