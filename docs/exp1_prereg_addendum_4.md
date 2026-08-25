# Experiment 1 — pre-registration addendum 4

**Pre-verdict.** No P1/P2/P3 value has been seen. Amendment 2 §4's thresholds are
untouched and are not discussed here. Three items: how the superseded stop rule is
handled in code, two reporting requirements, and one declared deviation.

Basis: `docs/exp1_addendum3_bottom_decile_gate.md`.

---

## 1. The §B rule is superseded, not deleted

Addendum 2 §B's rule is coded into `analyse_stage2.py` and **will trip again on
re-run** — the −7.906 / −7.496 pp asymmetry is a property of the data, not of the
previous invocation. So the script cannot simply be re-run, and it must not be
"fixed" by removing the rule.

**Required handling.** On the stop path, the script consults an explicit,
documented override and proceeds only if one is present:

- Print the §B rule result as measured, unchanged. It tripped; the record says so.
- Print the addendum 3 §3 authorisation immediately after, with its numbers —
  `Δb/median = 0.000400` (jumpingjacks), `0.000000` (standup), bound 0.02 —
  and a citation to `docs/exp1_addendum3_bottom_decile_gate.md`.
- Then proceed.

A reader of the script and of its output must be able to see that a stop rule
tripped and was overridden by a named, dated, committed measurement. **Deleting the
rule, loosening its bounds, or silently branching past it are all prohibited.**

## 2. The stop-path verdict leak, fixed

`analyse_stage2.py:231` dumps `R["predictions"]` before the stop branch at
`:234-237`, so the stop path wrote the verdicts it exists to withhold. Self-reported
in addendum 3 §0 and correctly not exploited.

**Required:** on any stop path, emit only the exposure/rule block. Move
`docs/exp1_assets/exp1_adjudication.json` out of the repo rather than overwriting
it in place, so the quarantined artefact is not silently replaced by a legitimate
one bearing the same name.

---

## 3. Two reporting requirements, both pre-verdict

### 3.1 Absolute counts alongside every ratio

`median(C_rigid | bottom decile)` is **5.0** (jumpingjacks) and **12.0** (standup),
with the decile spanning 1–8 and 1–19 cameras out of 135.

Two consequences:

**The P1 ceiling does not bind.** 135/5 = 27× and 135/12 = 11.25× against a 1.5×
threshold. Addendum 1 §B's concern is resolved, and this should be stated as
resolved rather than left implicit.

**But the ratio is coarse.** At C_rigid = 1 a single additional camera yields a 2×
gain. A median ratio reported alone would hide whether it represents 5→9 cameras or
1→2. **Report median C_rigid and median C_seq in absolute cameras alongside every
ratio, per decile, per stratum, per scene.** This is neutral to the direction of the
result and makes it interpretable either way.

### 3.2 P3 population counts, and its power

Only **819** (jumpingjacks, 2.5 % of 32,200) and **286** (standup, 0.77 % of
37,218) dynamic Gaussians have C_rigid = 0 — derived from the addendum 3 §1 table,
not from any verdict.

P3 is a rate ratio over those populations. At n ≈ 286 a few units move the rate
materially. **Report the C_rigid = 0 count and the rescue count, not only the rate,
for both strata and both scenes** (amendment 2 §3 already requires the counts; this
makes the rescue numerators explicit too). Do not attach a confidence interval to
these rates without stating n; `HANDOVER.md` §9.14.

**P3's threshold is unchanged.** If P3 proves underpowered, that is reported as a
property of the result, not corrected for.

---

## 4. Seventh declared deviation — the canonical set is not a static-capture set

Added to amendment 2 §8, and it is the most consequential of the seven.

> **§8.7.** C_rigid asks how visible the Gaussians would be if held still. It is a
> counterfactual on an existing representation — **not** a model of what a static
> capture would have produced. LumiMotion's canonical Gaussian set was trained on
> all 135 deformed frames, so the deformation's observations are already baked into
> which Gaussians exist and where.
>
> This is visible in the numbers above: only 0.77–2.5 % of dynamic Gaussians have
> C_rigid = 0, far fewer than a ~55°/72° frontal cap would suggest — because the
> model does not place Gaussians where it had no supervision.
>
> Experiment 1 therefore measures **exposure of an existing representation**, which
> is the right feasibility question and is what the pre-registration asks. It does
> **not** measure what a genuinely static pipeline would have reconstructed. Any
> method claim built on this must not overstate it, and Stage 3 must say so.

---

## 5. What is now settled, for the Stage 3 record

The instrument is validated in the population that adjudicates, by direct
measurement rather than by proxy:

- Δb/median = 0.000400 / 0.000000 against a 0.02 bound — 50× and ∞
- 1 mask disagreement in 270,000 cells, in the **control** arm
- Overflow **not saturated** (41.4/33.5 %, 58.8/51.3 %) — the §B asymmetry was
  real, unsaturated, and simply does not propagate into coverage
- Bottom-decile fragility under 1.8 % even at δ = 5e-2, 2,500× the mean |Δvis|
- Recomputed port `n_views` reproduces the stored Stage 2 values for 500/500
  Gaussians in both arms and both scenes — the gate measured the run that will be
  adjudicated
- C_seq per-frame dynamic medians match Task 1's independent measurement to four
  decimals, two scripts two days apart
- The C_seq arm is the **diagonal** — frame *j* uses deformation at `cams[j].fid`
  *and* camera *j*. The Task A single-frame gate held one deformation across all
  135 cameras, a configuration Stage 2 never evaluates; the buffer defect it found
  is real and general, and its impact is now measured in the configuration actually
  used.
