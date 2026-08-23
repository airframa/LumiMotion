# Direction proposal — observation, not amortisation

**Status:** proposal + pre-registration. Nothing here is established.
**Sources:** `HANDOVER.md`, `HANDOVER_REVIEW.md`, `lumimotion_campaign_summary.md`, `CLAUDE.md`.
All figures quoted from those; none from recollection.

---

## 1. The one-line claim

> **RadioGS invents a prior for radiance in unobserved directions. Deformation
> supplies observations instead.**

The proposed contribution is a method that uses deformation-induced visibility
change as *supervision* for interreflection in regions that no static capture can
observe — and a measurement showing that this closes a deficit that is currently
real, systematic, and unaddressed.

---

## 2. Why this is not direction (C)

This must survive first contact with a graphics reviewer, so state it precisely.

| | direction (C) — dead | this proposal |
|---|---|---|
| Role of time | a quantity to be **modelled correctly** | a source of **information** |
| Claim | transport content should vary across frames so rendering at frame *t* is accurate | visibility varies across frames, so the canonical estimate is better constrained |
| Gain measured on | per-frame render error | canonical decomposition quality (albedo, indirect, SH radiance) |
| Prior art collision | temporal GI amortisation, Chen 1990 → Müller 2021 (§2.3) | none found — amortisation reuses a solution, this acquires data |
| Killed by | §21 (bounce-limit exclusion) + 0.19–0.90% render error at benchmark F | n/a — the deficit it targets is 13–35%, not 0.19% |

The arrow reverses. (C) treats temporal variation as an error term to model.
This treats it as a measurement channel.

**This is HANDOVER §8(B)'s parenthetical, promoted to the thesis.** §8 buried it
in one sentence and called the whole option "least proven." Its empirical core is
in fact the campaign's *strongest verified* result.

---

## 3. The problem statement, already measured

§5.2 is the strongest positively-verified result in the campaign, and
`HANDOVER_REVIEW.md` verified **every figure in it** (`:103-104`).

- Spearman ρ(coverage, SH error) negative in **all 24** rung×channel cells
  (−0.085 to −0.355); decile relationship r = −0.88 to −0.97 in every rung
- Poorly observed Gaussians are **13–35% too dark**; well-observed ones sit within
  **2–7%** of GT
- Survives a luminance control (attenuates 35–40%, negative in 39 of 40 bands)
- Passes the healthy-case check (the groove shows it *more* steeply)
- Subject-independent: the two subjects agree within **~8%** at matched coverage
- High-error Gaussians are spatially concentrated in **concavity interiors**, all
  eight rungs

**The sharpest form of the problem statement:** RadioGS's entire published
contribution is a loss supervising indirect radiance in unobserved directions.
It is ICLR'26 Oral. And in unobserved concavities it is still 13–35% too dark.
The state of the art's headline mechanism underperforms in exactly the regime it
was built for.

That is a problem statement with a named victim, a measured magnitude, and a
subject-independent law. It is what two months bought.

---

## 4. The insight

Coverage is treated as a fixed property of the capture. **For deforming geometry
it is not.** A concavity that is occluded in one pose is exposed in another.

This is not speculative geometry — it is the structure of the existing assets.
Probe B observed that the indirect channel brightens as arms approach the torso
(`lumimotion_campaign_summary.md` §4). The underarm is a concavity that opens and
closes. In the closed pose it is high-indirect and unobserved; in the open pose it
is observed. Both conditions of §5.2's law are traversed by the deformation
itself.

---

## 5. What the method would be

Not "train on video" — that accumulates geometry and albedo into canonical space
and is what deformable GS already does. The unaddressed quantity is **transport
state**, and the two nearest methods get it wrong in opposite directions:

- **LumiMotion** freezes transport *content* — traced radiance comes from a
  canonical frame-independent SH bank (`_albedo_dc_stage1`) while the BVH is
  rebuilt per frame. Transport geometry is frame-aware; content is not.
- **RadioGS** has no time at all, and its incident-light cache is baked for
  *geometry current at call time* (`radiogs_gaussian_model.py:845`, every 100
  iters) — which becomes silently wrong the moment time is threaded
  (`HANDOVER_REVIEW.md` A3; the handover calls this the single biggest hazard in
  the codebase).

Concretely, three components, in dependency order:

1. **Visibility-weighted canonical transport accumulation.** Per-Gaussian incident
   light indexed by canonical identity, updated from the frames in which that
   Gaussian is actually exposed. This is simultaneously the method *and* the fix
   for the staleness hazard.
