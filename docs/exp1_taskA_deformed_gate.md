# Experiment 1 — Task A: gate (b) on the treatment arm

Required by `docs/exp1_prereg_addendum_1.md` §A. **Result: standup PASSES,
jumpingjacks FAILS with 2 disagreements in 67,500 mask cells.**

Per the addendum — *"do not proceed to Stage 2 with a known discrepancy in the
treatment arm"* — **Stage 2 has not been run.** This document is the diagnosis.

---

## 1. What was run

Gate (b) unchanged: same 500 Gaussians, seed 0, all 135 cameras, same brute force
including the `d_g² < 1e-6` clamp rejection, same exact-agreement pass condition,
no tolerance. Only the arm changed, via a new `--deform_label` flag.

Frame selection, verified rather than assumed. The addendum names frames by their
`r_NNNN` label; those resolve to array indices, and both are exactly the argmax of
per-time median `‖d_xyz‖` over the dynamic set — the addendum's stated criterion:

| scene | label | array index | t | per-time median `‖d_xyz‖` |
|---|---|---|---|---|
| jumpingjacks | `r_0142` | 127 | 0.946667 | 0.284658 (max over 135) |
| standup | `r_0149` | 134 | 0.993333 | 0.558546 (max over 135) |

The static arm was re-run first as a regression check and reproduced the Stage 1
numbers exactly (0 disagreements, mean `n_views` 97.7520 / 75.0300).

### 1.1 A guard fired on the way, and it was right to

The first attempt aborted on `camera fid does not match transforms_train.json`.
Cause: `Camera.fid` is stored **float32** (`scene/cameras.py:46`,
`torch.Tensor(np.array([fid]))`), so it is the float32 image of the float64 JSON
time — max deviation 2.94e-08.

The fix is a *stronger* assertion, not a looser one: `cam.fid == float32(json_time)`
**exactly**, elementwise. Verified: zero difference across all 135 in both scenes,
ordering preserved. `coverage_seq.py` carried the same latent defect
(`np.allclose(..., atol=0, rtol=0)`, which would have blocked Stage 2) and has been
fixed the same way. Both scripts now feed the deform network `cam.fid` directly, as
`scripts/train_stage2.py:144` does, rather than the JSON value.

---

## 2. Result

| scene | arm | mask cells | disagreements | verdict |
|---|---|---|---|---|
| jumpingjacks | static (C_rigid) | 67,500 | 0 | PASS |
| **jumpingjacks** | **deformed `r_0142` (C_seq)** | 67,500 | **2** | **FAIL** |
| standup | static (C_rigid) | 67,500 | 0 | PASS |
| standup | deformed `r_0149` (C_seq) | 67,500 | 0 | PASS |

Both jumpingjacks disagreements are `ported = False / brute force = True` — **the
tracer found more occlusion than the brute force**. That direction immediately
rules out a dropped-hit explanation.

| cell | ported vis | brute-force vis |
|---|---|---|
| Gaussian 56077, camera 103 | 0.480926 | 0.594872 |
| Gaussian 127826, camera 80 | 0.495839 | 0.514413 |

---

## 3. Diagnosis: the anyhit buffer double-counts an occluder

Four steps, each ruling out an alternative before the next.

**Step 1 — not the acceptance criteria.** Recomputing cell 1 with each brute-force
condition relaxed in turn: dropping `dd > 0` overshoots wildly (vis → 0.000000, 85
"occluders" — these are the source Gaussian's own neighbours *behind* the offset
ray origin, which the BVH correctly never returns); dropping the parallel rejection
changes nothing. Neither explains the gap.

**Step 2 — not per-Gaussian alpha.** Each candidate occluder was traced *in
isolation* by pushing every other Gaussian 1000 units away and rebuilding the BVH.
Every per-Gaussian tracer alpha matched the brute force exactly, and the **product
of the per-Gaussian tracer alphas was 0.594872 — precisely the brute-force value**,
against 0.480926 with the full scene present. So the disagreement is not in any
individual alpha; it appears only in aggregate.

**Step 3 — not attributable to any subset.** Bisecting the complement of the 11
occluders found **zero** contributors: no half, added to the 11, reproduced the
full-scene value. An effect invisible in every subset but present in the whole is
the signature of something that requires many Gaussians present simultaneously.

**Step 4 — the buffer.** The anyhit program keeps the 16 nearest hits per chunk
(`MAX_BUFFER_SIZE 16`, `submodules/surfel_tracer/src/optix/auxiliary.h:10`;
insertion sort at `gaussiantrace_forward.cu:120-141`), and the raygen loop then
advances `t_start += t_curr` and re-traces (`:27-28,50-58`). Critically, `t_curr` is
assigned **before** the `alpha < alpha_min` test (`:58` vs `:79`), so hits that
contribute nothing still consume buffer slots and still advance the chunk boundary.

Cumulative sweep over the Gaussians whose *bounding icosahedron* the ray enters,
ordered front-to-back:

```
jumpingjacks, Gaussian 56077, camera 103   (11 alpha-occluders, 27 icosahedron entries)
   k   tracer vis   prod(1-a)      delta
  18     0.735817    0.735819   -0.000002
  20     0.480926    0.594872   -0.113946   <== DEPARTS

jumpingjacks, Gaussian 127826, camera 80   (14 alpha-occluders, 28 icosahedron entries)
  22     0.547613    0.547613   -0.000001
  24     0.503015    0.521858   -0.018843   <== DEPARTS
```

