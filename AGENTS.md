# AGENTS.md — Constitutive Appearance / LumiMotion

## Project

This worktree is the active research branch for **constitutive appearance**:
deformation-conditioned reflectance for dynamic Gaussian inverse rendering.

Repository/worktree:

```text
/home/fmb/projects/LumiMotion
branch: constitutive-appearance
```

A separate worktree exists for an unrelated observability direction:

```text
/home/fmb/projects/LumiMotion-observability
branch: lumimotion-observability
```

**Do not switch branches, edit the other worktree, cherry-pick from it, compare
against it, or treat its state as part of this project unless explicitly asked.**

The goal of this branch is a **new method paper**, not an evaluation/diagnostics
paper and not a continuation of the previous dynamic-GI mechanism hunt.

---

## Read this first

The authoritative research-direction document for this worktree is:

```text
docs/CONSTITUTIVE_APPEARANCE_DIRECTION.md
```

Read it before doing substantive work.

The completed substrate audit is:

```text
docs/constitutive_code_audit.md
```

Current validated instrument/results documents:

```text
docs/constitutive_strain_interface_spec.md
docs/constitutive_strain_validation_prereg.md
docs/constitutive_strain_extractor_validation.md
docs/constitutive_deformation_regime_prereg.md
docs/constitutive_deformation_regime_results.md
docs/constitutive_blender_version_fidelity_prereg.md
docs/constitutive_blender_version_fidelity_results.md
```

Historical LumiMotion campaign documents live under:

```text
docs/miscellaneous/
```

The most useful historical references are:

```text
docs/miscellaneous/lumimotion_campaign_summary.md
docs/miscellaneous/lumimotion_eval.md
docs/miscellaneous/lumimotion_repro.md
docs/miscellaneous/test1_hook_points.md
docs/miscellaneous/blend_files_survey.md
```

Treat `docs/miscellaneous/` as **historical evidence, not the current research
plan**. Some files contain superseded analyses, retracted claims, or debugging
paths from the previous campaign.

Prefer:
1. current source code for implementation facts;
2. `docs/constitutive_code_audit.md` for the current LumiMotion substrate state;
3. `docs/CONSTITUTIVE_APPEARANCE_DIRECTION.md` for the active research framing;
4. `docs/miscellaneous/` only for historical context.

Do not reorganize, rewrite, or "clean up" `docs/miscellaneous/` unless explicitly
asked.

---

## Current research hypothesis

Current dynamic inverse-rendering methods deform geometry while largely treating
intrinsic material parameters as deformation-invariant.

The working hypothesis is:

> Local deformation changes intrinsic surface reflectance for some deformable
> materials, and this response can be represented and recovered as a function
> of local physical deformation rather than arbitrary time.

Working representation:

```text
theta_i,t = theta_i^0 + g(z_i, epsilon_i,t)
```

where:

- `theta_i^0` is the canonical material state;
- `z_i` is material/local identity;
- `epsilon_i,t` is a local physical deformation/strain descriptor;
- `g` is a low-capacity constitutive appearance law.

A direct timestep input is **not** the intended scientific model.

The key final generalization axis is **unseen deformation**, ideally combined
with unseen illumination.

The intended paper is not merely about making material dynamic. It is about
recovering a **constitutive appearance law**:

```text
local material deformation
        ->
intrinsic reflectance response
```

---

## What this project is NOT

Do not silently drift into any of these framings:

- "add PBR to dynamic Gaussians";
- "make LumiMotion roughness time-varying";
- generic time-conditioned appearance;
- static anisotropic Gaussian inverse rendering;
- dynamic multi-bounce GI / temporal GI caching;
- a RadioGS indirect-light fix;
- a benchmark/diagnostics-only paper.

If a proposed change weakens the thesis toward one of these, flag it before
implementation.

In particular:

```text
roughness = MLP(time)
```

is not the intended method.

The scientific distinction we want to preserve is:

```text
same material + same deformation state
    ->
same material response
```

even if the same state occurs at a different time or under a different motion.

---

## Current phase

The geometry/strain instrument chain is complete for the current stage.

Verified state:

- LumiMotion substrate audit: **DONE**;
- strain-interface specification: **DONE**;
- controlled Path-A validation: **DONE**;
- all-four-scene Joanna deformation-regime characterization: **DONE**;
- Blender 3.6.13 vs 4.4.0 evaluated-geometry/strain fidelity: **DONE — PASS**.