2. **Coverage-conditioned consistency loss.** Where a Gaussian has been directly
   observed in *some* frame, down-weight the invented prior and use the
   observation. RadioGS's loss becomes the fallback for genuinely never-observed
   directions rather than the primary supervision.
3. **Per-Gaussian embedding deformation** (E-D3DGS style) rather than a coordinate
   MLP — already a settled decision (`HANDOVER_REVIEW.md` A4) **because the
   transport cache is indexed by canonical Gaussian identity and an embedding
   shares that index.** That reasoning was recorded before this direction existed
   and it lands exactly on it.

---

## 6. The regime problem, and why it is solvable here

§5.3 is a poison pill for any method paper and it needs confronting before design,
not after:

> 3 of 4 TensoIR scenes have first-bounce share ≈ 1.0 (1.000 / 0.996 / 0.987).
> Attributions span 0.452–2.462 at essentially constant *x*.

**If the standard benchmarks cannot detect the deficit, they cannot detect its
repair.** A method that fixes indirect recovery will show ≈ 0 PSNR gain on
TensoIR. That is not a presentation problem, it is a rejection.

So the benchmark critique is not an alternative to the method paper — it is a
**required section of it**, and it is what licenses an authored evaluation set.
That is a standard and respected paper shape.

**The accessible high-indirect regime is self-occluding concave objects, not
rooms.** Phase 3a failed because it went scene-level: RadioGS depends on a
silhouette existing, the envmap being directly observed, and alpha isolating the
subject (§3) — an interior violates all three, and `Env ≡ 0` measured 9.79× too
bright. But the groove and crosshatch are concave *and* object-centric *and* they
work. High albedo on a self-occluding object buys indirect fraction without
leaving RadioGS's architectural assumptions. **Do not read "we need high F" as
"we need the interior scene."**

---

## 7. Honest risk register

| risk | severity | mitigation / status |
|---|---|---|
| Deformation may expose *very little* concavity interior | **fatal if true** | Experiment 1 below. Cheap, decisive, pre-registered |
| Reviewers read it as LumiMotion's "motion as supervision" | high | LumiMotion varies **irradiance** on a surfel (normal rotates under fixed light) to disentangle materials. This varies **mutual visibility** — a property of the transport operator, not the appearance model. Defensible, not free |
| DR-GS rejection shape ("combines existing techniques") | high | The defence is that the supervision signal does not exist in the static case and closes a measured deficit. Whether that clears the bar is a judgement call, and it is the main thing to put to the supervisor |
| §5.2 is a **lower bound** — test cameras sit on the training radius, while the gather samples arbitrary hemisphere directions | medium | The probe render lifts it. ⚠️ `HANDOVER.md` §5.2/§13.4 say the scoring path is implemented; **`HANDOVER_REVIEW.md` A1 grepped it and found `--probe_src` returns 0 matches.** Trust the review. This is implementation work, not a render job |
| The deficit may be representational, not observational | **high — see below** | §6/O2 |
| Self-authored evaluation set distrusted | medium | §5.3 gives a measured, principled reason. Also report on LumiMotion's public data with the BVH bug fixed, and predict the small gain rather than being surprised by it |

**The load-bearing dependency, stated plainly:** this direction assumes the
deficit is an *observation* problem. If it is a *representational* limit — if the
architecture cannot carry the energy no matter how well supervised — then more
observations fix nothing. That is exactly §6's single-bounce row, and
`HANDOVER_REVIEW.md` O2 says the entire exclusion rests on `xh_a0.85 = 0.839`,
one rung of one subject, ~0.10 of headroom, with §21.6 saying in its own words:
*"I would not build on it until it is [strengthened]."*

**I am about to build on it.** That is the argument for Experiment 2.

---

## 8. Pre-registration — Experiment 1

**Registered before any data is looked at. Written to be falsifiable.**

### Question
Does deformation increase per-Gaussian coverage, and does the increase land on
the Gaussians that §5.2 identifies as high-error?

Both must hold. Coverage gain on already-well-observed exterior Gaussians is
worthless — that is just more multi-view capture.

### Cost
No training. No new renders. `observability.py` already computes per-Gaussian
coverage; this applies it per-frame on assets that exist (jumpingjacks, standup,
hook). Days, not weeks.

