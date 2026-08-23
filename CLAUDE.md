# CLAUDE.md — LumiMotion / observability-under-deformation

## Read this first
This worktree pursues **one** research direction. Read, in order:

1. `docs/HANDOVER.md` — authoritative account of the two-month RadioGS campaign.
   Four mechanisms excluded by measurement. Read §5, §6 and §9 before proposing
   anything.
2. `docs/HANDOVER_REVIEW.md` — corrections to the above. Where they conflict, the
   review is later and wins.
3. `docs/direction_proposal.md` — the direction this worktree exists to test.
4. `docs/exp1_coverage_under_deformation_brief.md` — the current task, with its
   pre-registration.

This file is operational only: ground rules, layout, footguns, assets.

⚠️ If any of those four files is missing from `docs/`, **stop and say so.** Do not
proceed from this file alone — it deliberately does not restate their content.

---

## Worktree layout — read before touching anything

```
/home/fmb/projects/LumiMotion                [constitutive-appearance]  ← DO NOT TOUCH
/home/fmb/projects/LumiMotion-observability  [lumimotion-observability] ← this one
```

Two git worktrees over one repository, one per research direction. **Never read
from, write to, or reason about the sibling worktree.** It is an unrelated
direction and cross-contamination between them is the specific thing this
structure exists to prevent.

⚠️ **Worktrees share one object store and one conda environment.** Two
consequences, both silent:

- **Compiled CUDA extensions are installed into the `lumimotion` env, not into a
  worktree.** If either branch rebuilds a submodule (rasterizer, tracer), *both*
  worktrees then run the new binary while showing old source. Before trusting any
  numerical result, confirm the installed extension matches this worktree's
  submodule source. If a rebuild is ever needed, say so and stop — do not rebuild
  unprompted.
- **Submodules are not independently checked out per worktree** on all git
  versions. Verify `submodules/` state here rather than assuming.

---

## Ground rules
- **DEFAULT TO READ-ONLY.** Do not modify LumiMotion source or run training unless
  asked. Instrumentation goes in **new files** under `scripts_local/`, as additive
  hooks.
- **Francesco launches all long jobs himself in tmux.** Write and verify the
  script, then hand it over with the exact command. Before proposing any launch,
  check `pgrep -af <script>` — `nohup` jobs survive session termination and are
  invisible in a new session. This previously caused two concurrent drivers
  writing to the same directory.
- Cite exact `file:line`. **Flag uncertainty rather than guessing.**
- Write analysis to `docs/`, not just chat output.
- **Never `git add .`** — submodules are dirty from compilation. Stage explicitly.
- **Pre-register predictions and falsifiers before any test with a stake in the
  outcome.** This caught three results that read as confirmation and were wrong.
- **Do not propose new experiments.** One experiment is registered. If a second
  seems warranted, argue for it explicitly against `HANDOVER.md` §6's history of
  four exclusions.

---

## ⚠️ Footguns

**The BVH is built once and never updated in the eval scripts.**
`eval_nvs_dynamic.py:69,86-88` and `eval_relight_dynamic.py:80,97-99` set
`build_bvh=True` on frame 0, then `False`, and never call `update_bvh`. Training
does it correctly (`train_stage2.py:155-159`). **Fails silently:** deformed
geometry passed into `trace()` still intersects against the stale frame-0 BVH.

This is a real bug in the released code (owed to the author, `HANDOVER.md` §12) and
it is **positioned to fake a null in the current experiment** — it would make
sequence coverage collapse onto canonical coverage, which reads as a clean
falsification. Any code path that touches visibility must be checked for it.