Current project sequence:

```text
LumiMotion substrate audit                    [DONE]
    ->
strain-interface specification                [DONE]
    ->
validated mesh strain extraction              [DONE]
    ->
measure available deformation regime          [DONE]
    ->
Blender-version geometry/strain fidelity       [DONE — PASS]
    ->
independent material-response calibration      [CURRENT]
    ->
Gate-1 preregistration
    ->
synthetic signal / observability gate
    ->
real-material existence gate
    ->
minimal LumiMotion prototype
    ->
anisotropic/material-frame extension if justified
```

### Current task boundary

The immediate task is **independent material-response calibration**: establish
from external material-physics evidence what deformation→reflectance response is
defensible over the measured deformation regime, then freeze Gate 1.

Do **not**:

- implement Path B;
- modify LumiMotion training/material code;
- implement deformation-conditioned roughness;
- choose a response law because it makes a strong image effect;
- run the Gate-1 appearance experiment before its preregistration is frozen;
- run another geometry/Blender-version experiment without a new concrete
  inconsistency.

The deformation-support question and the Blender-version concern are closed for
this stage.

## Default operating mode

### Default to read-only

Unless the user explicitly asks for an implementation:

- do not modify source code;
- do not change configs;
- do not install/update packages;
- do not render;
- do not train;
- do not launch long jobs;
- do not change datasets;
- do not rewrite existing research documents.

Writing a requested analysis/specification document under `docs/` is allowed.

### User launches long jobs

The user launches all long jobs manually in `tmux`.

When a future task requires a long render/training job:

1. prepare and verify the script/command;
2. check for conflicting processes when appropriate:
   ```bash
   pgrep -af <script-or-process-name>
   ```
3. hand the command/script to the user;
4. do **not** launch the long job unless explicitly asked.

Do not use `nohup` as a substitute for `tmux`.

---

## Scientific discipline

The previous campaign caught multiple convincing but wrong results. Preserve the
following rules.

### Pre-register before confirmatory tests

Before any experiment whose outcome affects the direction, write down:

- hypothesis;
- primary prediction(s);
- falsifier(s);
- primary statistic;
- threshold / kill criterion;
- controls;
- exclusions;
- analysis convention.

Do this **before** inspecting the confirmatory result.

Exploratory analysis may generate hypotheses, but label it exploratory and do not
retroactively present its pattern as pre-registered evidence.

### Prefer a cheap kill

Before implementing a full method, ask whether the physical signal is:

- real;
- large enough;
- observable under the intended capture conditions;
- not absorbable by a strong baseline;
- identifiable independently of geometry/normal error.

If a cheap test can kill the premise, do that first.

### Healthy controls are mandatory

Whenever possible, test a mechanism in a condition where it should **not** fire.

For this project, especially important controls include:

- same-frame identity deformation;
- known synthetic stretch;
- rigid translation/rotation (`strain ≈ 0`);
- GT geometry/normals when testing material-change mechanisms;
- held-out deformation;
- held-out illumination.

### Verify invariants numerically

Do not trust plausible images.

For deformation extraction, expected invariants include:

```text
same configuration         -> F ≈ I
rigid motion               -> U ≈ I
known uniaxial stretch     -> recovered principal stretch matches authored value
```

For render decompositions or new buffers, define and assert any conservation
identity that should hold.

### Keep physical quantities distinct

Do not use authored settings as proxies for physical quantities.

Do not conflate:

- time with deformation;
- rotation with strain;
- world-frame orientation with intrinsic material state;
- display-space PNG values with linear radiance;
- static material fitting error with deformation-conditioned material response;
- Gaussian scale with physical surface stretch.

---

## Code-audit standards

For read-only audits:

1. cite exact `file:line` ranges;
2. trace call sites, not only definitions;
3. separate verified source facts from inference/design suggestions;
4. state uncertainty explicitly;
5. verify whether a variable actually reaches the relevant computation;
6. prefer minimal data-flow diagrams over broad prose;
7. check initialization, optimization, serialization/checkpointing, evaluation,
   and rendering paths separately;
8. identify silent failure modes.

