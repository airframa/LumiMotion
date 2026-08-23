# Experiment 1 — Coverage under deformation

**Task brief for Claude Code. Read fully before acting.**
Pre-registered. Amended once, before any data was seen — see §2.
Governing documents: `HANDOVER.md`, `HANDOVER_REVIEW.md`, `CLAUDE.md`.

---

## 0. What this is and what it is not

**Question:** does deformation expose concavity interiors that a static
multi-view capture with the same camera budget cannot reach?

This is a **feasibility gate** for a research direction, not a mechanism hunt.
Four mechanisms have already been excluded by measurement (`HANDOVER.md` §6). This
is not a fifth. It tests one geometric precondition, and if the precondition fails
the direction is abandoned rather than patched.

**Standing constraints, from `CLAUDE.md`:**
- **Default to read-only.** Do not modify LumiMotion or RadioGS source. Additive
  dump hooks only, in new files.
- Cite exact `file:line`. Flag uncertainty rather than guessing.
- Write analysis to `docs/`, not just chat output.
- **Never `git add .`** — submodules are dirty from compilation.
- Long jobs are launched by hand in tmux. Write and verify the script, hand it
  over. Check `pgrep -af <script>` before proposing any launch.

---

## 1. Where the work happens

| | |
|---|---|
| **Working tree** | `/home/fmb/projects/LumiMotion-observability`, branch `lumimotion-observability`. conda env `lumimotion` (3.8.18, CUDA 12.1, PyTorch 2.1) |
| **Do not touch** | `/home/fmb/projects/LumiMotion` [`constitutive-appearance`] — unrelated direction, sibling worktree over the same repository |
| **Assets** | Trained LumiMotion models: `jumpingjacks`, `standup` (`HANDOVER.md` §11). `hook` is a third if the first two are ambiguous |
| **Coverage definition** | `scripts_local/phase3b/observability.py` in `~/projects/RadioGS-public`, branch `audit-notes`. Port the statistic; do not reimplement it |
| **Analysis record** | `docs/exp1_coverage_under_deformation.md` **in this worktree** |
| **Compute** | 10× RTX 4090. `CUDA_VISIBLE_DEVICES` to pick. `--load2gpu_on_the_fly` if OOM |

All work happens in this worktree. `~/projects/RadioGS-public` is opened for the
coverage definition and for the Stage 1 gate baseline only. Do not try to load a
LumiMotion checkpoint with RadioGS code.

## 2. Pre-registration, as amended

**Amendment, made before any data was inspected, and the reason for it:**

The original registration (`direction_proposal.md` §8) compared sequence coverage
against single-pose coverage, with a separately-constructed rigid sequence as the
healthy control (P3). That control required a rigid subject, which would require
either new assets or training — breaking the "no training" premise that makes this
gate cheap.

**Replaced with a control that is the denominator rather than a separate run:**
freeze the deformation field at canonical and re-accumulate coverage over the
*identical* camera trajectory and frame count. Camera-motion gain is then divided
out by construction, the Gaussian set is identical in both arms, and P3 is
structural rather than a second experiment.

This is a strictly stronger design and it is registered here before any numbers
exist. It is not to be renegotiated after seeing results.

### The three quantities

For canonical Gaussian index *i*, over the *N* frames of the sequence:

- **C_rigid(i)** — coverage accumulated over all *N* frames with the deformation
  field evaluated at the canonical pose for every frame. This is *the static
  multi-view baseline at matched camera budget*.
- **C_seq(i)** — coverage accumulated over the same *N* frames with deformation
  live.
- **C_single(i)** — coverage from a single frame's camera(s). Diagnostic only,
  used to check the baseline is not degenerate (§5).

Index *i* is stable across frames because LumiMotion is canonical-set +
deformation field. **Verify this rather than assuming it.**

### Predictions

Deciles are defined on **C_rigid**, not on C_seq. Low C_rigid is the
concavity-interior population — the analogue of §5.2's 13–35%-too-dark Gaussians.

> **P1.** Median C_seq/C_rigid in the bottom decile of C_rigid > **1.5×**
>
> **P2.** Median gain in the bottom decile exceeds median gain in the top decile
> by ≥ **1.3×**

### Falsifiers

- **P1 fails** → deformation does not expose enough. Direction abandoned.
- **P2 fails** → deformation adds views of what was already visible. Abandoned.
- **C_rigid ≈ C_single** → the camera trajectory does not provide multi-view
  coverage, so the baseline is degenerate and the whole comparison is void. Stop
  and report; do not reinterpret.

Either prediction failing kills it. Thresholds are not renegotiable post-hoc.

### Scope limit, stated in advance

§5.2's law was measured on **RadioGS** models of **groove/crosshatch**. This
measures **LumiMotion** models of **jumpingjacks/standup**. The link between
"low coverage" here and "13–35% too dark" there is by analogy, not by measurement.
That is acceptable for a feasibility gate and must be stated as a limitation in
the write-up. Do not report it as though the error law had been re-verified.

---

## 3. Stage 0 — read-only investigation. **Stop and report at the end.**

No code written, no compute. Produce a findings note with `file:line` for every
claim, and **wait for review before Stage 1.** The answers here may change the
design.

1. **What exactly is `observability.py`'s coverage statistic?** Is it a count of
   cameras in which the Gaussian is the front-most visible surface, an alpha- or
   depth-weighted contribution, or something else? Quote the code. §5.2's medians
   are 33.0 vs 21.8 cameras, which reads like a count — confirm.
2. **Does that path use the rasterizer or the tracer?** This matters — see §4.
3. **LumiMotion's camera layout for `jumpingjacks` / `standup`:** one camera per
   timestep, or a multi-view rig per timestep? How many distinct viewpoints total?
   This determines whether C_rigid is a meaningful baseline at all.
