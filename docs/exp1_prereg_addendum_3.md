# Experiment 1 — pre-registration addendum 3

**Written after the addendum 2 §B stop rule fired and before any P1/P2/P3 verdict
has been seen by anyone.** That blindness is the whole basis on which this document
is legitimate. See §0.

Basis: the Stage 2 run of 2026-08-24 and `docs/exp1_stage2_plan.md`.

---

## 0. The quarantine, which comes before everything else

`analyse_stage2.py` exited 2 and printed no verdict, exactly as designed. But it
also wrote `docs/exp1_assets/exp1_adjudication.json` on the stop path.

**Until §3 is complete, nobody opens that file, and nobody computes, prints or
infers P1, P2 or P3.** If the JSON contains verdict inputs, it is quarantined; if
it does not, no harm. Determine which without reading the fields.

Everything below concerns *instrument fidelity in a population*, which is not an
outcome of the experiment. The decision about the stop rule is being made blind to
the result it gates. That is the only thing separating this from moving a threshold
after seeing data, and it is not a formality.

---

## 1. What fired, and what did not

| clause | bound | jumpingjacks | standup | verdict |
|---|---|---|---|---|
| between-arm overflow difference | < 5 pp | **−7.906 pp** | **−7.496 pp** | exceeded |
| `\|vis − 0.5\| < 1e-2`, worst arm | < 1 % | 0.2371 % | 0.3820 % | **passed, 2.6–4.2× margin** |

Only the overflow clause tripped. The clause that directly measures whether a
perturbation could move the statistic passed comfortably, in both scenes.

**The sign is the concerning direction, and it should be said plainly.** Negative
means the C_seq arm carries *less* spurious occlusion than C_rigid. Overflow
double-counts occluders, depressing `vis` and hence coverage — so more overflow in
the control depresses C_rigid, which **inflates C_seq/C_rigid**. If this channel
were material it would push P1 toward a false pass. It is not being dismissed
because it is inconvenient; it is exactly why the clause exists.

Note also the bottom decile is ~3× more asymmetric than the pooled sample
(−7.9 pp vs Task A's −2.55 pp), which is the addendum 2 §B prediction confirmed:
the adjudicating population is more overflow-exposed than the population the
pooled table described.

---

## 2. My specification error, stated before the remedy

Two defects in the rule I wrote, both mine, both identifiable without reference to
the numbers:

**(a) The clauses were joined with AND when the harm mechanism is a chain.** The
defect can bias a verdict only if exposure differs between arms **and** cells sit
close enough to threshold to flip. Harm is a conjunction, so *immateriality* is a
disjunction — the pass condition should have been OR, and I wrote AND. Under the
correct logic the fragility result alone would have cleared it.

**I am not invoking this to reclassify the stop.** It is recorded because it is
true and because a reader should be able to see that the rule was stricter than its
own rationale required. The remedy in §3 does not rely on it.

**(b) The rule proxied a quantity that can be measured directly.** The overflow
clause asks "could the defect bias coverage?" via crossing counts, because when I
wrote it I was thinking of the defect as unmeasurable in the adjudicating
population. It is not. Gate (b)'s brute force already computes the correct
visibility for any chosen set of Gaussians; restricting it to the bottom decile is
a sampling change, not new machinery. **Measure the denominator before chasing the
numerator** (`HANDOVER.md` §9.6) — I specified a proxy where the direct measurement
was one flag away.

A third point, which cuts against relaxing anything: fragility at δ = 1e-2 does
**not** bound flips from perturbations larger than 1e-2, and Task A observed
|Δvis| up to 0.19 at a rate of ~0.043 % of cells. So the fragility clause alone
does not close the channel either. **Neither clause is sufficient.** That is the
strongest argument for §3 and against simply amending the rule.

---

## 3. The remedy — measure the bias where it adjudicates

**Gate (b), restricted to the population that adjudicates.** Unchanged machinery,
unchanged brute force including the `d_g² < 1e-6` clamp rejection.

**Sample.** 500 Gaussians, seed 0, drawn from the **bottom C_rigid decile of the
dynamic stratum** — the P1/P2 population, taken over the `C_rigid > 0` subset per
`exp1_stage2_plan.md` §2. Both arms (C_rigid and C_seq), both scenes. C_seq uses
the same per-frame deformed geometry the Stage 2 run used.

**Reported quantities** (all instrument fidelity, none an outcome):

1. Mask disagreement rate, per arm, per scene.
2. Mean per-Gaussian coverage bias `b_arm = mean(n_views_port − n_views_brute)`,
   per arm, in cameras.
3. **`Δb = b_seq − b_rigid`** — the single channel by which the defect can reach
   P1/P2 — and `Δb / median(C_rigid | bottom decile)` as a fraction.
4. Per-arm overflow *levels*, not only the difference. Crossings use the
   circumscribed radius and are an upper bound; if both arms exceed ~90 % the
   difference clause is saturated and uninformative, and that must be said rather
   than passing silently.
5. Fragility at all three δ, per arm, for the same population.

**Decision rule, fixed here, before the measurement:**

> **PROCEED** if `|Δb| / median(C_rigid | bottom decile) < 0.02`.
>
> P1 asks for a 1.5× median ratio. A systematic coverage bias under 2 % of the
> bottom-decile median cannot move a 50 % threshold; the margin is 25×. If this
> holds, the defect is reported as immaterial **by direct measurement in the
> adjudicating population**, addendum 2 §B is satisfied on its own terms, and
> `analyse_stage2.py` runs unchanged.
>
> **STOP** otherwise. If `|Δb|` is 2 % or more of the bottom-decile median, the
> tracer defect is material to this experiment on this substrate, and no verdict is
> written. The outcome is then a documented instrument failure, not a result about
> deformation — and the honest next step is `direction_proposal.md` §10, not a
> repaired threshold.

**No third option is authorised.** If the measurement returns PROCEED, we
adjudicate as registered. If STOP, the experiment does not adjudicate.

---

## 4. This is a fifth gate, after I declared instrument work closed

Addendum 2 §D said no further instrument validation was authorised, with §B's rule
as the one remaining exit. The rule fired; this is that exit. But it is a fifth
gate and the cost is real — five rounds of validation and no result yet.

Two things make it defensible rather than a regress. It is **terminal**: §3's rule
has a STOP branch that ends the experiment rather than generating a sixth gate. And
it replaces an argument with a measurement, which is the direction this project's
lessons all point.

**If §3 returns STOP, that is the end of Experiment 1 on this substrate.** No
sixth gate, no repaired proxy, no reinterpretation.

---

## 5. Also verify, cheaply, while the arrays are open

The Stage 2 run's own guards passed and should be recorded as such in Stage 3:
BVH refits 135 per arm in both scenes; C_rigid displacement identically zero;
C_seq per-frame dynamic median in [0.0881, 0.5585] for standup, matching Task 1's
independently measured range. The arms are what they claim to be.