A useful audit should answer **where the minimal future hook belongs** without
implementing it prematurely.

---

## Verified substrate facts from the constitutive-appearance audit

Source:

```text
docs/constitutive_code_audit.md
```

These facts were verified against the current `constitutive-appearance` source
tree and should not be re-derived unless the relevant code changes.

### Stage-2 material state

Stage-2 intrinsic albedo and scalar roughness are per-Gaussian and
**time-invariant**.

There is no learned metallic parameter.

The direct BRDF uses a fixed dielectric Fresnel term.

Material parameters are serialized through the Gaussian PLY.

Stage-2 geometry/deformation is frozen while material parameters remain
optimizable.

Important qualification:

appearance is **not wholly time-invariant** even though intrinsic material is.

A time-conditioned Stage-1 shadow/radiance pathway remains active and can
compensate for material errors.

Therefore future constitutive-material comparisons must distinguish:

```text
intrinsic material change
vs.
time-conditioned radiance/shadow compensation
```

Do not interpret an image-space gain as material evidence without controlling
this pathway appropriately.

### Gaussian identity

Gaussian identity is **not stable during Stage 1** because densification,
splitting, and pruning change topology.

After the selected Stage-1 checkpoint is loaded into Stage 2:

- Gaussian count/order is fixed;
- Stage 2 performs no densification or pruning;
- canonical Gaussian row `i` maps deterministically to deformed row `i`
  at every timestep.

This correspondence is checkpoint-local.

There is no persistent semantic Gaussian ID stored across independently written
PLY files.

Any canonical neighbourhood graph must therefore be associated with the exact
loaded Stage-1 checkpoint / PLY row ordering.

### Canonical and deformed state

At the shared `render_ir` path, canonical and deformed Gaussian positions
coexist:

```text
x_i^canonical
x_i^t = x_i^canonical + d_xyz_i,t
```

Canonical and deformed rotations/scales are also simultaneously available.

This is the preferred future seam for deformation-state computation.

### Scale is NOT physical strain

The deformation model predicts `d_scaling` but then forcibly zeroes it.

Therefore:

```text
Gaussian scale change != available physical stretch signal
```

Do not use Gaussian scaling as a deformation/strain proxy.

Any strain estimate must instead come from the relative motion of a fixed
canonical neighbourhood.

### Canonical neighbourhoods

No persistent canonical kNN graph currently exists.

The bundled `simple-knn` functionality used by LumiMotion returns nearest-
neighbour distance for scale initialization; current Python code does not retain
neighbour identities.

A future Gaussian strain estimator will therefore need an explicitly computed
and stored fixed canonical neighbour graph.

That graph should:

- be built after loading the exact Stage-1 checkpoint used by Stage 2;
- preserve canonical row identity;
- remain fixed across timesteps;
- not be recomputed in deformed space.

### Normals and material frames

LumiMotion has geometric surfel orientation/normals but no stored:

- tangent;
- bitangent;
- UV;
- intrinsic material axis/frame.

The current GGX model is isotropic.

Therefore scalar isotropic roughness is the intended first constitutive-
appearance target.

Directional / anisotropic material response is intentionally deferred until a
stable material-frame representation is justified.

Do not silently infer a material frame from a view-dependent or ambiguously
signed geometric normal.

### Oracle roughness consistency

A future externally supplied per-Gaussian/per-frame roughness field must be
used consistently in BOTH:

1. primary material rasterization;
2. secondary ray-traced material features used for relighting/indirect light.

Updating only the primary rasterized roughness would create two inconsistent
material definitions for the same Gaussian.

The audit's unified-material approach ("Candidate B") is therefore the preferred
future oracle architecture.

Do not implement it yet.

### Dynamic evaluation BVH bug

Current source confirms:

- Stage-2 training builds the BVH and updates/refits it for later dynamic frames;
- dynamic NVS evaluation builds on the first frame and does not update it;
- dynamic relighting evaluation has the same stale-first-frame behavior.

Any future quantitative dynamic NVS/relighting comparison that uses secondary
visibility must address this before results are interpreted.

Do not fix it opportunistically during unrelated tasks.

Make it an explicit, scoped change when evaluation work begins.

### Current substrate verdict

```text
feasible with architectural caveats
```

No audit finding invalidates the scalar constitutive-appearance direction.

