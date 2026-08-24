# Experiment 1 — pre-registration addendum 2

**Pre-data.** No coverage array exists. Amendment 2 §4's thresholds (P1, P2, P3)
are untouched and are not discussed here.

Basis: `docs/exp1_taskA_deformed_gate.md`.

---

## A. Gate (b) is reclassified, and the reason is not a tolerance

Gate (b)'s pass condition was *exact agreement on the boolean coverage mask, no
tolerance*, and Task A returned 2 disagreements in 67,500 cells on
jumpingjacks-deformed. Under the instruction as written, that is a fail.

**It is reclassified as a pass, on the following ground, which must be audited
rather than accepted.**

Gate (b) exists to answer one question: *does the port reproduce the model's own
visibility function?* It answers that by comparing the port against an independent
implementation of the same semantics. That construction assumed the tracer computes
`vis = Π(1−αᵢ)`. **It does not, in the overflow regime.** With
`MAX_BUFFER_SIZE = 16` (`submodules/surfel_tracer/src/optix/auxiliary.h:10`) and
`t_curr` assigned at `gaussiantrace_forward.cu:58` — *before* the `alpha < alpha_min`
test at `:79` — a ray crossing more than 16 bounding volumes has the Gaussian at
the chunk boundary accumulated twice.

The identification is arithmetic, not inferential:

```
1 − 0.480926 / 0.735817  =  0.3464  =  1 − (1 − 0.1916)²
```

So the brute force is not a reference for the tracer's *actual* semantics; it is a
reference for its *intended* semantics, and the two differ. The port matches the
actual behaviour, which is what the model-actual doctrine requires
(`RadioGS: observability.py:11`) — and note the defect was present during training,
so LumiMotion's learned Gaussians were optimised against exactly this visibility
function. Measuring with a corrected tracer would measure something the model never
experienced.

**Outcome-independence audit.** The mis-specification is a property of the kernel
established by source reading and confirmed by an exact arithmetic identity. It
would hold whether or not it produced any disagreement. It was, in fact, asserted
in the *opposite* direction before the data existed — `exp1_stage1_gate.md` §3.4
claimed the buffer "cannot change the mask" — and that claim has been retracted by
measurement. **Passes.**

⚠️ **This is not a general licence.** It applies to this gate, for this reason.
Any future disagreement must be diagnosed to a specific, source-located,
arithmetically-confirmed cause before it may be reclassified. A disagreement that
is merely small remains a failure.

**Option 3 is rejected** — fixing the tracer means rebuilding a compiled submodule,
which `CLAUDE.md` forbids unprompted, breaks comparability with the trained model,
and contradicts the paragraph above.

---

## B. Required before Stage 2 adjudicates: exposure in the population that adjudicates

This adopts Task A's option (2) and extends it, for a reason worth stating.

**The §4 exposure table is pooled.** 17–27% of rays overflow; mean |Δvis| ~2e-5;
between-arm signed difference ~2e-6; 2 flips in 270,000 gated cells. Those numbers
are computed over a 500-Gaussian random sample across the whole population.

**P1 and P2 adjudicate on the bottom C_rigid decile**, which is not that
population. It is the *most occluded* Gaussians in the scene — and a ray is
occluded precisely because it passes through a lot of geometry, which is the same
condition that causes buffer overflow. The bottom decile is therefore plausibly the
most overflow-exposed population in the scene, and the pooled table says nothing
about it. `HANDOVER.md` §9.2 is the campaign's most repeated lesson and it is
exactly this: pooled statistics across heterogeneous units mask within-unit
behaviour.

A second, unquantified concern: overflow double-counts one Gaussian *per chunk
boundary*. The maximum observed crossing count is 1006 (jj), which is ~62 chunk
boundaries, so the perturbation is not bounded by the single-boundary case measured
so far. The countervailing argument — that a ray crossing 1006 volumes has true
`vis ≈ 0` and is mask-saturated anyway — is plausible and is exactly the shape of
argument this campaign has learned not to trust.

