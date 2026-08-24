# Review of `docs/HANDOVER.md`

Line references are to `HANDOVER.md` as reviewed (521 lines). Source citations are
`file:line`. Nothing in the handover was edited.

**Summary:** the handover is accurate on the large majority of its figures. Two
numeric problems are material — a wrong CI statistic that invalidates a stated
justification (C1), and one §6 row that appears to invert its source (C6). Three
§6 exclusions are stronger-sounding than their evidence (O1, O2, O3). Five
lessons are missing from §9, all of them silent-failure class.

---

## Priority 1 — factual corrections

### C1. §5.1 confidence intervals use the wrong statistic, and the "non-overlapping" claim fails ⚠️

The CIs `[+0.777, +1.353]` and `[+1.607, +2.498]` are **normal 1.96σ intervals**.
With n = 4 points the regression has **df = 2**, so the correct multiplier is
`t₀.₉₇₅,₂ = 4.303`, not 1.960 — the normal form understates the interval by 2.2×.

| ladder | slope | stderr | as printed (1.96σ) | correct (t, df=2) |
|---|---|---|---|---|
| groove | +1.0622 | 0.1465 | [+0.775, +1.349] | **[+0.432, +1.693]** |
| crosshatch | +2.0524 | 0.2272 | [+1.607, +2.498] | **[+1.075, +3.030]** |

**Under the correct intervals the two CIs overlap on [+1.075, +1.693].** So the
claim in §5.1 ("CIs non-overlapping"), and the same phrase in §4.5's row 20 and
§0's framing, is **not supported**.

**The conclusion survives; the stated justification does not.** A proper
difference-of-slopes test gives `t = +3.66, df = 4, p = 0.0215`. Recommend
replacing "CIs non-overlapping" with that test throughout.

Recomputed from `docs/phase3b_assets/gt1_ladders.json`. Note the source document
is itself inconsistent: `phase3b_object_centric_highf.md:1925-1926` prints the
normal CIs, while §21.2 (`:2110-2113`) and §23.4 (`:2620ff`) print correct t CIs.
**§20 of the source needs the same correction.**

### C2. §5.1 slope and r values are quoted from the less precise of two computations

`+1.065` / `+0.9815` come from §20 (`:1925`, `np.polyfit`); §21.2/§23.4 give
`+1.062` / `+0.982` (`scipy.linregress`). Both correct, different estimators.
Pick one and use it consistently — recommend the linregress values, since the CI
and p-value in C1 come from that fit.

### C3. §5.1 "diffuse-only slope ≈ +1.88" — actual value is +1.850

`§21.4` (`:2154` region) and a direct refit both give **+1.8505**. §20.2's "≈ +1.88"
was a rounding. Use +1.85.

### C4. §4.4 "49.1 dB" is the headline figure; the comparison table says 48.90 dB

`phase1_blend_pipeline.md:19` and `:237` say 49.1 dB. The version-comparison table
at `:247` says **48.90 dB** for 2.93.9 (and 40.40 for 3.6.13, which §4.4 and §10
quote correctly as 40.4). The source is internally inconsistent. Recommend "~49 dB"
or citing 48.90 with the table.

### C5. §4.2 drops two figures from its own source table

- Link 1 omits **"15–112% under occlusion"** (`lumimotion_campaign_summary.md:36`).
- Link 3 omits **p99 23.7% / 50.8%** (`:38`). The p99 matters: it is the tail that
  makes the "small fraction" framing conditional.

The means `4.37% / 9.60%` are **correct and more precise** than the summary's
rounded 4.4/9.6 (`phase0_tensoir_indirect_fraction.md:269`). Rotation angles
8.7°/49.6°/91.2° and 8/49/93%, the 61%/75%, and 0.19–0.90% vs 2.4–13.2% all
verify exactly against `:36-39`.

### C6. §6's chromatic row is unsupported and appears to invert its source ⚠️

> "Chromatic effect on TensoIR benchmark | Artifact of multiplying by
> near-zero-blue albedo; R/B falls 12.2× → 1.65× once glossy indirect included"

**The value "1.65×" does not appear anywhere in `docs/`.** And
`phase0_tensoir_indirect_fraction.md:218-227` records the opposite conclusion —
that table is the *corrected* per-channel measurement, and it gives R/B =
**12.2× / 4.3× / 5.8× / 3.2×** as a standing finding: *"Indirect light in every
one of these scenes is strongly red-biased… The scalar column understates the red
channel by 1.25–1.56×."* `:365` then makes per-channel reporting a **requirement**
for the ladder, not an excluded artifact.