The major remaining uncertainty is scientific, not architectural:

```text
Is deformation-dependent reflectance strong and observable enough to matter?
```

That question must be approached only after deformation/strain extraction has
been defined and validated.

---

## Joanna's author-shared Blender assets

Joanna's author-shared Blender files are already present locally in this worktree
at:

```text
blend_files/blendfiles_v5_specular32/
```

The directory contains the five main scene families:

```text
hook150_v5_specular32.blend
jumpingjacks_v5_specular32.blend
mouse_v5_specular32.blend
spheres_with_rotations_v5_specular32.blend
standup150_v5_specular32.blend
```

plus:

- `*_dynamic_mask.blend`;
- `*_roughness.blend`;
- `envmaps_32/`;
- `blendfiles_for_normals_examples.zip`.

These files predate the `constitutive-appearance` branch and were inherited from
the previous LumiMotion research campaign.

### Git status

`blend_files/` is intentionally ignored by `.gitignore`.

Verified:

```bash
git status --short blend_files/
git ls-files blend_files/ | head
```

both return no tracked files.

Therefore:

- treat `blend_files/` as **local, private, untracked research data**;
- do not move or rename it merely for project organization;
- do not change `.gitignore` rules for it;
- do not use `git add -f` on anything under `blend_files/`;
- do not commit, upload, repackage, or redistribute these assets;
- do not delete or clean them;
- do not save over or re-export the original `.blend` files.

Unless a task explicitly requires Blender-level inspection or rendering, treat
the contents as read-only.

For code-audit tasks it is acceptable to inspect:

- directory/file names;
- repository code referring to `blend_files/`;
- generation scripts already present elsewhere in the repository;
- historical documentation describing the assets.

Do not launch Blender merely to reconfirm facts already established by the
existing survey unless the current task requires it.

The historical read-only survey is:

```text
docs/miscellaneous/blend_files_survey.md
```

Important established facts from that survey include:

- the character scenes use Armature-driven animation;
- the dynamic-mask **RGB** channels encode the dynamic/static segmentation;
- the mask Alpha channel is the whole opaque foreground silhouette;
- camera sampling uses fixed seed `40422`;
- dynamic animation frame `i` is paired with camera sample `i`;
- the surveyed character Principled material uses fixed roughness `0.553`;
- the current Blender benchmark therefore does **not** contain deformation-
  dependent roughness ground truth;
- Color Management -> View Transform is stored per `.blend` file and is not set
  by the embedded dataset-generation scripts.

These are useful historical facts, but when a future task depends on exact
current repository behavior, verify the corresponding code path rather than
relying solely on prose.

### Role in the constitutive-appearance project

These assets are expected to become useful after the current strain-interface
specification because their animated meshes may provide canonical and deformed
surface geometry for validating local strain extraction.

They should **not** be treated as evidence for deformation-dependent reflectance:
their authored material parameters are essentially deformation-invariant.

Do not implement a strain extractor, modify these scenes, or generate new renders
until the relevant step has been designed and approved.

---

## Blender version policy

Blender version is **task-specific**.

Known evidence:

- portable Blender **3.6.13** opens all 15 surveyed author-shared main `.blend`
  files cleanly and matches the file-format version reported by the survey;
- one hook asset warns about content written by Blender **4.4.32**;
- prior reproduction work found non-trivial render differences across Blender
  versions and preferred 4.4.x when matching author GT.

Therefore:

1. for read-only inspection of the shared archive, 3.6.13 is the known-safe
   reader;
2. for quantitative rendering, choose the binary deliberately for that
   experiment;
3. record the exact Blender binary/version in the preregistration/manifest;
4. never mix Blender versions within one quantitative comparison;
5. do not save/re-export author files merely to silence compatibility warnings.

Do not use the system Blender 3.0.1 for these files; the survey found it crashes.

---

## Environment

Use the existing working environment unless a concrete requirement proves it
insufficient.

Known environment:

```text
conda env: lumimotion
Python:    3.8.18
CUDA:      12.1
PyTorch:   2.1
```

Do not rebuild or upgrade the environment casually.

GPU jobs should use explicit `CUDA_VISIBLE_DEVICES` when relevant.

---

## Git / worktree discipline

This repository is a Git worktree.

Rules:

