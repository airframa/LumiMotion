# Experiment 1 — Stage 2: instrumentation, dump format, and pre-registered adjudication

**Pre-data.** Written before any coverage array exists. Records Task B (addendum 2
§B) and the adjudication code, both fixed before the measurement runs.

---

## 1. Exposure instrumentation (addendum 2 §B)

Added to `scripts_local/exp1/coverage_seq.py`. Computed at **full population** —
every Gaussian as a ray origin, all 135 cameras, both arms, both `t_scale` arms —
not a subsample. Benchmarked at 30,400 rays/s, so 10.8 min per (arm, `t_scale`);
full population is affordable and avoids sampling error in the per-decile
quantiles that §B asks for.

**Crossing count.** For each ray, the number of bounding icosahedra it enters:
plane intersection within the **circumscribed** radius
`1.2584 · sqrt(2 ln(opacity/alpha_min))` in `p_g` units
(`scene/gaussian_model.py:99,618`), in front of the origin, within
`T_SCENE_MAX = 100`. Using the circumscribed rather than inscribed radius makes
this an **upper bound** on crossings — conservative for an exposure measure.

This counts what actually consumes anyhit buffer slots: the kernel assigns
`t_curr` at `gaussiantrace_forward.cu:58`, **before** the `alpha < alpha_min` test
at `:79`, so hits contributing no alpha still advance the chunk boundary.

**Mask fragility.** Per-Gaussian counts of gated cells with `|vis − 0.5| < δ`,
δ ∈ {1e-3, 1e-2, 5e-2}, accumulated in-loop at full precision.

### Dump format, and why

| key | shape / dtype | rationale |
|---|---|---|
| `xings_{arm}{tag}` | (N, C) uint16 | **per cell.** §B asks for the *distribution* (median/p90/p99/max) of crossing counts within a decile — a distribution over rays, which per-Gaussian summaries cannot reconstruct. Raw, unaggregated (brief §6). |
| `frag_{arm}{tag}` | (N, 3) int32 | per-Gaussian count of gated cells inside each δ |
| `gated_{arm}{tag}` | (N,) int32 | count of cells with `infr ∧ face` — the fragility **denominator** |

Deciles and the dynamic/static strata are per-Gaussian properties, so the
per-Gaussian counts re-aggregate **exactly** into any decile × stratum breakdown.
That is why §B's allowance for per-Gaussian summaries is taken up for fragility but
not for crossings.

**The fragility denominator is `infr ∧ face`, not all N×C.** A cell failing either
contributes `False` to the mask whatever `vis` does, so no `vis` perturbation can
flip it. `gated` is stored so both denominators remain available.

**Per-cell `vis` is not stored.** The only questions asked of it are
threshold-distance counts, computed exactly in-loop; storing it would add ~79 MB
per arm per `t_scale` and answer nothing further.

### A diagnostic that was wrong, and is now stratified

The displacement sanity check (brief §4) reported the **pooled** median
`‖d_xyz‖`, which reads `1.3e-11` — it sits inside the 78% static block and is
uninformative whatever the deformation does. It came within a hair of firing a
false "C_seq arm did not deform" alarm. It now reports and asserts on the
**dynamic** set (0.1918–0.1922 on a 3-frame smoke test, matching Task 1's 0.194
median) and prints the pooled value alongside, labelled. `HANDOVER.md` §9.2, on my
own instrument this time.

---

## 2. Pre-registered adjudication — `scripts_local/exp1/analyse_stage2.py`

**Written before the arrays existed**, so the adjudication is fixed pre-data.
Order of operations is enforced by the code, not by discipline:

1. **Addendum 2 §B interpretation rule first.** If the bottom dynamic decile has
   between-arm overflow difference ≥ 5 pp **or** `|vis − 0.5| < 1e-2` ≥ 1% of gated
   cells, the script prints **no** P1/P2/P3 verdict and exits 2. "Do not adjudicate
   P1/P2 and then caveat them."
2. **Addendum 1 §B P1 ceiling**, printed *before* the P1 verdict.
3. P1/P2/P3 against amendment 2 §4, thresholds untouched.
4. Committed JSON of every adjudication input (addendum 1 §D.1).

Both paths were exercised on synthetic arrays with the real key layout: the pass
path prints verdicts, the stop path prints none and exits 2.

### The one interpretive choice, stated

Amendment 2 §4 defines deciles on C_rigid; §3 restricts P1/P2 to `C_rigid > 0` and
P3 to `C_rigid = 0`. **Deciles for P1/P2 are taken over the `C_rigid > 0` subset of
the stratum.** Taking them over the whole stratum would place every `C_rigid = 0`
Gaussian in the bottom decile and then remove them all again, leaving it empty or
unrepresentative. The alternative is computed and reported as a sensitivity and
**adjudicates nothing**.

Ties are frequent (C_rigid is an integer count), so decile bins are not equal-sized;
boundaries and per-bin counts are both reported, per brief §6.

---

## 3. The run

~45 min wall clock, two scenes in parallel on GPUs 0 and 1. Launched by hand in
tmux per `CLAUDE.md`; `pgrep` checked clean and no other exp1 job was running.

```
tmux new -s exp1stage2
bash scripts_local/exp1/run_stage2.sh
```

Writes `docs/exp1_assets/coverage_{jumpingjacks,standup}150_v5_spec32_r2_mlp.npz`
(< 300 MB each; `*.npz` is gitignored, hence the committed JSON) and logs to
`/data/fmb/lumimotion/logs_exp1/` (on `/data`, not the repo). Then:

```
python scripts_local/exp1/analyse_stage2.py \
  --npz docs/exp1_assets/coverage_jumpingjacks150_v5_spec32_r2_mlp.npz \
        docs/exp1_assets/coverage_standup150_v5_spec32_r2_mlp.npz \
  --json docs/exp1_assets/exp1_adjudication.json
```
