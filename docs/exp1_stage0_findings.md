# Experiment 1 — Stage 0 findings (read-only)

Answers to `exp1_coverage_under_deformation_brief.md` §3, Q1–Q7. No code written,
no files in the LumiMotion tree modified, no compute, no rendering, no training.

Citations are `file:line`. Paths without a repo prefix are in this worktree
(`/home/fmb/projects/LumiMotion-observability`). Paths prefixed `RadioGS:` are in
`~/projects/RadioGS-public`, branch `audit-notes` (confirmed checked out, HEAD
`ff1d1c5`).

**Two findings change the design and are flagged for decision before Stage 1:**
§Q3 (camera layout is a 98° frontal cap, not an orbit) and §Q6b (78% of Gaussians
have identically zero deformation). Both are in §8.

---

## Q1. What exactly is `observability.py`'s coverage statistic?

**It is an integer count of cameras.** Confirmed — §5.2's medians of 33.0 vs 21.8
are camera counts, not weights.

The statistic is `n`, computed in two steps.

*Per-camera masks* — `RadioGS: scripts_local/phase3b/observability.py:124-154`:

| line | quantity |
|---|---|
| `:136-138` | `d` = unit direction from Gaussian centre `mu` to `cam.camera_center` |
| `:141-145` | `infr` — in-frustum: world→clip via `full_proj_transform`, then `clip[:,3] > 0 & |ndc.x| < 1 & |ndc.y| < 1` |
| `:149` | `face` — front-facing: `(nrm · d) > 0`, where `nrm` is the surfel normal `normalize(splat2world[:,2,:3])` (`:130`) |
| `:152` | `out = g.trace(mu + t_scale * light_t_min * d, d, back_culling=...)` |
| `:153` | `vis[:,j] = 1.0 - out["alpha"]` |

*Reduction to the statistic* — `RadioGS: observability.py:157-169`:

```python
160    ok = (vis > thr) & infr & face        # thr = 0.5, (N,C) boolean
161    n  = ok.sum(1).float()                # <- THE COVERAGE STATISTIC
```

`n` is saved as `n_views` (`:377`) and is the field the analysis treats as
coverage throughout — `RadioGS: obs_analysis.py:94,114,134,150,173`. The console
line `:388` prints it as `"coverage: median {...} views"`.

So: **coverage(i) = the number of cameras c for which Gaussian i is simultaneously
(a) inside the frustum, (b) front-facing, and (c) unoccluded to better than 50%,
where occlusion is the model's own `1 - alpha` visibility.** Not alpha-weighted,
not depth-weighted; the alpha enters only through the `> 0.5` threshold.

Two ancillary points that matter for a faithful port:

- `thr=0.5` is a default argument (`:157`), never overridden.
- A second arm `n2` (`n_views_t3`) is computed with `t_scale=3.0`
  (`:320-322`) as a self-hit robustness check, because the 2σ bounding radius can
  exceed `light_t_min`. The port should reproduce both arms.

**Visibility is the model's own function, not a reimplementation.** RadioGS
defines it at `RadioGS: scene/radiogs_gaussian_model.py:848-850`
(`precompute_incidents`): `incident_visibility = 1 - trace_alpha`. `coverage()`
replicates that call, aimed at cameras instead of hemisphere samples — stated in
the file header, `RadioGS: observability.py:7-11`.

---

## Q2. Does that path use the rasterizer or the tracer? Does it inherit the stale BVH?

### It uses the tracer, and the coverage path is **entirely BVH-dependent**.

`observability.py:152` calls `g.trace(...)`, which reaches
`GaussianTracer.trace` (`submodules/surfel_tracer/surfel_tracer/raytracer.py:84`).
The BVH is load-bearing at two points there:

```
raytracer.py:104   self.impl.intersection_test(rays_o, rays_d, ...) -> mask
raytracer.py:111-114  only rays with mask=True are traced; the rest keep alpha = 0
```