**Recommend deleting this row.** If something was genuinely excluded here I could
not find it; as written it would stop a fresh session from acting on a live
methodological requirement.

### C7. §11 Phase 2b range conflates the arm with its control

"F = 1.90–56.76%" — the arm is **10.09%–56.76%** (`phase2b_high_f_arm.md:25`);
**1.90% is the open control** (`:250`). "8 rungs" is correct (`:22`).

### C8. §4.4's glossy correction was not one-directional

"understating by 0.94–5.24×" — `phase2_albedo_sweep.md:70-74` shows ficus 5.24×
(understated) but **lego 0.94×, i.e. overstated**. Source wording: *"Phase 0's
anchor was wrong by 0.94× – 5.24×, not by a constant"* (`:20`). Say "wrong by
0.94–5.24×, in both directions".

### Verified correct — no change needed

§4.3's Test 2 ladder, **all six rows exactly** (`lumimotion_campaign_summary.md:57-62`).
§5.2 **every figure**: ρ −0.085 to −0.355, decile r −0.88 to −0.97, 35–40%
attenuation, 39 of 40 bands, 13–35% too dark, 2–7%, ~8% at matched coverage,
medians 33.0 vs 21.8, 1.52×, 6× fewer, 12–19% (`:2373`, `:2436-2438`, §22.2 tables).
§6's **0.839 and 0.899** (§21.2, §23.3). §5.3's 1.000/0.996/0.987, the 0.452–2.462
span, ficus 20% diffuse / 44% transmission (`:1694-1696`, `:1724`, `:1671`).
§3's 9.79× (`phase3a:409`) and 2.4–4.8× (`phase0:134`). §11's Phase 2 line,
1.55–11.63% and five matched-F cells (`phase2:18,310`). Hook "within ~1 std"
(`lumimotion_repro.md:9,42-43` — note it is one scene against a 5-scene average).

---

## Priority 3 — §6 exclusions that are stronger-sounding than their evidence

### O1. Row 1 ("frozen transport content") — the exclusion is conditional, and the exception is the interesting case ⚠️

`lumimotion_campaign_summary.md:86` records that the trustworthy `mean × median`
implied error **clears the noise floor in exactly one cell — interior +
standup-like deformation, 3.13% against a 2.4% floor.** The handover's
"~1–3% extrapolated to F = 30%" obscures that a specific configuration already
crosses.

That cell is *enclosed scene + substantial deformation* — precisely the regime a
dynamic-transport paper would target. A fresh session reading §6 would conclude
the original hypothesis is dead everywhere. Recommend stating the exception.

### O2. Row 4 ("single-bounce architecture") — excluded on one rung of one subject, and §21.6's own caveat is dropped ⚠️

The groove **never** drops below 1.0 (1.223 / 1.150 / 1.175 / 1.344). The entire
exclusion rests on `xh_a0.85 = 0.839`, one rung of one subject, with ~0.10 of
headroom (0.899 under the wrong-flag stress test).

§21.6 says this explicitly and the handover drops it:

> *"The exclusion of (1) rests on one value below unity (0.839) plus a monotone
> trend of four points. It would be strengthened cheaply, and I would not build on
> it until it is."*

This is the single most consequential exclusion in the campaign — it is what
killed direction (C). It should carry its caveat.

### O3. Row 3 ("bounce leaks into albedo") — the interpretation was retracted, the measurement was not

§13.1 (`:920-925`): *"The measurement was correct: a systematic, monotone,
chromatically structured albedo error that tracks per-pixel indirect fraction,
~19% of true albedo, is really there in `groove_a0.55`."* Only the causal reading
was wrong.

Also, the row's "F-effect is 89.6% of the gap net of luminance" is §15.2's result
(`:1322`) and says the F effect **is** real net of luminance — inside an
"excluded" row it reads as supporting exclusion when it does the opposite.

### O4. Row 5 ("observability") — correctly scoped, but §6 is a skim target

The row says "explains shape dependence", which is right. But §5.2 presents
observability as the campaign's strongest verified result, and the two sit far
apart. One clause would prevent the misread: *"the mechanism is confirmed (§5.2);
what is excluded is its ability to explain the between-subject slope difference."*

### Solidly excluded — no change