### Primary prediction
Let *C_static* be coverage from the cameras of a single pose, and *C_seq* coverage
accumulated across the sequence. In the bottom coverage decile of *C_static*
(§5.2's high-error population):

> **P1.** Median relative coverage gain (*C_seq* / *C_static*) in the bottom
> decile exceeds **1.5×**.
>
> **P2.** The gain is *concentrated*: median gain in the bottom decile exceeds
> median gain in the top decile by at least **1.3×**.

### Healthy control — the falsifier that matters
A **rigidly rotating** object also accumulates coverage across frames. That is
ordinary multi-view capture and there is no paper in it. So:

> **P3.** Run the identical measurement on a rigid sequence (same subject, same
> frame count, same camera trajectory, rotation only — no Armature deformation).
> If P1 and P2 hold *equally* in the rigid control, **the direction is dead.**

This is HANDOVER §9.8 applied before the fact rather than after: *test whether the
mechanism fires in the healthy control.* It caught two confidently-asserted wrong
diagnoses in this campaign.

### Falsifiers, stated in advance
- **P1 fails** (bottom-decile gain < 1.5×) → deformation does not expose enough.
  Direction dead. Go to §10.
- **P2 fails** (gain not concentrated) → deformation adds views of what was
  already visible. Direction dead.
- **P3 fails** (rigid control matches) → the effect is multi-view capture wearing
  a costume. Direction dead.
- Any of the three failing kills it. I am not going to renegotiate the thresholds
  after seeing the numbers.

### Known confounds to handle before running
- **Coverage must be measured the same way §5.2 measured it**, or the comparison
  is meaningless. Use `observability.py` as-is; do not reimplement.
- **Channel-mean scalarization hides chromatic effects** (lesson §9.5). Coverage
  is scalar so this is safe here, but any follow-on that touches radiance reports
  per channel — and `HANDOVER_REVIEW.md` C6 makes per-channel reporting a standing
  *requirement*, not an option.
- **Verify the restriction restricts** (lesson §9.7). If a dynamic mask is used to
  select deforming Gaussians, confirm it selects. The `dynamic_mask` RGB-vs-alpha
  bug was a no-op across four probes. Prefer LumiMotion's own
  `get_binary_feature()`, which Probe C used and which was unaffected.
- **n is small.** If any ladder-style aggregate appears, t interval, df correct
  (lesson §9.14; every ladder in this campaign is n = 4).

---

## 9. What follows, and only if Experiment 1 passes

Sequenced so that each step is cheap and can kill the next.

**2. Strengthen §6's single-bounce exclusion.** Not a relitigation of (C) — the
proposed direction *depends on that exclusion being true*, and its own author said
not to build on it until strengthened. §21.6 says it can be strengthened cheaply.
If it inverts, the deficit is representational and §5 collapses.

**3. Complete the groove diffuse arm.** Three `render.py` calls on banked models.
**Must carry `--diffuse_sample_num 64 --back_culling`** or they reproduce the §23
footgun. This is A2 and it is owed regardless of direction.

**4. Implement `--probe_src` and run the probe render.** Lifts §5.2 from a lower
bound to a measurement over the directions the gather actually uses. Note this is
implementation *plus* render, contrary to §13.4 — see the risk table.

**5. Only then design the method.** Not before.

---

## 10. If Experiment 1 fails

The fallback is **(D) — anisotropic / deformation-coupled materials.** RadioGS's
own limitations section names it as their future work, not dynamics. Anisotropy is
strongly normal- and tangent-dependent, so the low-frequency-lighting argument
that killed direction 2 does not apply. Cloth is the canonical case and the stated
personal interest.

Cost, stated honestly: **near-zero asset transfer.** Different scenes, different
GT, different failure modes, and the two months of instrument-building do not come
along. It is a restart with a good problem rather than a continuation with a
measured one.

---

## 11. What I am explicitly not proposing

- **The §7 successor hypothesis** (normal MAE misaiming the hemisphere gather;
  ratio 2.2 vs slope ratio 1.93). Two matching ratios at n = 2. Lesson §9.11
  exists because three previous results read as confirmation and were wrong.
- **Any scene-level or enclosed capture on unmodified RadioGS.** §3, positively
  excluded, three assumptions violated simultaneously.
- **Reviving (C).** Even if O2 inverts, the novelty problem stands: temporal GI
  amortisation is 35 years old and static multi-bounce Gaussian IR is crowded.
- **A fifth mechanism for the §20 shape dependence.** That hunt is over. The shape
  dependence becomes a limitation paragraph, not a research programme.