`self.impl` is the OptiX acceleration structure. `intersection_test` gates which
rays enter the trace at all. **A ray that misses the BVH returns `alpha = 0`
exactly, i.e. `vis = 1.0`, i.e. reported as perfectly visible.**

The BVH's geometry is the deformed bounding icosahedra, built from the deformation
arguments — `scene/gaussian_model.py:610-632`:

```
:617   L = build_scaling_rotation(scale + d_scaling, self._rotation + d_rotation)
:618   vertices_b = (2*(opacity/alpha_min).log()).sqrt() * (icosa @ L.T) + (get_xyz + d_xyz)
:624-627   build_bvh(...)  -> gaussian_tracer.build_bvh
:629-632   update_bvh(...) -> gaussian_tracer.update_bvh
```

So the BVH encodes a *specific pose*. Nothing else in `trace()` can compensate:
`trace()` takes the deformed `xyz/scales/rotation/opacity` as explicit arguments
(`gaussian_model.py:634-637`), so with a stale BVH the traversal runs against
frame-0 bounding volumes while the shading evaluates frame-*t* surfels — an
inconsistency that silently biases `alpha` toward zero (missed occluders).

**This is exactly the fake-null mechanism §4 of the brief warns about.** A stale
frame-0 BVH makes visibility frame-0's visibility regardless of the deformed
geometry passed in, which drives C_seq → C_rigid and reads as a clean
falsification of P1 and P2.

### Tracing the call sites, rather than concluding from the mechanism

Per `HANDOVER.md` §9.15, I traced every `build_bvh`/`update_bvh` call site in the
tree rather than inferring from the pattern.

**Defective — build once, never update (dynamic):**

| file:line | |
|---|---|
| `scripts/eval_nvs_dynamic.py:69,86-88` | `build_bvh = True`; build at `:87`; `build_bvh = False` at `:88`; no `update_bvh` anywhere in the file |
| `scripts/eval_relight_dynamic.py:80,97-99` | same pattern |

Both are confirmed exactly as `CLAUDE.md` records them (line numbers correct; see
§9 for the missing `scripts/` prefix).

**Same pattern, but on static datasets — not a bug in context:**
`scripts/eval_nvs_static.py:81,98-100` and `scripts/eval_relight_static.py:91,108-110`.
Flagged only so they are not mistaken for additional instances of the defect.

**Correct — build once, update per frame:**

| file:line | |
|---|---|
| `scripts/train_stage2.py:155-159` | verified verbatim; `if not self.built_bvh: build_bvh(...)` / `else: update_bvh(...)` |
| `utils/train_report_utils.py:295` | `update_bvh` |
| `scripts/render_relight_with_hdr.py:120,123` | build then update |
| `scripts/render_relight_with_rotating_envmap.py:103,106` | build then update |

**Our own prior instrumentation is already correct** — all four existing
`scripts_local/` scripts build on the first frame and `update_bvh` thereafter:
`scripts_local/dump_lind.py:105,108`, `scripts_local/render_trajectory.py:143,146`,
`scripts_local/measure_indirect_fraction.py:134,137`,
`scripts_local/probe_c_transport_residual.py:239,242`.
`probe_c_transport_residual.py:22-25` documents the reason, including that
`update_bvh` asserts the triangle topology was already set by a prior `build_bvh`
(`raytracer.py:79-82`).

### Consequence for Stage 1

The port must **not** copy from either dynamic eval script. The correct template
is `scripts/train_stage2.py:155-159`, and four working precedents already exist in
`scripts_local/`. Because `coverage_seq.py` is a new file (brief §5), it inherits
nothing automatically — the hazard is confined to copy-paste, and the mitigation is
to use the `scripts_local/` pattern.

**A runtime guard is cheap and should be in the port:**
`raytracer.py:80` already asserts `faces_b` is unchanged across `update_bvh`, so
topology drift cannot pass silently. What is *not* guarded is forgetting to call
`update_bvh` at all. The C_rigid arm is a legitimate exception — geometry genuinely
does not change there, so building once is correct — which means an unconditional
"must update every frame" assertion would fire falsely. The guard should instead
assert that the BVH-build arguments match the geometry handed to `trace()` on that
frame, in both arms.