Rows 2 (envmap resolution: flat 32×16→4K at all angles and occlusion levels),
6 (enclosure arm: three architectural assumptions violated simultaneously,
`phase3a` §9), 7 (TensoIR as a bounce ladder: independent variable does not vary,
`:1694-1696`).

---

## Priority 4 — §9 methodological lessons

Lessons 1–7 match `CLAUDE.md`'s list in substance; 8–11 correspond to real events
(§9.6's healthy-case check, §10.4's transfer function, §17-18's authored flags,
the three pre-registration files). **No inaccuracies found.** Five are missing,
all of them silent-failure class and four of them my own errors.

**M1. Verify conservation identities numerically, not visually.** The
`MAX_FEATURES` overrun (§10) produced plausible-looking images that summed to
**3.66× their own total**. It was caught only by checking two identities that must
hold exactly — `direct + indirect == diffuse + specular`, both **1.0000**
(`:1822`). Ruling out background compositing and eyeballing the images did not
catch it. The footgun is in §10; the lesson is not in §9.

**M2. A validity gate is defined by its statistic; substituting another invents
failures.** `verify_tensoir_gt.py` used **max-absolute** where the real gate was
**median-relative** (§16). That reported four scene failures, and I then argued
from the fabricated magnitude ("1.92 vs 1e-8 is too large to be a scale
convention") — wrong by orders of magnitude *of statistic choice, not of data*.
The same metric flags the passing groove at 1.22e-01.

**M3. With n = 4, use the t interval.** See C1. The normal approximation
understated the CI by 2.2× and manufactured the "non-overlapping CIs" claim that
§20 and this handover both rest on. Directly relevant: every ladder in this
campaign is n = 4.

**M4. Trace the call site before declaring a footgun fired.** §22.8 asserted the
whole campaign's renders were mis-flagged, from reading `get_combined_args` alone.
`train_rung.sh:91-92` passes the flags explicitly. Corrected in §23 by
re-rendering — bit-identical. Reading a mechanism is not evidence it executed.

**M5. Snapshot before the first edit, not after.** The `radiogs.py` backup was
taken *after* the first edit, so restoring it restored the broken version;
recovery came from `git checkout`.

---

## Priority 2 — what a fresh session would need and cannot find

### A1. `--probe_src` is not implemented ⚠️ — **RESOLVED 2026-08-23, see note below**

`grep -c probe_src scripts_local/phase3b/observability.py` → **0**. §5.2 says
`run_probe_views.sh` is "written and verified" (true — syntax and flags verified,
never run), but there is **no scoring path for its output**. A fresh session would
render 240 views × 8 rungs and then discover it cannot score them. §22.7 flags
this; the handover does not.

> **Amendment, 2026-08-23 (LumiMotion Experiment 1, Stage 0).** The finding above
> was accurate when written and is **now out of date.** `--probe_src` **is
> implemented** in RadioGS at commit `ff1d1c5` ("Finalise handover: apply review
> corrections, implement --probe_src"), branch `audit-notes`:
> `scripts_local/phase3b/observability.py:275-279` defines the flag and
> `:280-282` the companion `--probe_cams`; `:324-359` is the scoring branch,
> including the probe-camera gate that refuses to score unless the rebuilt test
> cameras reproduce Scene's own (`:338-352`) and the `prefix="train"` dispatch into
> `sh_error` (`:357-359`). `verify_probe_cams` is at `:107-120`.
>
> The original A1 text is retained above rather than deleted, because the
> distinction matters: it records a real gap that was closed, not an error in the
> review. What remains true is that `run_probe_views.sh` has still **never been
> run** — the render job is outstanding, only the scoring path is now present.
>
> Not load-bearing for LumiMotion Experiment 1; recorded so it is not re-derived.
> Source: `docs/exp1_stage0_findings.md` §9.

### A2. The groove diffuse arm is 1/4 complete

Only `groove_a0.55` has `render_indirect_diffuse` — the pass was added in §19.2,
after the other three rungs rendered. So §21.4's diffuse-only comparison is
**crosshatch-only**, and §5.1's "+1.88" has no groove counterpart. Fix is three
`render.py` calls on banked models, which **must carry
`--diffuse_sample_num 64 --back_culling`** or they reproduce the §23 footgun.

### A3. §10 is missing the hazards that matter for time-threading

All recorded in `CLAUDE.md`, none in the handover, and every one is load-bearing
for the extension the project was originally about:

- **`Camera` has no `frame_id`.** `Camera.uid` is re-enumerated densely and
  **separately per split** — it cannot double as a frame index.
- **`precompute_incidents` staleness** — §10 names the mechanism but not the
  consequence: once time is threaded, radiometric consistency is computed against
  the **wrong frame's geometry**. No crash, silently wrong numbers.
- **`restore_from_refgs`** unpacks `env_1`/`env_2` and never loads them into
  `self.env_map` — canonical-stage lighting silently discarded. Pre-existing.
- **`train_init` → `train` handoff resets materials**
  (`radiogs_gaussian_model.py:288-290`).
- **`train.py` never densifies** (`is_densify` hardcoded False, `:135`) — the
  fixed-topology invariant already exists rather than needing to be imposed.

### A4. The settled architecture decisions are gone

`CLAUDE.md` records four with their reasoning; §2 mentions E-D3DGS but not the
decision or why:

- canonical Gaussian set + deformation field, **fixed topology**
- topology freezes at the `train_init` → `train` boundary
- per-Gaussian embedding (E-D3DGS) over coordinate HexPlane **because the
  transport cache is indexed by canonical Gaussian identity**, and an embedding
  shares that index — an improvement over both ST-2DGS and LumiMotion
- RadioGS over RadiosityGS **because RadiosityGS has no persistent per-Gaussian
  state** (`radiosity = emissions.clone()` per call), with the accepted risk that
  RadioGS keeps the stale-cache hazard

A fresh session would re-derive all four. If direction (C) is dead these are
mostly moot — but (B) and (D) still need the substrate reasoning.

### A5. §11 asset omissions

- `test_bcon/` and `test_bcoff/` under each model (§23; slated for deletion in §13)
- `docs/phase3b_assets/obs_*.npz` — 84 MB of per-Gaussian arrays, **gitignored**.
  A fresh clone will not have them; regenerate with `observability.py` (~10 min
  for 8 models on 8 GPUs).
- the phase3b probe directories used for shape/albedo selection
  (`data_phase3b/probe/`), which are how the crosshatch rungs were chosen

### A6. §11 should name the load-bearing scripts, not just directories

`gt1_ladders.py` (`--split`), `observability.py` (`--bc`), `obs_analysis.py`,
`indirect_curve.py`, `assess_rung.py`, `run_rung.sh` / `train_rung.sh`,
`verify_rung.py`, `run_probe_views.sh` + `make_probe_cams.py`, `plot_gt1.py` /
`plot_obs.py`.

### A7. Two more footguns worth §10

- **`points3d.ply` guard.** `run_rung.sh` and the loader disagreed about whether a
  `points3d.ply` should exist; the guard now checks *contents* (100k points in
  [−1.3, 1.3]) rather than presence. Presence-checking cost a cycle.
- **Envmap path.** The pipeline's sunset HDR is
  `data/tensoir_blend/blender_download/light_probes/high_res_envmaps_2k/sunset.hdr`.
  My first draft of `run_probe_views.sh` guessed `assets/envmaps/` and would have
  failed at launch.

---

## §12 — Joanna's surname

**Not recorded anywhere in the repo or `docs/`.** Only the given name appears
(`project_status_interim.md:259`, and `HANDOVER.md:466,475,502`). There is no
paper PDF, BibTeX entry, or email archive in-tree, and `data/` holds no LumiMotion
release metadata carrying it. **I am not going to guess it** — a wrong surname in a
handover that recommends emailing her is worse than a placeholder. Take it from
the email thread or the CVPR'26 listing.

---

## One structural recommendation (argued, not applied)

**§6 should gain a "strength" column rather than being reordered.** Its eight rows
currently span three very different epistemic states:

- **positively excluded** — envmap resolution; enclosure arm; TensoIR as a ladder;
  bounce-into-albedo (measured 3.7× *stronger* in the control)
- **excluded by elimination or on thin support** — single-bounce architecture (one
  rung, one subject, O2)
- **conditionally excluded** — frozen transport content, which clears the noise
  floor in one specific cell (O1)

§6's stated purpose is to stop a fresh session reopening settled questions. Rows
of the second and third kind *should* be reopened under the right conditions, and
a flat table cannot say so. A single column — "positively excluded" / "by
elimination, n = 1 subject" / "conditional, see exception" — preserves the
section's function while making its weak rows visible. This is a smaller change
than restructuring and it targets exactly the failure mode raised in Priority 3.
