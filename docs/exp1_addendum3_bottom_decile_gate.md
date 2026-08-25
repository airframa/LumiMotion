# Experiment 1 — addendum 3 §3: gate (b) in the adjudicating population

**Result: PROCEED, both scenes, by a margin of 50× and ∞.**
Reported, not acted on. `analyse_stage2.py` has **not** been re-run.

**Quarantine honoured (§0).** `docs/exp1_assets/exp1_adjudication.json` was not
opened. No P1, P2 or P3 quantity was computed, printed or inferred anywhere in this
work; no C_seq/C_rigid ratio was formed.

---

## 0. The quarantined file does contain verdict inputs

Determined from the source that wrote it, without opening it — the safest
available method, since reading even the key names of a JSON risks more than
reading the code that emits them.

`scripts_local/exp1/analyse_stage2.py` builds `R["predictions"]` — P1's median
ratio, P2's bottom/top ratio, P3's rate ratios, and the three pass booleans — at
`:158-190`. That dict is folded into `out` at `:216`, and `json.dump` at `:231`
executes **before** the stop branch at `:234-237`.

**So the JSON holds full verdict inputs for both scenes. It stays closed.**

⚠️ **This is a defect in my own script, and it is the direct cause of the
quarantine.** The stop path exists precisely to withhold verdicts, and it wrote
them to disk anyway. Before any re-run, `analyse_stage2.py` should emit only the
exposure/rule block when the rule trips, and the existing file should be deleted or
moved outside the repo rather than overwritten in place. Not done here — §3 says
report and stop.

---

## 1. What was run

Gate (b) unchanged: same brute force, same activations applied locally, same
rotation matrices built locally, same alpha semantics transcribed from
`gaussiantrace_forward.cu:55-105`, **same `d_g² < 1e-6` clamp rejection**. 500
Gaussians, seed 0, both arms, both scenes.

**Sample.** Bottom C_rigid decile of the **dynamic** stratum, deciles taken over the
`C_rigid > 0` subset per `exp1_stage2_plan.md` §2.

| | jumpingjacks | standup |
|---|---|---|
| dynamic ∧ C_rigid > 0 | 31,381 | 36,932 |
| bottom decile | 2,950 | 3,592 |
| decile boundary | 9.0 | 20.0 |
| **median(C_rigid \| bottom decile)** | **5.0** | **12.0** |
| C_rigid range in decile | 1 – 8 | 1 – 19 |
| sample | 500, seed 0 | 500, seed 0 |

**The C_seq arm is the diagonal**, reproduced exactly as Stage 2 computed it: frame
*j* uses the deformation at `cams[j].fid` **and** camera *j*, with `build_bvh` on
frame 0 and `update_bvh` thereafter. The earlier single-frame gate held one
deformation fixed across all 135 cameras; that is a configuration Stage 2 never
evaluated, and using it here would have measured the wrong thing.

**Verified against the Stage 2 arrays:** the gate's recomputed port `n_views`
reproduces the stored Stage 2 `n_views` for **500/500** sampled Gaussians in **both
arms, both scenes**. The gate is measuring the same run that will be adjudicated.

---

## 2. The five §3 quantities

### (1) Mask disagreement rate

| scene | arm | disagreements | cells | rate |
|---|---|---|---|---|
| jumpingjacks | rigid | **1** | 67,500 | 0.00148 % |
| jumpingjacks | seq | **0** | 67,500 | 0 |
| standup | rigid | **0** | 67,500 | 0 |
| standup | seq | **0** | 67,500 | 0 |

One disagreement in 270,000 cells, and it is in the **control** arm.

### (2) Mean per-Gaussian coverage bias, in cameras

`b_arm = mean(n_views_port − n_views_brute)`

| scene | `b_rigid` | `b_seq` |
|---|---|---|
| jumpingjacks | −0.002000 | +0.000000 |
| standup | +0.000000 | +0.000000 |

jumpingjacks' −0.002 is exactly the single disagreement: −1 camera over 500
Gaussians.

### (3) Δb — the channel by which the defect can reach P1/P2

| scene | Δb (cameras) | median(C_rigid) | **\|Δb\| / median** | bound |
|---|---|---|---|---|
| jumpingjacks | **+0.002000** | 5.0 | **0.000400** | < 0.02 |
| standup | **+0.000000** | 12.0 | **0.000000** | < 0.02 |

50× inside the bound for jumpingjacks; identically zero for standup.

The sign is also the reassuring one. §1 of the addendum flagged that negative
overflow asymmetry would *inflate* C_seq/C_rigid and push P1 toward a false pass.
Δb is **positive** in jumpingjacks (+0.002 cameras) and **zero** in standup — so the
measured bias does not run in the feared direction, and in standup there is no bias
to have a direction.

### (4) Overflow levels — **not saturated**