---

## Q3. Camera layout for `jumpingjacks` / `standup` ⚠️ **design-relevant**

### It is one camera per timestep. There is no multi-view rig.

Measured directly from
`data/d-nerf-relight-spec32/{jumpingjacks,standup}150_v5_spec32/transforms_{train,test}.json`:

| | jumpingjacks | standup |
|---|---|---|
| train frames | 135 | 135 |
| distinct times (train) | **135** | **135** |
| distinct camera centres (train) | **135** | **135** |
| cameras per distinct time | **1** | **1** |
| test frames / times / centres | 15 / 15 / 15 | 15 / 15 / 15 |
| `cameras.json` in trained model | 150 (= 135 + 15) | 150 |
| time range (train) | 0.006667 – 0.993333 | same |
| camera radius | 5.003 ± 0.100 | 3.853 ± 0.117 |

`fid` is read straight from the JSON `time` field
(`scene/dataset_readers.py:170-173`) into `Camera.fid` (`scene/cameras.py:46`).
Camera order is the JSON order — **shuffling is commented out**
(`scene/__init__.py:75-77`), so frame index *j* maps deterministically to
`frames[j]`, and the three arms can be index-matched exactly.

### But C_rigid is **not** degenerate — the 135 viewpoints are genuinely distinct

The brief's concern was that one-camera-per-timestep might collapse the baseline.
It does not. The 135 camera centres are 135 *different* points, so C_rigid over all
135 frames with deformation pinned is a real 135-view static multi-view capture.

- Median pairwise angular separation between viewpoints: **40.3° (jj) / 57.8° (standup)**
- Median nearest-neighbour separation: **3.69° / 5.17°**
- Consecutive frames are *not* a smooth trajectory — median consecutive separation
  is 40.1° / 58.0°, i.e. the ordering is effectively random, not a spiral.

`C_rigid ≈ C_single` therefore cannot occur: C_single uses one camera, so
C_single ∈ {0,1} per Gaussian, while C_rigid ranges over 0–135.

**The §2 falsifier "C_rigid ≈ C_single" is consequently inert.** It cannot fire.
It should be replaced in the write-up by the statistic that actually establishes
non-degeneracy — the distinct-viewpoint count and the angular spread above — rather
than reported as a test that passed. (`HANDOVER.md` §9.13: a validity gate is
defined by its statistic.)

### ⚠️ The real problem is different: the cameras are a **frontal cap**, not an orbit

| | jumpingjacks | standup |
|---|---|---|
| azimuth span | **98.3°** (−48.4° to +49.9°, contiguous) | **134.8°** (−66.5° to +68.4°) |
| elevation span | 104.0° (−52.1° to +51.9°) | 136.8° (−69.5° to +67.3°) |
| max pairwise separation | 110.2° | 145.3° |
| mean-direction concentration `‖mean(û)‖` | **0.837** | **0.672** |

All 135 cameras lie inside a cone of half-angle ≈ 55° (jj) / ≈ 72° (standup) about
a single mean direction, and every camera aims within 7.0° of the origin. The
azimuths are contiguous over that wedge — I printed all 135 sorted values to rule
out wrap-around.

**Implication.** The subject's back is never observed by any camera, in either arm.
That population has C_rigid = 0 *and* C_seq = 0 (neither subject turns around), so
it enters the bottom C_rigid decile as a hard structural zero and contributes a
ratio of 0/0 rather than a concavity-interior gain. The bottom decile — which P1
and P2 are both defined on — is therefore contaminated by a population about which
the hypothesis makes no claim, and the contamination pushes both statistics
*toward the null*.

This is not a reason to abandon the design, but the handling of C_rigid = 0 stops
being a footnote and becomes a pre-registration item. See §8.

