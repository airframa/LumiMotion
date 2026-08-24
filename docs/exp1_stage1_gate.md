# Experiment 1 — Stage 1: canonical-pose check and port gate

Covers Tasks 1–3. **Stage 2 has not been run.** No coverage arrays exist.

Governing document: `docs/exp1_prereg_amendment_2.md`, which supersedes §2 of
`exp1_coverage_under_deformation_brief.md`. Basis: `docs/exp1_stage0_findings.md`.

Files written: `scripts_local/exp1/canonical_pose_check.py`,
`scripts_local/exp1/coverage_seq.py`, `scripts_local/exp1/gate_coverage.py`.
Assets: `docs/exp1_assets/canonpose_*.npz`.

---

## 1. Task 1 — canonical-pose check (amendment §6)

**Verdict: the canonical set is a plausible pose in both scenes. The stop
condition does not fire.** Reading (a) — `d_xyz = d_rotation = 0` exactly — stands
as the C_rigid arm.

Command (both scenes, iteration 55000, `CUDA_VISIBLE_DEVICES=0`, ~4 s each):

```
python scripts_local/exp1/canonical_pose_check.py \
  --model_path /data/fmb/lumimotion/outputs_test1/chapelday_goldenbay/<scene>150_v5_spec32_r2_mlp \
  --source_path $PWD/data/d-nerf-relight-spec32/<scene>150_v5_spec32 \
  --deform_type mlp --iteration 55000
```

### 1.1 `‖d_xyz(t)‖` — the deformation deforms

Over all N × 135 (Gaussian, time) pairs, world units:

| | jumpingjacks | standup |
|---|---|---|
| N | 146,400 | 156,893 |
| dynamic (`binary_feature > 0.5`) | 32,200 (21.99%) | 37,218 (23.72%) |
| canonical bbox diagonal | 4.1957 | 2.9881 |
| **dynamic median** | **0.1938** (4.62% of diag) | **0.2663** (8.91% of diag) |
| dynamic p90 | 0.4233 (10.09%) | 0.5921 (19.82%) |
| dynamic p99 | 0.6316 (15.05%) | 0.8356 (27.97%) |
| dynamic max | 0.7690 | 0.9943 |
| all-Gaussian median / p90 / p99 | 0.0000 / 0.2137 / 0.5019 | 0.0000 / 0.3039 / 0.7165 |
| `‖d_rotation‖` dynamic median / p99 | 0.0869 / 0.9435 | 0.1987 / 0.8686 |

Per-time median over the dynamic set, 135 times:

| | jumpingjacks | standup |
|---|---|---|
| min | 0.0575 at t = 0.4400 (`r_0066`) | 0.0881 at t = 0.4400 (`r_0066`) |
| max | 0.2847 at t = 0.9467 (`r_0142`) | 0.5585 at t = 0.9933 (`r_0149`) |
| mean over times | 0.1727 | 0.2840 |
| max/min ratio | 4.95 | 6.34 |

`d_scaling` was asserted identically zero at every time, confirming
`utils/time_utils.py:192`.

**This satisfies brief §4's "verify the deformation deforms."** The displacement is
not marginal: the median dynamic Gaussian moves 4.6% / 8.9% of the subject's bbox
diagonal, and the p99 moves 15% / 28%.

### 1.2 ⚠️ Correction to Stage 0 — "static" Gaussians are not identically zero

Stage 0 §Q6b said 78% of Gaussians "have identically zero self-displacement."
**That was too strong, and the measurement corrects it.** The gate is
*multiplicative*, not boolean — `d_xyz = raw_d_xyz * binary_feature`
(`utils/time_utils.py:190`) — so a Gaussian at `binary_feature = 0.49` is "static"
under the 0.5 threshold and still receives 49% of the displacement.

| | jumpingjacks | standup |
|---|---|---|
| static Gaussians that move at all (max over t > 1e-6) | 1,056 / 114,200 (**0.92%**) | 1,545 / 119,675 (**1.29%**) |
| static Gaussians moving > 0.01 world units | 131 (0.11%) | 199 (0.17%) |
| max static displacement | 0.1426 | 0.3572 |
| `binary_feature` of the movers: median / max | 6.6e-04 / 0.4935 | 2.9e-04 / 0.4981 |