Agreement is exact until the ray crosses enough bounding volumes to overflow the
16-slot buffer, then departs.

**The arithmetic identifies the fault exactly.** For cell 1 the boundary occluder
has α = 0.1916, and

```
1 − 0.480926 / 0.735817  =  0.3464  =  1 − (1 − 0.1916)²
```

— that occluder is accumulated **twice**. Cell 2 shows the same signature
(0.503015 / 0.521858 = 0.96389 → a doubled occluder of α = 0.0361).

**This is a defect in LumiMotion's released tracer, not in the port.** When a ray
crosses more than `MAX_BUFFER_SIZE` bounding volumes, the Gaussian at the chunk
boundary is processed in both chunks. The port faithfully calls the model's own
visibility function and inherits the behaviour.

---

## 4. Exposure — larger than the disagreement count suggests

Measured over the same 500-Gaussian × 135-camera sample, per arm:

| scene / arm | rays crossing > 16 bounding volumes | mean \|Δvis\| | cells \|Δvis\| > 1e-2 | mask disagreements |
|---|---|---|---|---|
| jj static | **19.33%** | 1.59e-05 | 0.043% | 0 |
| jj deformed | **16.78%** | 1.99e-05 | 0.044% | 2 |
| standup static | **26.77%** | 1.39e-05 | 0.033% | 0 |
| standup deformed | **24.99%** | 1.72e-05 | 0.043% | 0 |

Max bounding-volume crossings per ray: 1006 (jj), 878 (standup).

**The overflow regime is common — 17–27% of rays — not rare.** What is rare is its
effect on the *boolean* statistic: mean perturbation of `vis` is ~2e-5, and a
perturbation only flips the mask if `vis` sits within that distance of 0.5. Across
all four arms, 270,000 gated cells, it flipped **2**.

Signed mean (tracer − brute force): −6.0e-06 (jj static), −7.6e-06 (jj deformed),
+1.2e-06 (standup static), +3.5e-06 (standup deformed). Mixed in sign, ~1e-6 in
magnitude, and the **between-arm difference is ~2e-6** — the quantity that would
bias C_seq/C_rigid. For jj the deformed arm carries slightly *more* spurious
occlusion (conservative, against the hypothesis); for standup slightly less
(anti-conservative). Both are six orders of magnitude below the 0.5 threshold.

---

## 5. ⚠️ This corrects two earlier statements

**`exp1_stage1_gate.md` §3.4 is wrong as written.** It said the 16-hit buffer and
early break *"cannot change the mask."* The order-independence half of that
argument is sound (`vis = Π(1−αᵢ)`, and the `T < 0.03` break implies `vis < 0.5`
already). The buffer half is not: overflow does not merely drop hits, it can
double-count one, and that is a change the product argument does not cover. It
changed the mask twice.

**Addendum §D.2's framing needs updating.** It says gate (b)'s zero disagreements
are *"empirical evidence this does not bite here."* That was true of the evidence
available when it was written. It is now measured directly, and the accurate
statement is stronger and more specific:

> The 16-hit anyhit buffer **does** overflow, on 17–27% of rays, and **does**
> perturb `vis` — by ~2e-5 on average, up to 0.19 in the worst observed cell, via
> double-counting of the Gaussian at the chunk boundary. It almost never changes the
> **coverage mask**, because that is a threshold at 0.5: 2 flips in 270,000 gated
> cells. The mask is robust to the defect; `vis` itself is not.

Stage 3 should say that, not the weaker claim.

---

## 6. Where this leaves the experiment — for decision, not for me to settle

Stage 2 is **not** run, per the addendum.

The discrepancy is real, understood, and located in the model's own tracer rather
than in the port. That makes the next step a judgement about the measurement's
definition, which amendment 2 §0 puts under an outcome-independence audit and which
I should not make unilaterally. The options as I see them:

1. **Proceed as registered.** The port reproduces LumiMotion's own visibility
   function, defect included, which is exactly what the model-actual doctrine
   requires (`RadioGS: observability.py:11`). Record the defect as a sixth declared
   deviation alongside amendment 2 §8, with the §4 exposure table. Gate (b) is then
   reported honestly as 2 disagreements in 270,000 cells, diagnosed to a tracer
   defect, rather than as a clean pass.
2. **Proceed, and additionally dump per-ray bounding-volume crossing counts** so the
   Stage 3 write-up can report what fraction of the adjudicating population sits in
   the overflow regime, per arm and per decile. Cheap — it is the same brute-force
   geometry — but it is extra measurement, and the C_rigid/C_seq difference in
   overflow rate is the one channel by which the defect could bias P1/P2.
3. **Do not proceed** until the tracer is fixed. This means modifying a compiled
   submodule and rebuilding, which `CLAUDE.md` forbids unprompted, would make every
   number incomparable with the trained model's own behaviour, and would break the
   model-actual doctrine.

My recommendation is **(2)**: it keeps the registered definition intact, and it
closes the only channel by which the defect could reach a verdict. It adds one
array to the dump and no new analysis choice, so it does not touch any threshold.

Whichever is chosen, it should be written down before Stage 2 runs.

**Owed upstream.** This is a second real bug in the released LumiMotion code, after
the stale-BVH bug in the two dynamic eval scripts (`HANDOVER.md` §12). Both are
worth reporting to the author.