---

## Q4. How is the deformation field evaluated, and what is the API for arbitrary *t*?

### API

`DeformModel.step(xyz, time_emb, iteration=0, **kwargs)`
(`scene/deform_model.py:24-25`) forwards to `DeformNetwork.forward(x, t, **kwargs)`
(`utils/time_utils.py:172-207`). The canonical call, from
`scripts/train_stage2.py:144,148-150`:

```python
144   time_input = fid.unsqueeze(0).expand(N, -1)      # (N,1), fid = camera time scalar
148   d_values = self.deform.step(self.gaussians.get_xyz.detach(), time_input,
149                               iteration=self.iteration,
150                               feature=self.gaussians.get_binary_feature(),
                                  camera_center=viewpoint_cam.camera_center)
```

**Evaluating at an arbitrary *t* is exactly this call with `time_input` filled
with the desired scalar.** There is no other time pathway. `fid` is a plain float
in [0,1] read from the JSON (`scene/dataset_readers.py:170-173`), so any value in
that range is addressable.

### Three properties that make the C_rigid arm clean

1. **The field is camera-independent.** `forward` reads only `kwargs["feature"]`
   (`utils/time_utils.py:174`). `camera_center` is passed by every caller and
   **never used**. Likewise `iteration` is accepted and ignored, and
   `DeformNetwork.update` is a no-op (`utils/time_utils.py:209-210`). So pinning
   *t* cannot be confounded by which camera the frame belongs to, and evaluation
   is deterministic.

2. **`d_scaling` is identically zero** — `utils/time_utils.py:192`:
   `'d_scaling': scaling*0`. The network head `gaussian_scaling` exists
   (`:126`) but its output is discarded. Only position and rotation deform.

3. **`d_xyz` and `d_rotation` are gated by the binary feature** —
   `utils/time_utils.py:190-191`: `d_xyz * binary_features`,
   `d_rotation * binary_features`. See Q6.

### Deformed geometry, as the renderer assembles it

`gaussian_renderer/render_ir.py:79,96-97` — `means3D = pc.get_xyz + d_xyz`,
`scales = pc.get_scaling + d_scaling`, `rotations = pc.get_rotation_bias(d_rotation)`
— then handed to the tracer at `:287-288` → `:503-505`.

I checked one consistency risk and it is **not** a problem: `get_boundings` uses
`build_scaling_rotation(scale, self._rotation + d_rotation)`
(`gaussian_model.py:617`) while the render path uses
`get_rotation_bias(d_rotation) = rotation_activation(self._rotation + d_rotation)`
(`gaussian_model.py:151-153`). These agree, because `build_rotation` normalises
internally (`utils/general_utils.py:146-148`). The BVH bounds and the traced
surfels use the same rotation.

### ⚠️ Unresolved: what "pinned to canonical" means operationally

The brief §2 says C_rigid is "the deformation field evaluated at the canonical pose
for every frame". Two readings, and they are different measurements:

- **(a) `d_xyz = d_rotation = 0` exactly** — the true canonical Gaussian set. This
  is what "canonical pose" means structurally, and it makes the C_rigid arm exactly
  reproducible with no MLP evaluation.