**`dynamic_mask` PNG channels.** **RGB** is the dynamic/static segmentation;
**alpha** is the whole-scene silhouette (IoU 0.999 with the beauty render's alpha).
IoU between them is 0.18–0.22; alpha selects 4.4–5.3× more pixels. Thresholding
alpha makes any "dynamic-only" restriction a **no-op** — it did so across four
probes before anyone checked. Prefer LumiMotion's own learned per-Gaussian split,
`get_binary_feature()`, which Probe C used and which was unaffected.

**Transport content is frozen.** The BVH is rebuilt per frame, so transport
*geometry* is frame-aware, but traced radiance comes from `_albedo_dc_stage1` — a
canonical, frame-independent per-Gaussian SH bank. Transport *content* is not.
This is a property of the method, not a bug, and it is the finding the campaign
started from.

**Blender version.** These `.blend` files are authored at **4.4.32**. Use
`~/blender-4.4.0-linux-x64/blender`. **Not** 2.93.9 — that is the TensoIR /
groove / crosshatch pipeline. Wrong version = silently non-matching ground truth.
Both 3.6.13 and 4.4.0 emit "expect loss of data"; this was checked and no scene
content is lost (206/264 resolved keys identical, geometry byte-identical, the 58
diffs are Blender 4.0 renames with values intact).

**Colour management.** `view_transform = Standard` (not Filmic), exposure 0,
gamma 1, envmap in `Linear`. Confirmed with the author.

**`sample_clamp_indirect = 10.0`** — an authored clamp bounding indirect energy,
present identically in every scene. It is one of three mechanisms suppressing
indirect light in this benchmark; the dominant one is open-platform geometry.

**Small denominators destroy mean-based relative statistics.** 18% (jj) / 56%
(standup) of dynamic Gaussians have `|L_true(canonical)| < 0.05`. Use medians, or
filter unstable denominators and report the count filtered.

**Signed vs. unsigned.** Correlating a signed residual against an angular distance
is ≈ 0 *by construction*. Pearson r is invariant to subtracting a per-series
constant, so removing a per-unit offset alone changes nothing — both corrections
are needed together. This produced a false null that nearly killed the project.

**Pooled correlations mask within-unit effects.** Between-Gaussian variance
swamped the within-Gaussian signal by **13–15×**.

**Channel-mean scalarization hides chromatic effects entirely.** A red-wall
configuration drove R to 1.58× G/B while the scalar mean *fell*. Per-channel
reporting is a standing requirement (`HANDOVER_REVIEW.md` C6), not an option.

**A validity gate is defined by its statistic.** Substituting max-absolute for
median-relative once invented four scene failures that did not exist. State the
statistic before running the gate, not after.

**Small n.** At n = 4, `t₀.₉₇₅,₂ = 4.303`, not 1.96 — the normal form understates
the interval by 2.2× and once manufactured a "non-overlapping CIs" claim. **Never
put a confidence interval on n = 2.**

**Verify the restriction restricts, and the deformation deforms.** Before trusting
any conditional result, assert numerically that the condition selects what it
claims to. Two separate silent failures in this project came from skipping this.

**Trace the call site before declaring a footgun fired.** Reading a mechanism is
not evidence that it executed. One session asserted the whole campaign's renders
were mis-flagged; re-rendering produced bit-identical output.

**Verify conservation identities numerically, not visually.** A channel overrun
once produced entirely plausible images whose components summed to **3.66× their
own total**.

**Snapshot before the first edit, not after.** A backup taken after the first edit
restores the broken version.

**Disk.** Data and outputs live on `/data` via symlinks. `/` filled once and killed
a training run mid-flight.

**Git.** conda shadows OpenSSL → use the `gitssh` alias
(`LD_LIBRARY_PATH= GIT_SSH_COMMAND=/usr/bin/ssh git`) for push/pull/fetch; plain
`git` for local ops.

---

## Key locations

⚠️ **The paths below marked `[verify]` were carried over from campaign documents
and have not been confirmed against this worktree. Confirm before citing, and
correct this file when you do.**

| what | where |
|---|---|
| BVH bug — NVS eval | `eval_nvs_dynamic.py:69,86-88` |
| BVH bug — relight eval | `eval_relight_dynamic.py:80,97-99` |
| correct BVH handling | `train_stage2.py:155-159` |
| canonical SH radiance bank | `_albedo_dc_stage1` [verify location] |
| learned dynamic/static split | `get_binary_feature()` [verify location] |
| Blender source scenes | `blend_files/` |
| our instrumentation | `scripts_local/` |
| interior scene (Test 2) | `scripts_local/test2/` |
| campaign records | `docs/` |

**Coverage statistic** is defined by `scripts_local/phase3b/observability.py` in
the **RadioGS** repo (branch `audit-notes`), not here. Port it; do not
reimplement. Path to that repo: `~/projects/RadioGS-public`.

---

## Assets

**Trained (LumiMotion):** `hook` (reproduced, within ~1 std of the paper — note
that is one scene against a 5-scene average), `jumpingjacks`, `standup`.

**Source:** the author's `.blend` files — 5 scenes plus normals / roughness /
dynamic-mask variants, author-shared. Authored at 4.4.32.

**Measured scene properties** (`docs/lumimotion_campaign_summary.md`):
indirect fraction mean 4.37% (jj) / 9.60% (standup), p99 23.7% / 50.8%. The
six-configuration Test 2 ladder runs 6.72% → 33.27% mean; **enclosure is the
driver (2.7–5×), not the render setting** (`db` 1→8 is worth only +7%).

---

## Environment
- conda env `lumimotion` (Python 3.8.18, CUDA 12.1, PyTorch 2.1)
- 10× RTX 4090 (48 GB). `CUDA_VISIBLE_DEVICES` to pick.
- `--load2gpu_on_the_fly` if OOM.
- tmux for everything long, launched by hand.

---

## Current status

**Experiment 1 (coverage under deformation) is registered and not yet run.**
It has a **read-only Stage 0 with a stop-gate** — six questions answered with
`file:line`, reported back before any code is written. Stage 0 answers may change
the design, so do not skip ahead to Stage 1.

Nothing in this direction is established. The problem statement is measured
(`HANDOVER.md` §5.2); the direction's central geometric precondition is not.

### Out of scope in this worktree
- Training anything, until the Stage 2 gate passes
- Scene-level or enclosed captures on RadioGS (`HANDOVER.md` §3 — positively
  excluded; three architectural assumptions violated simultaneously)
- The §7 normal-error successor hypothesis (n = 2, unregistered)
- Any attempt to explain the §20 shape dependence — that hunt is closed
- The `constitutive-appearance` direction, in any form