The leak is confined to Gaussians sitting just under the threshold, exactly as the
multiplicative gate implies. **This matters for P3**, whose static arm is the
control: the control is contaminated at the 0.1–0.2% level by Gaussians that do
move. That is small enough not to threaten a 2× rate ratio, but it is real, it is
now on the record, and the counts above should be repeated in the Stage 3 write-up
so the P3 control is auditable (amendment §2's "known weakness" clause).

### 1.3 Stop condition — not triggered

Three independent degeneracy probes, all negative:

| probe | jumpingjacks | standup | reading |
|---|---|---|---|
| deformed bbox extent / canonical, min–max over all times and axes | 0.9888 – 1.0989 | 0.9884 – 1.0751 | **not collapsed**; the canonical extent is within 1–10% of every deformed frame |
| median nearest-neighbour spacing (4096-pt subsample, seed 0), canonical vs deformed at t = 0.5 | 0.009258 vs 0.009348 (ratio 0.990) | 0.010764 vs 0.010778 (ratio 0.999) | **no pile-up**; canonical is not a squashed configuration |
| `‖x_canon − mean_t x(t)‖ / max_t ‖x(t) − mean_t x(t)‖`, dynamic set | median 0.335, p90 0.434, p99 0.652 | median 0.169, p90 0.316, p99 0.575 | **canonical sits inside the observed trajectory**, not outside it |
| fraction of dynamic Gaussians with that ratio > 1 | 0.61% | 0.12% | negligible extrapolation |
| closest observed frame to canonical | index 59, t = 0.4400, median displacement 0.0575 = **1.37% of bbox diagonal** | index 59, t = 0.4400, median displacement 0.0881 = **2.95% of bbox diagonal** | canonical is close to a pose the sequence actually contains |

The third probe is the one that addresses the amendment's actual concern — "a
static capture of a configuration the sequence never contains is not a meaningful
baseline." It is not such a configuration: in both scenes the canonical set lies
well inside the convex extent of the observed trajectory and is within 1.4% / 2.9%
of the bbox diagonal of frame 59 (t = 0.44). Both scenes independently landing on
the same closest frame is a coincidence worth noting but not acting on.

The `max` column of the offset ratio (20.68 / 8.05) is driven by Gaussians whose
own trajectory radius is near zero — the denominator, not the numerator. It is the
expected small-denominator artefact (`HANDOVER.md` §9.4) and is why the median and
p90 are quoted.

---

## 2. Task 2 — `scripts_local/exp1/coverage_seq.py`

Written, not run. Parameters are asserted at runtime against the amendment rather
than merely set, so a silent drift fails loudly:

| parameter | value | asserted against |
|---|---|---|
| `back_culling` | False | module constant; no caller in LumiMotion ever passes it |
| `light_t_min` | 0.1 | `assert abs(pipe.light_t_min - 0.1) < 1e-12` |
| `alpha_min` | 1/100 | `assert abs(g.alpha_min - 1/100) < 1e-12` |
| `transmittance_min` | 0.03 | `assert ... - 0.03 < 1e-12` — implied by the above, declared because it bounds the trace |
| `thr` | 0.5 | module constant |
| `t_scale` | 1.0 and 3.0, both arms | module constant |

**BVH.** Build on the first frame, `update_bvh` on every frame thereafter, per
`scripts/train_stage2.py:155-159`. Applied uniformly in *both* arms, including
C_rigid where the geometry does not change — one code path, no branch that could
diverge between arms. Nothing was copied from `scripts/eval_nvs_dynamic.py` or
`scripts/eval_relight_dynamic.py`.

**The guard** (`BVHGuard`) records a clone of `(d_xyz, d_rotation, d_scaling)` at
each build/update and asserts `torch.equal` against the tuple used to build the
geometry passed to `trace()` on that frame. It checks the invariant that matters —
*the acceleration structure was refit to the geometry being traced* — rather than
the call pattern, so it does not fire falsely in the C_rigid arm (amendment §7).
A second assertion checks the refit count equals the frame count per arm.

**Other guards, all failing loudly rather than silently:**

- `source_path` is rejected if it resolves into the sibling worktree.
- `dataset.eval is True` is asserted — with `eval=False` the released eval scripts
  take, `dataset_readers.py:229-231` appends the 15 test cameras into the train
  list, giving 150 rather than the registered 135.
- Camera `fid` order is asserted equal to `transforms_train.json` order, and the
  `dataset_readers.py:164` re-sort is asserted to be a no-op on these assets.
- Post-run: `C_rigid` displacement is asserted exactly 0 and `C_seq` displacement
  strictly > 0 (brief §4).

**Output.** Raw per-camera boolean masks `(N, 135)`, packbits-packed, for both arms
× both `t_scale` arms, plus `n_views`, `vis_sum`, `infr_sum`, `face_sum`, the
canonical geometry, `binary_feature`, and a JSON record of every parameter.
**Nothing is aggregated** (brief §6): deciles, ratios and rescue rates are all
derivable from the dumped masks. C_single is not a separate arm — it is
`ok_seq[:, j]` for any single frame `j`.

### 2.1 Two repo-specific footguns found while writing it

- **`-m` / `-s` do not exist in this repo.** The shorthand block is commented out
  at `arguments/__init__.py:31-36`. The flags are `--model_path` / `--source_path`.
  Amendment §7 says "pass `-s` explicitly"; the long form is what that means here.
- **`ModelParams(parser)` without `sentinel=True` makes every argparse default
  silently override `cfg_args`**, because `get_combined_args:181-183` copies any
  non-`None` command-line value over the config. Every released eval script does
  this, which is why `bash_scripts/synthetic_results_from_paper.sh:138-142` must
  re-pass `--eval --is_blender --resolution`. This is the LumiMotion analogue of
  the RadioGS footgun documented at `observability.py:283-288`. Both new scripts
  use `sentinel=True` and print the resolved config.

---

## 3. Task 3 — the gate

### 3.1 Gate (c): unavailable

Stage 0 Q7 established the coverage path depends on the compiled OptiX submodule in
**both** repos (`raytracer.py:71,84,104`), so the port cannot be run against
`observability.py`'s own output on a groove rung. Gates (a) and (b) apply.

### 3.2 Gate (a) — definitional fidelity, line by line

Reference: `RadioGS: scripts_local/phase3b/observability.py:124-169`, branch
`audit-notes`, HEAD `ff1d1c5`. Port: `scripts_local/exp1/coverage_seq.py`,
`coverage_frame()` and `run_arm()`.

| `observability.py` | ported line | identical? |
|---|---|---|
| `:136-138` `v = cam.camera_center - mu; d = v / dist.clamp_min(1e-8)` | same, verbatim | ✅ |
| `:141-142` `h = cat([mu, ones]); clip = h @ cam.full_proj_transform` | same, verbatim | ✅ |
| `:143-144` `w = clip[:,3:4].clamp_min(1e-8); ndc = clip[:,:3] / w` | same, verbatim | ✅ |
| `:145` `infr = (clip[:,3] > 0) & (ndc[:,0].abs() < 1) & (ndc[:,1].abs() < 1)` | same, verbatim | ✅ |
| `:130` `nrm = normalize(splat2world[:,2,:3])` | same expression | ✅ (see D2) |
| `:149` `face = (nrm * d).sum(-1) > 0` | same, verbatim | ✅ |
| `:152` `out = g.trace(mu + t_scale*light_t_min*d, d, back_culling=...)` | same, **plus** the explicit `xyz/scales/rotation/opacity` LumiMotion's signature requires | ✅ (see D3) |
| `:153` `vis = 1.0 - out["alpha"]` | same, verbatim | ✅ |
| `:160` `ok = (vis > thr) & infr & face` | same, verbatim | ✅ |
| `:161` `n = ok.sum(1)` | same; stored as `int32` rather than `float` | ✅ |
| `:320-322` second arm at `t_scale = 3.0` | reproduced | ✅ |

Three structural differences, none of them a change to the statistic:

- **D1. `mu` and `splat2world` move inside the camera loop.** RadioGS computes them
  once at `:127,129` because its model is static. The port recomputes them per
  frame because the geometry deforms. In the C_rigid arm this reduces exactly to
  the RadioGS form.
- **D2. `get_covariance` is called with arguments.** RadioGS's signature takes
  none; LumiMotion's is `get_covariance(scaling_modifier, xyz, scales, rotation)`
  (`scene/gaussian_model.py:202-203`), so the deformed values are passed. The
  expression extracting the normal is unchanged. This matches what `trace()` itself
  does internally at `gaussian_model.py:654-655`.
- **D3. `trace()` requires geometry explicitly.** LumiMotion's `trace()`
  (`gaussian_model.py:634-637`) takes `xyz/scales/rotation/opacity` as arguments
  with no defaults; RadioGS's reads them from the model. The port passes the
  deformed values assembled exactly as `render_ir.py:79,96-97` assembles them.
  `camera_center` is deliberately **not** passed, so `flip_align_view` does not run
  and the normal sign is the raw surfel orientation — matching `observability.py`,
  which also omits it.

### 3.3 The three declared deviations (amendment §8), stated not glossed

**§8.2 — per-Gaussian vs per-pixel visibility. This is the substantive one.**
RadioGS's own visibility function is per-Gaussian: `precompute_incidents` traces
from `position = self.get_xyz` (`RadioGS: radiogs_gaussian_model.py:846-848`), so
`observability.py` could claim to measure "the coverage the model actually had"
literally. **LumiMotion's is per-pixel.** `rendering_equation` receives
`points[mask]`, and `points` is a depth-reprojected surface buffer
(`gaussian_renderer/render_ir.py:217`), used as the ray origin at `:503-505`. The
port traces from deformed Gaussian *centres*. That is the correct analogue of the
RadioGS construction and the only thing that yields an array indexed by canonical
Gaussian identity — but it is **not** what LumiMotion's own renderer does, and
the "model-actual" claim is therefore weaker here than it was for RadioGS. Any
Stage 3 sentence asserting this measures LumiMotion's own visibility must carry
this qualification.

**§8.3 — different culling regime.** §5.2's coverage was computed at
`back_culling=True`; this runs at `False`, because no LumiMotion caller ever passes
the flag (`gaussian_model.py:636` default; `render_ir.py:503-505` omits it). Stage 0
argued from a source diff that the two vendored tracers accumulate `alpha`
identically and that the kernel differences touch only the returned normal and
colour. **That argument was asserted from source, not measured, and it remains so** —
gate (b) below tests the port against a brute force, not RadioGS against LumiMotion.

**§8.5 — `.so` provenance.** The installed `surfel_tracer` binary was built
2026-08-07, predating both worktree checkouts. The tracer source is branch-invariant
(the only file differing between the two branches under `submodules/` is
`simple-knn/simple_knn.egg-info/PKG-INFO`), which bounds the risk without
eliminating it. Unchanged from Stage 0.

§8.1 (different subjects/method/codebase) and §8.4 (frontal cap) are unchanged and
carry into Stage 3 as stated.

### 3.4 Gate (b) — numeric cross-check

**Declared before running:** 500 Gaussians, seed 0, all 135 cameras = 67,500 rays ×
N Gaussians = 9.88e9 (jj) / 1.06e10 (standup) pair evaluations; ~2.4 GB peak at
chunk 512; estimated 1–3 min on one 4090. That was feasible, so **the sample stayed
at 500** — no reduction was needed.

Run on the **static** configuration (canonical geometry, no deformation), per brief
§5(b). `gate_coverage.py` shares no helper with the port: it reads the PLY with
`plyfile`, applies `sigmoid`/`exp`/`normalize` itself, builds rotation matrices from
quaternions itself, derives the surfel normal as the third column of R, and
transcribes the alpha semantics from
`submodules/surfel_tracer/src/optix/gaussiantrace_forward.cu:55-105`.

> ⚠️ **Corrected 2026-08-24 by Task A** (`docs/exp1_taskA_deformed_gate.md` §5).
> Fact 1 below is sound on order-independence but its conclusion that the 16-hit
> buffer *"cannot change the mask"* is **wrong**. Overflow does not merely drop
> hits — it can double-count the Gaussian at the chunk boundary. That changed the
> mask on 2 of 270,000 gated cells and perturbs `vis` on 17–27% of rays. See the
> Task A document for the measurement.

**Two facts derived from the kernel that make brute force tractable and valid:**

1. `O += T*alpha` with `T *= (1-alpha)` gives `O = 1 − Π(1−αᵢ)` **exactly**, so
   `vis = Π(1−αᵢ)` — a product, hence order-independent. The kernel's 16-hit sorted
   buffer (`auxiliary.h:10`, anyhit at `gaussiantrace_forward.cu:120-141`) and its
   early break therefore cannot change the mask: the break fires only once
   `T < 0.03`, which already implies `vis < 0.5`. Ordering was checked and then
   shown not to matter, rather than assumed away.
2. `alpha ≥ alpha_min` is exactly `|p_g| ≤ sqrt(2 ln(o/alpha_min))`, which is
   exactly the inscribed sphere of the BVH icosahedron (`gaussian_model.py:99,618`).
   Tangentially, the bound can only add hits the alpha test then rejects.

#### First run — one disagreement, diagnosed not tolerated

| scene | mask cells | disagreements |
|---|---|---|
| jumpingjacks | 67,500 | **0** |
| standup | 67,500 | **1** |

The standup cell: sampled Gaussian **5253**, camera **15**. Ported `vis = 1.000000`
exactly; brute force `vis = 0.456819`, from a single claimed occluder, Gaussian
**49250** at `dist = 0.702`, `alpha = 0.543`.

`vis = 1.0` exactly is the signature of `intersection_test` returning `False`
(`raytracer.py:103-114`) — the ray hit nothing in the BVH at all. Direct
measurement of the geometry:

```
dot(n_49250, ray_d) = 0.000011    ->  ray is 0.001 deg from PARALLEL to the surfel plane
occluder disc  : support radius 3.0347 sigma, world extent 0.0590 x 0.0681
BVH slab       : normal half-thickness 3.03e-06   (third scale is a literal 1e-6,
                                                   gaussian_model.py:615)
```

**The cause is the kernel's own guard.** Line 76 computes
`d = -o_g * d_g / max(1e-6, d_g*d_g)`. With `d_g = 1.1e-5`, `d_g² = 1.2e-10`, so the
denominator is **replaced by the constant** and `d = -o_g × 1.1e-5 / 1e-6 = 0.70` —
an arbitrary finite point manufactured by the clamp, not a plane intersection
(a ray parallel to a plane has none). That fabricated point happens to land inside
the disc and yields a large spurious `alpha`. The BVH correctly declines the hit,
because a ray parallel to a 3e-6-thick slab does not intersect it.

Confirmed by perturbation, which discriminates "grazing degeneracy" from "the brute
force invented an occluder": the tracer returns `alpha = 0` for the unperturbed ray,
for `t_scale = 3.0`, for ray-origin offsets of ±1e-5 … ±1e-2 along the occluder
normal, and for angular perturbations of 1e-6 … 1e-2 rad — and returns
`alpha = 1.000000` once the ray is rotated 1e-1 rad off-parallel. The occluding
geometry is real; a parallel ray simply does not intersect it.

#### The correction, and why it is not a tolerance

My "no ray-icosahedron test is needed" argument covers the two tangent directions.
It does **not** cover the normal direction, because the bound is a 3e-6-thick slab.
For near-parallel rays the bounding volume is load-bearing — it is the only thing
suppressing the clamp artefact.

The brute force therefore now rejects hits where **the kernel's own clamp is
active**: `d_g² < 1e-6`, the literal constant from `gaussiantrace_forward.cu:76`. In
that regime the kernel's `d` is definitionally not a plane-intersection distance.

This is a source-derived condition, not a fitted threshold. Three checks that it is
surgical rather than a fudge:

- It is the kernel's own constant, taken from the line whose output it invalidates.
- **jumpingjacks had 0 disagreements both before and after the correction** — the
  healthy case is untouched.
- It rejects **6 of 9.88e9** pairs in jumpingjacks (6.1e-08%) and **65 of 1.06e10**
  in standup (6.1e-07%). Of those 65, exactly one was flipping a mask cell.

#### Final result

```
GATE (b) -- exact agreement on the boolean coverage mask
  jumpingjacks : 67500 cells, 0 disagreements, per-Gaussian n_views identical 500/500
  standup      : 67500 cells, 0 disagreements, per-Gaussian n_views identical 500/500
  RESULT: PASS -- exact agreement, no tolerance applied
```

Mean `n_views` over the sample agreed to all printed digits in both scenes
(97.7520 / 75.0300).

**Gate (a) PASS, gate (b) PASS on two scenes rather than the one required.
Gate (c) unavailable.**

### 3.5 What the gate does not establish

- It tests the port against an independent implementation of **the same semantics**.
  It cannot detect an error shared by both — in particular, both take the surfel
  normal as the third column of R and both use Gaussian centres as ray origins
  (deviation §8.2).
- It was run on the static configuration only. The BVH-staleness hazard lives in the
  *deformed* path and is covered by `BVHGuard`, not by this gate.
- 500 Gaussians is 0.34% (jj) / 0.32% (standup) of the population.

---

## 4. Incidental observation, explicitly not a result

The gate prints mean `n_views` over its 500-Gaussian sample in the **canonical**
configuration, which is the C_rigid arm: **97.75 (median 121) for jumpingjacks,
75.03 (median 76) for standup**, out of 135 cameras.

Recorded because it was printed, and because it says the C_rigid baseline is not
starved. **It is not a Stage 2 result**: it is a 0.3% sample, it is pooled across
the dynamic/static strata that amendment §1 separates, and no decile structure has
been computed. P1, P2 and P3 are adjudicated in Stage 2 on the full arrays against
the thresholds fixed in amendment §4, and nothing here licenses revisiting them.

---

## 5. Status

Tasks 0–3 complete. **Stage 2 not run.** `coverage_seq.py` is written, gated and
ready; the command is in its header. Awaiting review of §1 and §3 before the
measurement.