Crossings use the circumscribed radius and are an upper bound.

| scene | arm | overflow % (decile) | (sample) | crossings median / p90 / p99 / max |
|---|---|---|---|---|
| jumpingjacks | rigid | **41.362** | 40.671 | 2 / 95 / 226 / 465 |
| jumpingjacks | seq | **33.456** | 33.194 | 0 / 86 / 185 / 553 |
| standup | rigid | **58.769** | 56.293 | 33 / 145 / 280 / 560 |
| standup | seq | **51.273** | 48.830 | 21 / 119 / 252 / 673 |

Between-arm difference: **−7.906 pp** (jj), **−7.496 pp** (standup) — reproducing
the values that tripped the addendum 2 §B rule.

**Neither scene is saturated: no arm exceeds 90 %.** The difference clause was
therefore *not* uninformative — it was measuring a real asymmetry between two
unsaturated levels. What §3 establishes is not that the proxy misfired
mechanically, but that **the real asymmetry does not propagate into coverage.**
Exposure in the bottom decile is 33–59 %, roughly double the pooled 17–27 %,
exactly as addendum 2 §B predicted — and the resulting coverage bias is still
≤ 0.002 cameras.

The reason is visible in (5): the defect perturbs `vis`, and in the bottom decile
`vis` is overwhelmingly far from the 0.5 threshold. These Gaussians are heavily
occluded; their mask value is not close to being decided.

### (5) Fragility in the bottom decile, fraction of gated cells

| scene | arm | < 1e-3 | < 1e-2 | < 5e-2 |
|---|---|---|---|---|
| jumpingjacks | rigid | 0.0277 % | 0.2371 % | 1.1279 % |
| jumpingjacks | seq | 0.0217 % | 0.1444 % | 0.8000 % |
| standup | rigid | 0.0390 % | 0.3820 % | 1.7528 % |
| standup | seq | 0.0171 % | 0.1617 % | 0.8071 % |

Even at δ = 5e-2 — a perturbation 2,500× the mean |Δvis| Task A measured — under
1.8 % of gated cells are close enough to flip.

---

## 3. Decision

> **PROCEED**, both scenes.
>
> | scene | Δb | median(C_rigid \| bottom decile) | ratio | rule |
> |---|---|---|---|---|
> | jumpingjacks | +0.002000 | 5.0 | **0.000400** | < 0.02 → PROCEED |
> | standup | +0.000000 | 12.0 | **0.000000** | < 0.02 → PROCEED |

Under §3, the tracer defect is immaterial **by direct measurement in the
adjudicating population**, addendum 2 §B is satisfied on its own terms, and
`analyse_stage2.py` may run unchanged.

**Not acted on.** No re-run has been performed and no verdict has been produced.

---

## 4. §5 guard confirmations, for the Stage 3 write-up

From the Stage 2 logs (`/data/fmb/lumimotion/logs_exp1/stage2_*.log`), plus one
cross-check:

| guard | jumpingjacks | standup |
|---|---|---|
| BVH refits per arm | **135 / 135** (rigid / seq) | **135 / 135** |
| C_rigid displacement, dynamic set | **0.000e+00** | **0.000e+00** |
| C_rigid displacement, pooled | **0.000e+00** | **0.000e+00** |
| C_seq per-frame median ‖d_xyz‖, dynamic set | **[0.0575, 0.2847]** | **[0.0881, 0.5585]** |
| C_seq per-frame median, pooled | [1.207e-11, 1.671e-11] | [5.771e-12, 8.682e-12] |
| N / dynamic | 146,400 / 32,200 (21.99 %) | 156,893 / 37,218 (23.72 %) |
| parameters | `back_culling=False light_t_min=0.1 alpha_min=0.01 transmittance_min=0.03 thr=0.5 t_scales=(1.0, 3.0)` | same |

**Both C_seq ranges match Task 1's independently measured per-time medians
exactly** — jumpingjacks min 0.057454 / max 0.284658, standup min 0.088066 / max
0.558546 (`exp1_stage1_gate.md` §1.1). Two separate scripts, run two days apart,
agree to four decimal places. The arms are what they claim to be.

Add to this the §1 result above: the gate's independent recomputation reproduces
the stored Stage 2 `n_views` for 500/500 Gaussians in both arms and both scenes.

---

## 5. Standing record

This is the fifth gate, and per addendum 3 §4 it is terminal in either branch. It
returned PROCEED. Cost: ~35 s per scene.

The instrument findings across all five gates now stand at: the BVH-template
hazard, the `d_g²` clamp artefact, the anyhit buffer double-count, the latent
float64 `fid` assertion, the pooled displacement diagnostic that read ~0, and the
stop-path JSON leak in §0 above. None of these was visible from reading the code
alone; each needed a measurement.