- **(b) the field evaluated at a fixed `t₀`** (e.g. frame 0's time) for all frames
  — a static capture of a pose the sequence actually contains.

They coincide only if `d_xyz(t₀) ≈ 0`, which is an empirical question: the warp
head is initialised near zero (`utils/time_utils.py:133,136`) but is trained, and
nothing constrains the canonical set to equal any observed pose. **I could not
determine which pose the canonical set corresponds to without running the MLP,
which is compute and therefore outside Stage 0.** Measuring
`‖d_xyz(t)‖` across the 135 train times is the natural first action of Stage 1 and
it doubles as the §4 "verify the deformation deforms" check.

Recommendation, for decision: **(a)**. It is the honest static baseline, it needs
no MLP call in the control arm, and it makes the two arms differ in exactly one
thing. But it must be chosen and written down before the numbers exist.

---

## Q5. Is the canonical Gaussian index stable across frames?

**Yes, and it is enforced at runtime rather than merely assumed.**

1. **Nothing changes N at evaluation time.** `scripts/train_stage2.py` contains no
   densification, pruning, or `add_densification_stats` call — grep over the file
   returns nothing. The densify/prune/split machinery exists
   (`scene/gaussian_model.py:506-602`) but is stage-1 only. Loading a checkpoint
   with a fixed `load_iteration` therefore fixes `_xyz` in both count and order.

2. **The deformation is row-aligned by construction.** `deform.step` takes
   `get_xyz` as input and returns `d_xyz` of the same shape
   (`utils/time_utils.py:186,190`); row *i* in equals row *i* out.

3. **The BVH primitive → Gaussian mapping is `arange`, per frame** —
   `scene/gaussian_model.py:619`:
   `faces_b = icosahedron_faces + arange(N)[:,None,None] * 12`, and
   `gs_id = arange(N)[:,None].expand(...)`. Twelve triangles per Gaussian, index
   *i* always at offset `12i`.

4. **It is asserted at runtime.** `raytracer.py:80`:
   `assert (self.faces_b == faces_b).all(), "Update bvh must keep the triangle id not change~"`.
   Any topology change between `build_bvh` and `update_bvh` raises rather than
   silently remapping.

5. **Camera order is stable too** — `scene/__init__.py:75-77`, shuffling commented
   out (see Q3).

Model sizes, from the PLY headers at `iteration_55000`:
**jumpingjacks N = 146,400; standup N = 156,893.**

---

## Q6. What does `get_binary_feature()` return, and is it the right split?

### (a) What it returns

`scene/gaussian_model.py:179-197`. With `T` hardcoded to 0.5 (`:183`) and
`eval=True` setting `u = 0.5` (`:193`), the Gumbel noise term
`log(u) − log(1−u)` vanishes and the function reduces to:

```
binary_feature = sigmoid(2 * self.feature)      # deterministic at eval
```

Shape is `(N, fea_dim)`. `fea_dim = 1` for both trained models — the PLY carries a
single `fea_0` column, and `cfg_args` records `hyper_dim=1`. So it is one scalar
per Gaussian in **(0,1)** — despite the name it is a *soft* gate, and
`no_binary_separation=False` in both models' `cfg_args`, so the sigmoid branch is
the live one (the `:185-188` all-ones shortcut does not apply).

### (b) ⚠️ In practice it is almost perfectly binary — and 78% of Gaussians never move

Read directly from the `fea_0` column of
`point_cloud/iteration_55000/point_cloud.ply` (file read only, no compute):

| | jumpingjacks | standup |
|---|---|---|
| N | 146,400 | 156,893 |
| dynamic at `> 0.5` | **32,200 (22.0%)** | **37,218 (23.7%)** |
| dynamic at `> 0.01` | 32,422 (22.2%) | 37,484 (23.9%) |
| dynamic at `> 0.99` | 32,021 (21.9%) | 37,019 (23.6%) |
| ambiguous, in [0.1, 0.9] | **0.10%** | **0.12%** |

The threshold is immaterial — moving it from 0.01 to 0.99 changes the selected set
by 0.3%. **This is the right split to use**, and it confirms `CLAUDE.md`'s
preference for it over the `dynamic_mask` PNG: it is a learned per-Gaussian
quantity, it is unambiguous, and it is unaffected by the RGB-vs-alpha channel bug.

**But note what it implies for the experiment.** Because
`d_xyz = raw_d_xyz * binary_feature` (`utils/time_utils.py:190`), the ~78% of
Gaussians with `binary_feature ≈ 0` have **identically zero displacement at every
t**. For those Gaussians C_seq can differ from C_rigid only through the motion of
*other* Gaussians occluding them. This is a real effect and part of the
hypothesis, but it is a much weaker one than self-motion, and it applies to the
large majority of the population. See §8.

### (c) Where `_albedo_dc_stage1` lives, while I was here

Asked for by `CLAUDE.md`'s `[verify]` marker. Parameter created at
`scene/gaussian_model.py:411`; PLY property declared `:294`, written `:319-323`,
read back `:374-381`; optimiser group `:268`; **consumed at
`gaussian_renderer/render_ir.py:149`**. Confirms the "transport content is frozen"
footgun: it is a per-Gaussian SH bank with no time argument.

---

## Q7. Does the coverage computation depend on compiled CUDA submodules?

**Yes. It is not pure PyTorch/NumPy, in either repo. Gate (c) of brief §5 is
therefore unavailable.**

The chain is `coverage()` → `g.trace()` → `GaussianTracer.trace`
(`raytracer.py:84`) → `self.impl` = `_C.create_gaussiantracer()`
(`raytracer.py:71`), an **OptiX** extension. Both repos vendor a `surfel_tracer`
submodule, and both `trace` and the BVH traversal live inside it. There is no
CPU or pure-PyTorch fallback path for occlusion.

This resolves brief §5(c) negatively: the coverage statistic cannot be run "directly
on one groove rung" from a pure-Python port. Gates **(a) definitional fidelity** and
**(b) numeric cross-check** remain. A caution on (b): a brute-force independent
implementation is O(N × C × N) ray-surfel tests — 146,400 × 135 × 146,400 — which is
not feasible over the full set. It will need to run on a random subsample of
Gaussians, with the subsample size stated in advance.

### The good news: the alpha semantics are identical across the two repos

I diffed the two vendored tracers. `raytracer.py` is **byte-identical**. The OptiX
forward kernel differs in exactly two hunks
(`submodules/surfel_tracer/src/optix/gaussiantrace_forward.cu` vs the RadioGS copy),
and **neither touches `alpha`**:

- `n_flip = multiplier * n` here, vs `n_flip = n` in RadioGS — affects the returned
  *normal* only.
- RadioGS additionally zeroes the SH colour when back-culling — affects *colour*
  only.

The accumulation that produces `alpha` is character-for-character the same in both:
`alpha = min(0.99, o * exp(-0.5 * dot(p_g,p_g)))`, `if (alpha < alpha_min) continue`,
`O += T * alpha`, `T *= (1 - alpha)`, `params.alpha[idx.x] = O`. Since coverage
depends on `alpha` alone, **the statistic transfers between the two codebases
exactly.** That is a meaningful strengthening of gate (a).

### Three parameter differences the port must decide, not inherit

| | RadioGS | LumiMotion | source |
|---|---|---|---|
| `light_t_min` | 0.05 | **0.1** | `RadioGS: arguments/__init__.py:104` vs `arguments/__init__.py:92` |
| `alpha_min` | 1/255 | **1/100** | `RadioGS: scene/radiogs_gaussian_model.py:118` vs `scene/gaussian_model.py:106` |
| `back_culling` | `--bc 1` default, "the value TRAINING used" (`RadioGS: observability.py:283-288`) | **always False** | see below |

On `back_culling`: it appears in LumiMotion **only** as a defaulted parameter at
`scene/gaussian_model.py:636` and its use at `:658`. Grep over the whole tree
(excluding `submodules/`) finds no caller that ever passes it. LumiMotion's own
visibility trace at `render_ir.py:503-505` omits it. **So the value this model
actually used is `back_culling=False`**, and RadioGS's `--bc 1` default does not
transfer. Per the doctrine "the coverage measured is the coverage the model
actually had" (`RadioGS: observability.py:11`), the port should use `False`, and
should say so before running rather than after.

### One definitional deviation that must be declared under gate (a)

RadioGS's visibility is **per-Gaussian**: `precompute_incidents` traces from
`position = self.get_xyz` (`RadioGS: radiogs_gaussian_model.py:846-848`).

LumiMotion's is **per-pixel**: `rendering_equation` is called with `points[mask]`,
and `points` is a depth-reprojected surface buffer,
`points = surf_depth * rays_d_hw_unnormalized + camera_center`
(`gaussian_renderer/render_ir.py:217`), used as the ray origin at `:503-505`.

A per-Gaussian coverage array indexed by canonical identity therefore cannot be
"LumiMotion's own visibility function" in the literal sense it was for RadioGS. The
port must trace from the deformed Gaussian centres `get_xyz + d_xyz`, which is the
correct analogue of the RadioGS construction but is a *deviation from LumiMotion's
render path*. It should be stated as such in the gate (a) report rather than
glossed.

---

## 8. Two findings that bear on the design, for decision before Stage 1

Raising these now because brief §3 says Stage 0 answers may change the design, and
because both are of the class that quietly biases the result toward the null — the
same class as the BVH bug.

**8.1 The bottom C_rigid decile will not be a clean concavity-interior population.**
The 98°/135° camera cap (Q3) guarantees a large never-observed back-side population
with C_rigid = 0 and C_seq = 0. The binary-feature split (Q6b) adds that 78% of
Gaussians have exactly zero self-displacement. The bottom decile of C_rigid will be
some mixture of (i) genuine concavity interiors — the population P1 and P2 are about,
(ii) back-side Gaussians no camera in either arm can see, and (iii) static Gaussians
that can only gain through occluder motion. Groups (ii) and (iii) dilute the
measured gain downward.

**8.2 C_rigid = 0 handling is now a pre-registration item, not a footnote.**
Brief §4 already requires reporting the count and handling of C_rigid = 0. Given
8.1, the *choice* of handling materially moves P1. It must be fixed in writing
before the arrays are inspected.

I am not proposing a new experiment, and `CLAUDE.md` is explicit that the
registered design is not to be renegotiated after seeing results. These are
pre-data observations about what the registered statistic will measure on this
asset. The options I can see, for Francesco to choose between:

- **Leave the design exactly as registered**, and report 8.1 as a stated limitation
  and a bias direction (toward the null) in the write-up. Defensible, and the
  cheapest.
- **Report the deciles both pooled and restricted to `binary_feature > 0.5`**, as
  a pre-declared secondary stratification, with P1/P2 adjudicated on the pooled
  arm as registered. This costs nothing at measurement time — brief §6 already
  requires dumping raw per-Gaussian arrays — and Q6b shows the restriction is
  unambiguous (0.1% ambiguous). `HANDOVER.md` §9.2 is directly on point: pooled
  correlations across heterogeneous units masked a within-unit effect by 13–15×.
- Both of the above also require the §4 "verify the restriction restricts" check.

My recommendation is the second, declared before Stage 1 runs, with P1/P2 still
adjudicated on the pooled arm exactly as §2 registers them so the pre-registration
is not weakened.

---

## 9. `CLAUDE.md` [verify] entries — confirmed and corrected

Not applied to the file; reported for approval.

| entry | verdict |
|---|---|
| BVH bug — NVS eval, `eval_nvs_dynamic.py:69,86-88` | **line numbers correct**, path should be `scripts/eval_nvs_dynamic.py` |
| BVH bug — relight eval, `eval_relight_dynamic.py:80,97-99` | **line numbers correct**, path should be `scripts/eval_relight_dynamic.py` |
| correct BVH handling, `train_stage2.py:155-159` | **exactly correct**, path should be `scripts/train_stage2.py` |
| `_albedo_dc_stage1` [verify location] | → `scene/gaussian_model.py:411`; consumed at `gaussian_renderer/render_ir.py:149` |
| `get_binary_feature()` [verify location] | → `scene/gaussian_model.py:179-197` |
| `blend_files/` | exists — `blend_files/blendfiles_v5_specular32` |
| `scripts_local/` | exists, 11 files |
| `scripts_local/test2/` | exists, 4 files |
| RadioGS path `~/projects/RadioGS-public`, branch `audit-notes` | **confirmed**, HEAD `ff1d1c5` |
| coverage statistic in `scripts_local/phase3b/observability.py` | **confirmed** — see Q1 |

Two additions worth making at the same time:

- **Trained models are at `/data/fmb/lumimotion/outputs_test1/chapelday_goldenbay/{jumpingjacks,standup}150_v5_spec32_r2_mlp`**, latest iteration 55000. Not currently in the table.
- ⚠️ **`cfg_args` in both trained models records
  `source_path='/home/fmb/projects/LumiMotion/data/...'` — the sibling worktree.**
  `get_combined_args` will use that path unless `-s` is passed explicitly. Any
  Stage 1 script must override it with this worktree's `data/` path. This is a
  live tripwire against the "never read from the sibling worktree" rule and belongs
  in the footgun list.

### Two `CLAUDE.md` statements that are not accurate for this repo

- **"Submodules are not independently checked out per worktree."** They are.
  `.gitmodules` is empty (one newline); `submodules/` is 1,543 ordinary tracked
  files, and `submodules/surfel_tracer` has no `.git`. Each worktree gets its own
  copy. The related claim that submodules are "dirty from compilation" is also not
  true here right now — `git status --short submodules/` is clean.
- **The shared-compiled-extension warning stands, and I checked it.**
  `surfel_tracer` is pip-installed into the `lumimotion` env
  (`.../site-packages/surfel_tracer/_C.cpython-38-x86_64-linux-gnu.so`, built
  2026-08-07), so it *is* shared across worktrees. I verified the specific risk:
  the only file under `submodules/` that differs between `lumimotion-observability`
  and `constitutive-appearance` is `simple-knn/simple_knn.egg-info/PKG-INFO`, a
  build-metadata artifact. **The tracer source is identical on both branches**, so
  a rebuild from the sibling branch cannot have changed the coverage kernel.
  *Residual uncertainty, flagged not resolved:* the installed `.so` predates both
  worktree checkouts, and I cannot prove it was compiled from the current source
  without rebuilding, which `CLAUDE.md` forbids unprompted. The branch-invariance
  above bounds the risk but does not eliminate it.

### `HANDOVER_REVIEW.md` A1 is now out of date

A1 states `--probe_src` is not implemented (`grep -c` → 0). It **is** implemented:
`RadioGS: observability.py:275-279` defines the flag and `:324-359` is the scoring
branch, including the camera gate. RadioGS HEAD `ff1d1c5` is titled "Finalise
handover: apply review corrections, implement --probe_src". Not load-bearing for
this experiment, noted so it is not re-derived.

---

## 10. `AGENTS.md` vs `CLAUDE.md`

`AGENTS.md` is an **untracked, stale byte-for-byte copy of `CLAUDE.md`** with a
single difference:

```
AGENTS.md:176   reimplement. Path to that repo: `[TODO — fill on first session]`.
CLAUDE.md:176   reimplement. Path to that repo: `~/projects/RadioGS-public`.
```

`git ls-files` tracks `CLAUDE.md` only; `AGENTS.md` shows as untracked in
`git status`. `CLAUDE.md` was updated at 11:02, `AGENTS.md` last written at 10:54.

**No substantive conflict** — no rule, footgun, or scope statement differs. The one
difference is a placeholder that `CLAUDE.md` has since filled, so `CLAUDE.md` is
strictly newer and strictly more complete. I followed `CLAUDE.md`. Recommend
deleting `AGENTS.md`, or replacing it with a one-line pointer to `CLAUDE.md`, so
the two cannot drift apart on something that matters.

Separately, and independent of `AGENTS.md`: **both files say Stage 0 is "six
questions"** (`CLAUDE.md:207`, `AGENTS.md:207`) while
`exp1_coverage_under_deformation_brief.md:115-131` asks **seven**. The brief
governs and I answered seven. `CLAUDE.md` should be corrected.