4. **How is the deformation field evaluated,** and what is the API for evaluating
   it at an arbitrary *t* (needed to pin it at canonical for the C_rigid arm)?
5. **Is the canonical Gaussian index stable across frames** in the sense required
   here? Cite where.
6. **What does `get_binary_feature()` return** and is it the right dynamic/static
   split to use? Probe C used it and it was unaffected by the `dynamic_mask` bug.
7. **Does the coverage computation depend on RadioGS's compiled CUDA submodules,**
   or is it pure PyTorch/NumPy over positions, cameras and a depth/alpha test?
   This determines which gate in §5 is available.

---

## 4. Hazards — read before Stage 1

**⚠️ The BVH bug will silently fake a null.** `eval_nvs_dynamic.py:69,86-88` and
`eval_relight_dynamic.py:80,97-99` set `build_bvh=True` on frame 0, then `False`,
and never call `update_bvh`. Training does it correctly
(`train_stage2.py:155-159`). If the visibility path reuses either eval script, every
deformed frame is evaluated against **frame-0 geometry** — which is exactly the
condition that would produce C_seq ≈ C_rigid and read as a clean falsification.
**Determine in Stage 0 whether the coverage path touches the BVH. If it does, fix
it in our copy before running anything, and note it.** This is the same bug we owe
Joanna (`HANDOVER.md` §12).

**⚠️ Verify the deformation deforms.** Before trusting any coverage number, assert
that per-Gaussian positions differ non-trivially between the canonical-pinned and
live arms — report median and p99 displacement. `HANDOVER.md` §9.7: a mask-channel
bug made "dynamic-only" a no-op across four probes before anyone checked.

**⚠️ Do not reimplement the coverage statistic.** Port it. Then gate it — see §5.

**⚠️ Report per channel where radiance is involved.** Not applicable to coverage
(scalar), but `HANDOVER_REVIEW.md` C6 makes per-channel reporting a standing
requirement for anything downstream.

**⚠️ Small-n statistics.** Per-Gaussian counts are large; scene-level aggregates
are n = 2. Do not put a confidence interval on n = 2. If any n = 4 aggregate
appears, `t₀.₉₇₅,₂ = 4.303`, not 1.96 (`HANDOVER.md` §9.14).

**⚠️ Small denominators.** C_rigid appears in a denominator. Gaussians with
C_rigid = 0 or 1 will dominate a mean ratio. **Use medians, and report the count
and the handling of C_rigid = 0 explicitly** (`HANDOVER.md` §9.4).

---

## 5. Stage 1 — port and gate

Write `coverage_seq.py` in the LumiMotion repo. Before it is used for anything:

**Gate — two parts, because the ideal version may not be runnable.**

*(a) Definitional fidelity.* Stage 0 must produce the exact coverage statistic
from `observability.py` with `file:line`. The port is then reviewed against that
written definition before use. Report the definition; do not paraphrase it.

*(b) Numeric cross-check.* Implement the statistic a second time, independently
(brute force, no shared helpers), and require exact agreement on the per-Gaussian
coverage array for one static LumiMotion model. Two independent implementations
agreeing is the check; this is the only context in which reimplementation is
permitted.

*(c) Stronger gate, if available.* If Stage 0 Q7 finds the coverage path is pure
PyTorch/NumPy with no dependence on RadioGS CUDA submodules, then run it directly
on one groove rung and require exact agreement with `observability.py`'s own
output. `docs/phase3b_assets/obs_*.npz` are gitignored (`HANDOVER_REVIEW.md` A5);
regenerate one rung by running `observability.py` in `~/projects/RadioGS-public`
under the **`radiogs`** conda env — a different environment, a separate shell, and
a job Francesco launches. Prefer this gate when it is available.

**A validity gate is defined by its statistic** (`HANDOVER.md` §9.13). If any
tolerance is needed, state which statistic and why before running it, not after.

**A validity gate is defined by its statistic** (`HANDOVER.md` §9.13). If a
tolerance is needed, state which statistic and why before running it, not after.

Report the gate result before proceeding.

---

## 6. Stage 2 — measure

Three arms per scene, `jumpingjacks` and `standup`:

1. C_single — one frame, diagnostic
2. C_rigid — all *N* frames, deformation pinned to canonical
3. C_seq — all *N* frames, deformation live

Same cameras, same frame indices, same Gaussian set in all three. Dump raw
per-Gaussian arrays to `.npz` — do not aggregate in the measurement script.

Then report, per scene:
- C_rigid decile boundaries and the count in each
- Median C_seq/C_rigid per decile, all ten
- P1 and P2 verdicts, stated against the thresholds in §2
- Displacement sanity check from §4
- Count of C_rigid = 0 Gaussians and how they were handled

---

## 7. Stage 3 — write up

`docs/exp1_coverage_under_deformation.md` in this worktree. Must contain:

- The pre-registration as stated in §2, verbatim, before the results
- Verdicts against P1/P2 with no reinterpretation of the thresholds
- The scope limit from §2 (LumiMotion subjects, not §5.2's population)
- Whatever went wrong, including anything caught by the gates

**If P1 or P2 fails, write the negative result properly and stop.** The fallback
is direction (D), and it is a real fallback, not a consolation. Four exclusions in
this campaign were obtained cheaply and each one was a real answer.

---

## 8. Explicitly out of scope

- Training anything
- Rendering new views
- Any scene-level or enclosed capture on RadioGS (`HANDOVER.md` §3 — positively
  excluded, three architectural assumptions violated simultaneously)
- The §7 normal-error successor hypothesis
- Any attempt to explain the §20 shape dependence
