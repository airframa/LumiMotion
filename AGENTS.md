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

**Do not switch branches, edit the other worktree, cherry-pick from it, or treat
its state as part of this project unless explicitly asked.**

The goal of this branch is a **new method paper**, not an evaluation/diagnostics
paper and not a continuation of the previous dynamic-GI mechanism hunt.

## Read this first

The authoritative direction document for this worktree is:

```text
docs/CONSTITUTIVE_APPEARANCE_DIRECTION.md
```

Read it before doing substantive work.

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
paths from the previous campaign. Prefer the latest summary when historical
documents conflict, and verify code facts against the current source tree rather
than trusting old prose.

Do not reorganize, rewrite, or "clean up" `docs/miscellaneous/` unless explicitly
asked.

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

- `theta_i^0` is the canonical material state,
- `z_i` is material/local identity,
- `epsilon_i,t` is a local deformation/strain descriptor,
- `g` is a low-capacity constitutive appearance law.

A direct timestep input is **not** the intended scientific model.

The key final generalization axis is **unseen deformation**, ideally combined
with unseen illumination.

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

## Current phase

We are at the **pre-method feasibility stage**.

The planned sequence is:

```text
read-only LumiMotion code audit
    ->
validated deformation/strain extraction
    ->
pre-registered synthetic signal gate
    ->
real-material existence gate
    ->
minimal LumiMotion prototype
    ->
anisotropic/material-frame extension if justified
```

**Do not skip ahead.**

At the moment, the immediate task is the read-only LumiMotion code audit.
No training-code modification is justified yet.

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

Writing a requested analysis document under `docs/` is allowed.

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
- held-out deformation and held-out illumination.

### Verify invariants numerically

Do not trust plausible images.

For deformation extraction, expected invariants include:

```text
same configuration -> F ≈ I
rigid motion        -> U ≈ I
known uniaxial stretch -> recovered principal stretch matches authored value
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
- static material fitting error with deformation-conditioned material response.

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

## LumiMotion facts and historical hazards

### Evaluation BVH bug

Previous inspection found that released dynamic eval scripts build the BVH at
frame 0 and do not update it per frame, while training does update it.

Any future head-to-head evaluation must re-check and fix/avoid this issue before
using the baseline numbers.

### Dynamic-mask semantics

For the author-shared Blender mask generator:

- **RGB** is the dynamic/static segmentation;
- **Alpha** is essentially the whole opaque foreground silhouette.

Do not use Alpha as the dynamic-only mask.

### Camera generation

The author scripts use deterministic random camera sampling with seed `40422`.
Dynamic frame `i` is paired with camera sample `i`.

Static-timestep variants keep the mesh at a fixed frame while cycling through the
same camera sequence.

### Color management

Color Management -> View Transform is a saved per-file Blender property and is not
set by the embedded generation scripts.

- beauty files were surveyed with `Standard`;
- a normal-pass example uses `Raw`.

Any new pass must explicitly inspect/set the intended view transform.

### Current authored character material

In the surveyed character files, the character Principled material uses fixed
roughness `0.553` rather than deformation-dependent roughness.

Therefore the existing Blender benchmark is **not** ground truth for the proposed
constitutive-appearance phenomenon.

## Joanna's author-shared Blender assets

Joanna's author-shared Blender files are already present locally in this worktree at:

```text
blend_files/blendfiles_v5_specular32/
```

The directory contains the five main scene families and their associated variants:

```text
hook150_v5_specular32.blend
jumpingjacks_v5_specular32.blend
mouse_v5_specular32.blend
spheres_with_rotations_v5_specular32.blend
standup150_v5_specular32.blend
```

plus:

- `*_dynamic_mask.blend`
- `*_roughness.blend`
- `envmaps_32/`
- `blendfiles_for_normals_examples.zip`

These files predate the `constitutive-appearance` branch and were inherited from the previous LumiMotion research campaign.

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

Unless a task explicitly requires Blender-level inspection or rendering, treat the contents as read-only.

For code-audit tasks, it is acceptable to inspect:

- directory/file names;
- repository code referring to `blend_files/`;
- generation scripts already present elsewhere in the repository;
- historical documentation describing the assets.

Do not launch Blender merely to reconfirm facts already established by the existing survey unless the current task requires it.

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
- the current Blender benchmark therefore does **not** contain deformation-dependent roughness ground truth;
- Color Management → View Transform is stored per `.blend` file and is not set by the embedded dataset-generation scripts.

These are useful historical facts, but when a future task depends on exact current repository behavior, verify the corresponding code path rather than relying solely on prose.

### Role in the constitutive-appearance project

These assets are expected to become useful after the current code audit because their animated meshes may provide canonical and deformed surface geometry for validating local strain extraction.

They should **not** yet be treated as evidence for deformation-dependent reflectance: their authored material parameters are essentially deformation-invariant.

Do not implement a strain extractor, modify these scenes, or generate new renders until the relevant experiment has been designed and pre-registered.

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
- do not rewrite history unless explicitly asked;
- inspect `git status` before and after edits;
- keep changes minimal and scoped to the requested task.

If submodules or generated build files are dirty, do not "clean" them without
permission.

## Project file organization

Current intended structure:

```text
docs/
├── CONSTITUTIVE_APPEARANCE_DIRECTION.md
├── constitutive_code_audit.md
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

Do not create all empty directories preemptively. Create only what the active
task requires.

New research documents should live directly under `docs/`, not in
`docs/miscellaneous/`.

## Documentation etiquette

When producing a research document:

- state the question first;
- distinguish **verified**, **inferred**, **proposed**, and **open**;
- cite exact source locations for code claims;
- record commands that were actually run;
- record environment/version details relevant to reproducibility;
- do not convert an exploratory observation into a claim;
- preserve failed/null results;
- append correction notes rather than silently rewriting history when a result
  has already informed later work.

For each confirmatory gate, maintain one preregistration document and one result
document.

## Current audit target

The next read-only audit should establish:

1. where Stage-2 albedo and roughness are initialized, stored, optimized,
   serialized, rasterized, and consumed;
2. whether they can currently depend on time/frame;
3. the exact canonical-to-deformed Gaussian data flow;
4. whether Gaussian identity is stable across time;
5. where canonical and deformed positions are simultaneously accessible;
6. how normals/rotations/scales are transformed;
7. whether a local deformation gradient can be derived from fixed canonical
   Gaussian neighborhoods without changing Stage 1;
8. what kNN/neighborhood machinery already exists;
9. the narrowest future hook for an externally supplied oracle time-varying
   roughness field;
10. silent hazards for strain estimation or material conditioning.
11. determine how `blend_files/blendfiles_v5_specular32/` relates to the
    generated LumiMotion datasets and whether any existing repository code
    already extracts geometry, animation state, normals, roughness, masks, or
    per-frame metadata from those source scenes.

Do not implement any of these changes during the audit.

## Stop conditions

Stop and report instead of improvising if:

- the current source contradicts a central assumption in
  `CONSTITUTIVE_APPEARANCE_DIRECTION.md`;
- Gaussian identity/topology is not stable in the way the planned strain model
  requires;
- the intended material variables are not where historical docs say they are;
- an audit requires destructive conversion of Joanna's assets;
- a requested experiment lacks a preregistered prediction/falsifier;
- a long job would need to be launched without the user's explicit request;
- a proposed implementation would turn the method into generic time-conditioned
  appearance without a clear scientific reason.

The correct outcome of an audit can be: **the planned hook is not viable**.
Do not force a positive design conclusion.