**Requirement.** `coverage_seq.py` additionally records, per arm and per `t_scale`
arm, quantities sufficient to report the following **per C_rigid decile** and per
dynamic/static stratum:

1. Fraction of rays crossing more than 16 bounding volumes; and the distribution of
   crossing counts (median, p90, p99, max).
2. **Mask fragility:** fraction of gated cells with `|vis − 0.5| < δ` for
   δ ∈ {1e-3, 1e-2, 5e-2}. This is the direct measure of how many mask cells could
   flip under a perturbation of a given size, and combined with (1) it bounds the
   defect's reach without a second brute force.
3. The between-arm difference in (1), per decile — the single channel by which the
   defect could bias C_seq/C_rigid.

Per-cell `vis` need not be stored if per-Gaussian summaries suffice; choose the
dump format accordingly, and state it.

**Interpretation rule, fixed here.** If, in the bottom decile, the between-arm
overflow-rate difference is under 5 percentage points **and** the fraction of cells
with `|vis − 0.5| < 1e-2` is under 1%, the defect is reported as immaterial to the
verdict and the verdict stands as measured. If either bound is exceeded, **stop and
report before writing a verdict** — do not adjudicate P1/P2 and then caveat them.

---

## C. Sixth declared deviation

Added to amendment 2 §8, to be carried into the Stage 3 write-up:

> **§8.6 — the anyhit buffer defect.** LumiMotion's released tracer double-counts
> the chunk-boundary Gaussian when a ray crosses more than `MAX_BUFFER_SIZE = 16`
> bounding volumes. Measured exposure: 17–27% of rays overflow; mean |Δvis| ~2e-5,
> worst observed 0.19; 2 mask flips in 270,000 gated cells. The coverage statistic
> is a threshold at 0.5 and is robust to this; `vis` itself is not. Coverage
> numbers here are the model's own visibility, defect included, by design.

---

## D. Instrument work ends here

Four gates have now been run and each found something real: the BVH-template
hazard, the `d_g²` clamp artefact, this buffer defect, and a latent `float64`
`fid` assertion in `coverage_seq.py` that would have aborted Stage 2. That record
justifies the gates. It does not justify an indefinite number of them.

**No further instrument validation is authorised before Stage 2.** The §B
measurement is part of the Stage 2 run, not a fifth gate preceding it. If §B's
interpretation rule triggers a stop, that stop is the one remaining exit; otherwise
Stage 2 adjudicates P1, P2 and P3 against amendment 2 §4 as registered, and Stage 3
is written.

---

## E. Corrections to prior documents

1. **`exp1_stage1_gate.md` §3.4** claimed the 16-hit buffer "cannot change the
   mask." The order-independence half holds; the buffer half does not. Retracted
   and annotated in place.
2. **Addendum 1 §D.2** said gate (b)'s zero disagreements were evidence the buffer
   "does not bite here." Superseded by direct measurement. The accurate statement,
   for Stage 3: *the buffer does overflow, on 17–27% of rays, and does perturb
   `vis`; it almost never changes the mask, because the mask is a threshold at 0.5.
   The mask is robust to the defect; `vis` is not.*

---

## F. Owed upstream — now two bugs

`HANDOVER.md` §12 records one obligation to the author. There are now two:

1. **Stale BVH in the two dynamic eval scripts** (`scripts/eval_nvs_dynamic.py:69,86-88`,
   `scripts/eval_relight_dynamic.py:80,97-99`). Likely *understates* the published
   dynamic numbers.
2. **Anyhit buffer double-counting** in `surfel_tracer`, as diagnosed above. This
   one affects training as well as evaluation, and it perturbs `vis` rather than
   the coverage mask — so its effect on published results is unknown to us and
   worth flagging as such rather than characterised.

Both are real, both are diagnosed to `file:line` with reproducible arithmetic, and
neither is a criticism of the work. **Send them.**