- remain on branch `constitutive-appearance`;
- do not switch branches;
- do not modify the sibling observability worktree;
- do not use `git add .`;
- stage files explicitly;
- do not commit generated data, checkpoints, renders, private assets, or scratch
  outputs;
- do not use `git add -f` on `blend_files/`;
- do not rewrite history unless explicitly asked;
- inspect `git status` before and after edits;
- keep changes minimal and scoped to the requested task.

If submodules or generated build files are dirty, do not "clean" them without
permission.

---

## Project file organization

Current intended structure:

```text
docs/
├── CONSTITUTIVE_APPEARANCE_DIRECTION.md
├── constitutive_code_audit.md
├── constitutive_strain_interface_spec.md
├── constitutive_prereg_gate1.md
├── constitutive_results_log.md
└── miscellaneous/
    └── historical campaign material

scripts_local/
└── constitutive/
    ├── audit/
    ├── blender/
    ├── strain/
    ├── analysis/
    └── manifests/
```

Do not create all empty directories preemptively.

Create only what the active task requires.

New research documents should live directly under `docs/`, not in
`docs/miscellaneous/`.

---

## Documentation etiquette

When producing a research document:

- state the question first;
- distinguish **VERIFIED**, **INFERRED**, **PROPOSED**, and **UNKNOWN**;
- cite exact source locations for code claims;
- record commands that were actually run;
- record environment/version details relevant to reproducibility;
- do not convert an exploratory observation into a claim;
- preserve failed/null results;
- append correction notes rather than silently rewriting history when a result
  has already informed later work.

For each confirmatory gate, maintain one preregistration document and one result
document.

---

## Current task: strain-interface specification

The substrate audit is complete.

The next task is a **specification only**, not implementation.

Create:

```text
docs/constitutive_strain_interface_spec.md
```

The specification must define two compatible deformation-state paths.

### A. Ground-truth mesh strain

For controlled physics/signal experiments using Joanna's animated Blender
meshes.

It must define:

- canonical/reference configuration;
- topology-stability requirements;
- evaluated-mesh coordinate convention;
- triangle-level surface deformation;
- principal stretches `lambda1`, `lambda2`;
- rotation-invariant strain quantities;
- degeneracy / conditioning handling;
- authoritative face-level outputs;
- optional face-to-vertex aggregation;
- numerical validation invariants;
- output manifest / provenance requirements.

### B. Future Gaussian-estimated strain

For the eventual LumiMotion method.

It must define:

- association with an exact Stage-1 checkpoint;
- fixed canonical neighbour graph;
- canonical/deformed row correspondence;
- local surface deformation estimation from neighbour positions;
- compatibility with the mesh-side strain descriptor;
- why Gaussian scale / `d_scaling` is not physical strain;
- limitations caused by the absence of a material tangent frame.

The two paths should expose the same physical deformation invariants wherever
possible.

### Mandatory future implementation gates

Any future strain extractor must pass these before Joanna's animations are
scientifically interpreted:

```text
identity:
same geometry -> lambda1 ≈ 1, lambda2 ≈ 1

rigid transform:
rotation/translation -> lambda1 ≈ 1, lambda2 ≈ 1

known uniaxial stretch:
1.10x authored stretch -> one principal stretch ≈ 1.10,
                          the other ≈ 1.00
```

Do not choose the strain-to-roughness constitutive law in the interface
specification.

Do not inspect Joanna's animation strain distribution before the extractor is
validated.

Do not implement deformation-conditioned material training during this phase.

---

## Stop conditions

Stop and report instead of improvising if:

- current source contradicts a central assumption in
  `CONSTITUTIVE_APPEARANCE_DIRECTION.md`;
- Gaussian identity/topology becomes unsuitable for the planned strain model;
- material variables differ materially from `constitutive_code_audit.md`;
- a task requires destructive modification of Joanna's assets;
- a confirmatory experiment lacks preregistered predictions/falsifiers;
- a long job would need to be launched without explicit user instruction;
- an implementation would collapse into generic time-conditioned appearance;
- a proposed strain definition depends on Gaussian scale as a physical stretch
  proxy;
- a result depends on stale dynamic-evaluation BVHs without explicitly fixing or
  controlling them.

The correct outcome of an audit/specification can be:

> **The proposed path is not viable.**

Do not force a positive result.
