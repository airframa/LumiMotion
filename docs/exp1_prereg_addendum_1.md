# Experiment 1 — pre-registration addendum 1

**Addendum, not amendment.** `exp1_prereg_amendment_2.md` §4's thresholds are
untouched. Three additions, made after Stage 1 (instrument validation) and **before
any coverage array exists**: one tightens a gate, two are reporting requirements.

The distinction matters. Amendment 2 changed *what would count as a pass*, which is
why it carried an outcome-independence audit per change. Nothing here does. If a
later reader finds a threshold moved in this file, that is a defect.

---

## A. Gate (b) must also run on a deformed frame

**Stage 1 gated the arm the hypothesis does not depend on.**

Gate (b) was run on the static configuration (`exp1_stage1_gate.md` §3.4), which is
exactly the C_rigid arm — the control. The C_seq arm, which carries the entire
hypothesis, is currently covered only by `BVHGuard`. That guard verifies the
acceleration structure was refit to the geometry being traced, which is the right
invariant and is not in question. But it is a *consistency* check on the call
pattern, not an independent check that the deformed-path visibility numbers are
correct.

`exp1_stage1_gate.md` §3.5 says this in its own words: *"It was run on the static
configuration only."*

**Requirement.** Re-run gate (b) unchanged — same 500 Gaussians, same seed 0, same
exact-agreement pass condition, same brute-force implementation including the
`d_g² < 1e-6` clamp rejection — on **one deformed frame**, both scenes. Use frame
index 142 (jj) and 149 (standup): the per-time maxima of median `‖d_xyz‖`
(`exp1_stage1_gate.md` §1.1), so the geometry is as far from canonical as the
sequence goes.

Cost is the same 1–3 minutes per scene. **Pass condition is unchanged: exact
agreement on the boolean coverage mask, no tolerance.** If it disagrees, diagnose it
as the standup cell was diagnosed; do not proceed to Stage 2 with a known
discrepancy in the treatment arm.

---

## B. The P1 ceiling must be reported alongside the P1 verdict

Coverage is bounded above by the camera count, 135. P1 asks for a median
C_seq/C_rigid above 1.5× in the bottom C_rigid decile. **If the bottom-decile
C_rigid boundary exceeds 90, a 1.5× gain is arithmetically impossible** and P1
cannot fire regardless of the hypothesis — the same failure class as the pooled
median that amendment 2 §1 corrected.

The Stage 1 incidental (mean `n_views` 97.75, median 121 out of 135 for
jumpingjacks, canonical, 0.3% sample) makes this worth checking rather than
assuming. That number is not a result and nothing here treats it as one; it is a
reason to compute the ceiling before writing a verdict.

**Requirement.** Report, per scene and per stratum, before the P1 verdict:

- the bottom-decile C_rigid boundary and the decile's median C_rigid
- the implied ceiling `135 / median(C_rigid | bottom decile)`
- whether that ceiling is below 1.5×

**No threshold changes.** If the ceiling binds, P1 is reported as *structurally
unpassable on this capture* rather than as evidence against the hypothesis, and
**P3 becomes the load-bearing prediction** — P3 is a rate ratio between two
populations and has no ceiling by construction. The fail-branch in amendment 2 §5
is unaffected and is still the only permitted follow-up.

---

## C. P3's static control — declared sensitivity, primary unchanged

Stage 1 corrected Stage 0: the binary gate is multiplicative, so "static" Gaussians
are not identically still. 0.92% (jj) / 1.29% (standup) of the static set moves at
all; 0.11% / 0.17% moves more than 0.01 world units; the movers sit just under the
0.5 threshold (`exp1_stage1_gate.md` §1.2).

P3's static arm is the control, so contamination inflates the denominator's rescue
rate and biases the ratio *down* — toward the null, i.e. conservative. At 0.1–0.2%
it does not threaten a 2× ratio.

**Primary stays `binary_feature > 0.5` / `< 0.5`, exactly as registered.**

**Additionally report, as a declared secondary with no threshold attached:** P3
computed with the static control restricted to `binary_feature < 0.01`. Stage 0
showed the selected set changes by only 0.3% between thresholds 0.01 and 0.99, and
Stage 1 showed the meaningful movers are those near 0.5 — so this cut removes the
contamination while keeping ~99.7% of the control. It costs nothing: the raw arrays
and `binary_feature` are both dumped.

Report the mover counts from `exp1_stage1_gate.md` §1.2 in the Stage 3 write-up, so
the control is auditable (amendment 2 §2's known-weakness clause).

---

## D. Two record-keeping requirements

1. **Commit a derived summary, not only the arrays.** `*.npz` is gitignored, as
   `obs_*.npz` was (`HANDOVER_REVIEW.md` A5). For a pre-registered result the
   adjudication must be reproducible from the committed record: write decile
   boundaries, per-decile medians, rescue counts and rates, and all P1/P2/P3 inputs
   to a committed JSON alongside the write-up.
2. **The order-independence argument is incomplete; the measurement covers it.**
   `exp1_stage1_gate.md` §3.4 shows `vis = Π(1−αᵢ)` is order-independent and that
   the early break at `T < 0.03` cannot flip a 0.5 mask. Both hold. What it does not
   address is the 16-hit anyhit buffer overflowing while `T` remains above 0.03,
   which could drop occluders and inflate `vis`. Gate (b)'s zero disagreements over
   135,000 cells against a brute force that uses every Gaussian is empirical
   evidence this does not bite here. **State it that way in Stage 3** — as covered by
   measurement, not by the argument.
