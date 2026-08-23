# Constitutive Appearance for Dynamic Gaussian Inverse Rendering
## Running research direction document

**Status:** Provisional research direction — hypothesis selected, first gate not yet run  
**Started:** 2026-08-23  
**Scope:** Dynamic inverse rendering + Gaussian splatting  
**Primary substrate candidate:** LumiMotion (CVPR 2026 Highlight)  
**Working name:** *Constitutive Appearance* / *Deformation-Conditioned Reflectance*

---

## 1. One-sentence thesis

Current dynamic inverse-rendering methods deform geometry while treating intrinsic material parameters as time-invariant. We hypothesize that, for deformable materials, **local deformation changes the reflectance itself**, and that this response can be recovered as a physically structured function of local strain rather than arbitrary time.

The target representation is therefore not merely a dynamic BRDF,

\[
\theta_{i,t} = g(i,t),
\]

but a **constitutive appearance law**

\[
\theta_{i,t}
=
\theta_i^0 + g_\psi(z_i,\epsilon_{i,t}),
\]

where:

- \(\theta_i^0\) is the canonical material state of Gaussian/surface element \(i\),
- \(z_i\) is a compact material identity or local material code,
- \(\epsilon_{i,t}\) is a physically meaningful local deformation descriptor,
- \(g_\psi\) predicts the deformation-induced change in reflectance.

The key intended generalization is:

> **same material + same local deformation state ⇒ same reflectance response, even at an unseen time, under an unseen motion, or under unseen illumination.**

This is the distinction between the proposed direction and a generic time-conditioned appearance MLP.

---

## 2. Why this is a research problem rather than “dynamic GS + PBR”

The novelty target is **not**:

- deformable Gaussians,
- PBR on deformable Gaussians,
- anisotropic BRDFs alone,
- relighting dynamic scenes,
- time-varying appearance,
- a larger deformation network.

Those spaces are already occupied or too close to “combine existing techniques.”

The target problem is:

> **Inverse recovery of how a material's scattering law changes as a function of its local deformation.**

This introduces a new latent quantity into dynamic inverse rendering: the **material response to deformation**.

### Current nearest neighbours

**LumiMotion (CVPR 2026 Highlight).** In its inverse-rendering stage, each Gaussian receives diffuse albedo and roughness, and the paper explicitly states that these properties remain constant across timesteps. Motion is used as supervision to improve material-light decomposition, but material itself is temporally invariant.

**DR-GS (ECCV 2026).** DR-GS performs static inverse rendering to recover albedo/metallic/roughness and then updates Gaussian geometry using deformation gradients from canonical to deformed configurations. Its central design decouples material from dynamic driving. This makes it a particularly important nearest neighbour: it already demonstrates that deformation gradients are practical in a Gaussian pipeline, but it uses them to update geometry rather than to infer a deformation-dependent material law.

**Prior graphics physics.** Nagano et al., *Measurement and Modeling of Microfacet Distributions under Deformation*, measured surface microgeometry under stretch/compression and reported that rough surfaces generally become flatter/shinier under tension and rougher under compression. They model this through deformation-dependent anisotropic microfacet roughness. This is physical precedent for the phenomenon, but not a dynamic multiview inverse-rendering solution.

### Novelty sentence to protect

The paper should eventually be able to say something close to:

> **We recover a constitutive appearance model that predicts how surface reflectance changes as a function of local deformation, enabling physically consistent relighting under unseen deformations.**

If the eventual method cannot support a statement substantially stronger than “we condition roughness on time/deformation,” the direction is not mature enough.

---

## 3. Relationship to the completed measurement campaign

This direction is **not a fifth explanation of the RadioGS indirect-light deficit**.

The previous campaign established several positive exclusions and several conditional findings. In particular:

- low envmap resolution does not explain the dynamic transport effect;
- the bounce-into-albedo causal interpretation was wrong;
- enclosed-scene RadioGS training violates three architectural assumptions;
- standard TensoIR scenes do not form a useful bounce ladder;
- observability is a real radiance-recovery mechanism but does not explain the between-shape attribution slope;
- the frozen-transport-content error is small on current open-platform LumiMotion benchmarks, with an important high-indirect/high-deformation exception.

None of those measurements tests whether **the material scattering law itself changes with deformation**.

The previous campaign does, however, impose methodological requirements on this project:

1. Measure the effect size before building the method.
2. Use healthy controls.
3. Pre-register predictions and falsifiers before confirmatory tests.
4. Do not pool heterogeneous units blindly.
5. Keep analysis in linear radiometric space unless a display-space metric is explicitly intended.
6. Verify every mask/pass/transfer function from source.
7. Treat authored settings as settings, not as physical quantities.
8. Prefer a cheap kill to a month of mechanism rescue.

---

## 4. Core physical hypothesis

Let \(F_{i,t}\) be a local deformation gradient mapping a canonical surface neighbourhood to timestep \(t\).

Use the polar decomposition

\[
F_{i,t}=R_{i,t}U_{i,t}.
\]

- \(R\): rigid/local rotation. This should change orientation in world space but **not intrinsic material state**.
- \(U\): stretch/shear state. This is the quantity allowed to change intrinsic reflectance.

Possible deformation descriptors include:

\[
\epsilon_{i,t}
=
[
\log \lambda_1,
\log \lambda_2,
\log(\lambda_1/\lambda_2),
\log(\lambda_1\lambda_2)
],
\]

where \(\lambda_1,\lambda_2\) are in-plane principal stretches.

A first material model could predict only scalar roughness:

\[
\alpha_{i,t}
=
\operatorname{clamp}
\left(
\alpha_i^0 +
g_\psi(z_i,\epsilon_{i,t})
\right).
\]

A stronger final model could predict anisotropic roughness in a transported material frame:

\[
(\alpha_u,\alpha_v)_{i,t}
=
h_\psi(z_i,\epsilon_{i,t}),
\]

with local tangent directions transported by the deformation.

### Important invariant

A pure rigid motion should produce:

\[
U = I
\quad\Rightarrow\quad
\Delta \theta = 0.
\]

This gives us a clean negative control that a time-conditioned appearance model does not naturally satisfy.

---

## 5. The first scientific question

Before touching LumiMotion training, answer:

> **At realistic deformation magnitudes, is the error caused by assuming a time-invariant BRDF large enough to matter in images?**

This is a **signal/existence gate**, not yet a method experiment.

A synthetic result alone will not prove that real materials behave this way — the shader will encode the phenomenon by construction. Its purpose is narrower:

1. establish whether literature-plausible reflectance changes are visible under the capture geometry and lighting regimes relevant to LumiMotion;
2. establish a measurable effect size;
3. determine whether the signal survives viewpoint and lighting changes;
4. determine whether a strong time-invariant material baseline can absorb it.

If this gate fails, the direction should be killed before any Gaussian-method implementation.

---

## 6. Joanna's LumiMotion Blender assets: how they help

The author-shared Blender drop is unusually useful for this project.

The surveyed archive contains 15 main `.blend` files over five scenes:

- `hook150`
- `jumpingjacks`
- `mouse`
- `spheres_with_rotations`
- `standup150`

with base, dynamic-mask, and roughness variants, plus HDRIs and normal-pass examples.

Useful properties:

- the character scenes contain an Armature-driven Mixamo animation;
- the character is a real skinned mesh, so canonical and deformed surface geometry can be extracted exactly;
- camera generation is deterministic and shared across the scenes (`seed=40422`);
- dynamic frame and camera index are paired one-to-one;
- four environment maps are available;
- the main render path uses Cycles;
- the character's authored Principled material in the surveyed hook scene uses **fixed roughness 0.553**, so the existing benchmark itself does **not** contain deformation-dependent roughness ground truth;
- normal maps and specular textures are available on the character;
- `spheres_with_rotations` provides a valuable rigid-motion control;
- roughness and dynamic-mask generation scripts make the data-generation conventions inspectable.

### What these assets are *not*

They are not evidence that deformation changes reflectance. Their current authored material is essentially time-invariant.

We should use copies of them as a controlled sandbox, not treat them as proof of the thesis.

### Blender version rule for this drop

The newest read-only survey reports the main files as Blender 3.6.13 files and confirms that portable Blender 3.6.13 opens all 15 cleanly. One hook asset emits a warning referencing Blender 4.4.32, likely due to a linked/appended sub-asset.

For this new project:

- default to the version validated by the asset survey for these exact files;
- never mix Blender versions within one quantitative gate;
- record the exact binary in every render manifest;
- explicitly set/check Color Management → View Transform for every new pass.

The existing beauty renders use **Standard**; the normal-pass example uses **Raw**. View Transform is a saved GUI property and is not set by the embedded scripts.

### Asset handling

These files were author-shared. Unless redistribution permission is explicit:

- use locally;
- do **not** commit the `.blend` files to the public repo;
- keep them under a gitignored/private data path;
- commit only our scripts, manifests, and documentation.

---

## 7. Recommended working environment

### Primary codebase

Use the **LumiMotion repo** as the main method-development substrate.

Reasons:

1. it already solves dynamic geometry + inverse rendering;
2. its Stage 2 explicitly assumes time-invariant albedo/roughness, which is the assumption under test;
3. it has already been reproduced locally;
4. Joanna's Blender scenes and generated benchmark are native to it;
5. it gives a clean baseline rather than forcing a dynamic architecture into RadioGS.

RadioGS should remain a reference/instrumentation repo, not the default implementation substrate for this direction.

### Environment

Keep the already-working `lumimotion` conda environment rather than rebuilding prematurely.

Known environment from the previous campaign:

- Python 3.8.18
- CUDA 12.1
- PyTorch 2.1
- long jobs launched manually in `tmux`

Do not change package versions until a concrete dependency requires it.

### Suggested branch

```text
constitutive-appearance
```

Do not start by editing training code.

### Suggested repo layout

```text
LumiMotion/
├── docs/
│   ├── CONSTITUTIVE_APPEARANCE_DIRECTION.md
│   ├── constitutive_code_audit.md
│   ├── constitutive_prereg_gate1.md
│   └── constitutive_results_log.md
│
├── scripts_local/
│   └── constitutive/
│       ├── audit/
│       ├── blender/
│       ├── strain/
│       ├── analysis/
│       └── manifests/
│
└── data_private/                  # gitignored or symlinked
    └── joanna_blend_files/
```

Prefer placing the actual `.blend` archive on `/data` and symlinking it into `data_private/`.

### Git rules

- never `git add .`;
- explicitly stage only our scripts/docs;
- keep generated renders/results on `/data`;
- keep author-shared assets out of git;
- use a manifest for every quantitative render.

---

## 8. Concrete research plan

### Phase 0 — freeze the question

**Goal:** prevent the method from drifting into generic dynamic appearance modeling.

Deliverables:

- this document;
- literature/nearest-neighbour table;
- explicit novelty sentence;
- non-goals;
- kill criteria.

**Decision:** selected direction is deformation-conditioned reflectance, not dynamic GI.

---

### Phase 1 — read-only LumiMotion code audit

**No training. No source modification.**

Use Codex/Claude Code in the LumiMotion repo to establish, with exact `file:line` references:

1. where per-Gaussian albedo and roughness live in Stage 2;
2. whether either can currently depend on timestep;
3. where canonical and deformed Gaussian positions/rotations/scales are available;
4. whether Gaussian identity is stable across time;
5. how normals are transformed under deformation;
6. where the deferred G-buffer is assembled;
7. where roughness enters the BRDF;
8. whether local canonical neighbours can be accessed cheaply;
9. the cleanest place to compute a local deformation gradient without altering Stage 1;
10. whether an existing deformation representation already exposes enough information to derive \(F\);
11. what would be required to render an oracle time-varying roughness field without optimizing it.

**Output:** `docs/constitutive_code_audit.md`.

This audit determines implementation feasibility, not scientific validity.

---

### Phase 2 — build an exact strain extractor on Blender meshes

Start outside the learning system.

For a selected Joanna scene:

1. evaluate the skinned mesh at canonical frame;
2. evaluate the same topology at timestep \(t\);
3. compute a local in-plane deformation gradient per triangle/vertex;
4. obtain principal stretches \(\lambda_1,\lambda_2\);
5. verify rigid-motion invariance numerically;
6. export deformation descriptors per frame.

#### Mandatory controls

**Rigid control:** `spheres_with_rotations` or an equivalent rigidly rotating mesh must produce approximately zero strain.

**Static-frame control:** same mesh evaluated twice at the same frame must produce identity deformation.

**Synthetic known-deformation control:** a simple patch stretched by a known factor must recover that factor.

Do not proceed to appearance rendering until these identities pass.

---

### Phase 3 — Gate 1: synthetic signal / observability test

This is the first experiment whose result affects whether the project lives.

**Pre-register it before rendering the full test.**

Use a copied Blender scene and a literature-plausible strain→roughness response.

The test should compare:

1. **GT constitutive material:** reflectance changes with local strain;
2. **canonical-fixed material:** material frozen at rest state;
3. **strong time-invariant oracle:** a spatial material field that is allowed to choose the best time-invariant roughness for each surface region across the sequence;
4. optionally, a **time-conditioned oracle** as a capacity upper bound, not as the proposed method.

Evaluate under:

- held-out camera views;
- at least one held-out environment map;
- deformation states spanning low to high strain;
- linear RGB foreground metrics;
- spatial maps of error versus strain.

#### Pre-registered predictions

**P1 — effect-size prediction**  
Error of the best time-invariant material model increases with deformation magnitude.

**P2 — mechanism prediction**  
Residuals concentrate in specular/high-angular-frequency appearance and remain when geometry, normals, lighting, and visibility are ground truth.

**P3 — generalization prediction**  
A strain-conditioned material law fit only on a subset of strain states improves held-out **deformation + lighting** rendering over the best time-invariant material model.

**P4 — invariance prediction**  
Pure rigid rotation does not trigger material change in the strain-conditioned model.

#### Falsifiers

**F1.** A strong time-invariant material field absorbs the effect to below a practically relevant level.

**F2.** Error does not increase with strain once geometry/normals are exact.

**F3.** Strain conditioning helps only on seen timesteps but not held-out deformation + lighting.

**F4.** Comparable gains are obtained from arbitrary time conditioning and there is no cross-motion/deformation generalization advantage.

If F1 or F2 holds robustly, stop this direction.

---

### Phase 4 — Gate 2: real-material existence check

Synthetic rendering cannot establish that the phenomenon is useful in real capture.

Before implementing the full Gaussian method, perform a small controlled real-material test.

Candidate material classes:

- woven stretch fabric;
- elastic technical fabric;
- skin-like elastomer;
- another material with visible strain-dependent specularity.

The goal is not a paper-quality dataset yet.

Question:

> Can repeated known stretch/compression states produce a repeatable reflectance change above fitting/capture noise?

A minimal setup should prioritize calibration and repeatability over scene complexity.

#### Falsifier

If recovered material variation is not repeatable across trials, is dominated by geometry/normal error, or is too small at realistic strains, stop or reformulate before method development.

---

### Phase 5 — minimal LumiMotion method prototype

Only after Gates 1 and 2 support the premise.

#### Prototype 1: scalar roughness only

Do **not** begin with full anisotropy.

Estimate local deformation state from the canonical/deformed Gaussian neighbourhood and predict:

\[
\alpha_{i,t}
=
\alpha_i^0 + g_\psi(z_i,\epsilon_{i,t}).
\]

Constraints:

- zero-response anchor at rest deformation;
- bounded physically valid roughness;
- no direct timestep input;
- low-capacity response model;
- fixed canonical neighbourhood;
- same model queried under unseen deformation.

This prototype tests the central idea while minimizing method complexity.

#### Essential control

Train a **time-conditioned model with matched capacity**.

If the strain-conditioned model cannot outperform it specifically on held-out motion/deformation generalization, the physics conditioning is not earning its complexity.

---

### Phase 6 — stronger method: anisotropic constitutive appearance

If scalar roughness succeeds, extend to a material frame:

\[
(\mathbf t,\mathbf b,\mathbf n)
\]

and predict anisotropic roughness:

\[
(\alpha_u,\alpha_v)_{i,t}.
\]

The frame must move with the surface while material response depends on stretch/shear in that frame.

This is likely the stronger final paper formulation because deformation is directional and the physical precedent is anisotropic.

Do not implement this before the scalar prototype establishes the core signal.

---

### Phase 7 — final evaluation design

A credible paper should evaluate three distinct generalization axes:

1. **novel view**
2. **novel illumination**
3. **novel deformation**

The third is the key differentiator.

Possible evaluation splits:

- train on one subset of deformation amplitudes, test on held-out amplitudes;
- train on one motion, test on a different motion that reaches overlapping local strain states;
- test extrapolation to larger but physically plausible strain;
- novel environment maps;
- rigid-motion controls.

Baselines should eventually include:

- LumiMotion fixed material;
- DR-GS where comparison is feasible;
- time-conditioned appearance control of matched capacity;
- canonical/static material oracle on synthetic data.

Metrics should include:

- linear-RGB reconstruction/relighting error;
- LPIPS/SSIM/PSNR as secondary image metrics;
- roughness/anisotropy error where GT exists;
- error as a function of strain;
- held-out deformation generalization;
- material-consistency/error maps.

---

## 9. Method design principles to preserve

### Do not condition directly on time

Time is an index, not a physical state.

A time-conditioned network can memorize animation-specific appearance and may fail under a different motion.

### Separate rigid motion from strain

Rotation should change the BRDF frame in world coordinates, but not intrinsic roughness merely because the object rotated.

### Prefer shared response laws

A fully independent MLP per Gaussian would be too expressive and weakens the constitutive interpretation.

A stronger structure is:

\[
\text{canonical material identity}
+
\text{shared/low-dimensional deformation response}.
\]

### Make unseen deformation a first-class evaluation

Without this, reviewers can reasonably interpret the method as a time-varying appearance field.

### Keep the first implementation intentionally small

Scalar roughness → demonstrate signal → then anisotropy/material-frame complexity.

---

## 10. Main risks

### R1 — effect too small

This is the primary risk and the reason Gate 1 comes before method development.

### R2 — deformation estimate is too noisy

Local strain from Gaussians may be unstable even if mesh GT strain is clean.

Mitigation path: establish the phenomenon with GT mesh strain first; then separately measure Gaussian strain-estimation error.

### R3 — geometry/material ambiguity

A changing highlight may be explained by changing normals rather than changing microfacet distribution.

Mandatory mitigation: GT geometry/normal oracle tests.

### R4 — synthetic tautology

A shader we designed will obviously favor a model with the same dependency.

Mitigation: synthetic is only the observability/power gate. Real-material evidence is required before the full method claim.

### R5 — “just condition roughness on deformation”

This is the novelty risk.

The final contribution must include:

- a principled deformation state;
- a constrained constitutive appearance representation;
- held-out deformation generalization;
- evidence that existing time-invariant material models fail;
- ideally anisotropic/material-frame modeling.

### R6 — current LumiMotion scenes may be poor final data

The Mixamo character is useful as infrastructure, but its authored material is fixed and its skeletal deformation is not a controlled cloth simulation.

Do not confuse “convenient sandbox” with “final benchmark.”

---

## 11. Immediate actions

### Action 1 — repository preparation

In the LumiMotion repo:

1. create branch `constitutive-appearance`;
2. copy this document to `docs/CONSTITUTIVE_APPEARANCE_DIRECTION.md`;
3. create `docs/constitutive_code_audit.md`;
4. create `scripts_local/constitutive/`;
5. add a private/gitignored path for Joanna's Blender files;
6. make no training-code changes yet.

### Action 2 — Codex read-only audit

Ask Codex to map the Stage 1/Stage 2 deformation/material pathways and identify the minimal hook for an oracle time-varying roughness field and local deformation-gradient computation.

The audit must cite exact `file:line` and must not edit source.

### Action 3 — decide the first Blender scene

Default candidates:

- `standup150` — large articulated deformation;
- `jumpingjacks` — broad motion;
- `spheres_with_rotations` — negative rigid-motion control.

Do not choose based on which produces the prettiest result. Choose based on measurable strain range after the extractor is validated.

### Action 4 — write Gate 1 preregistration

Freeze:

- material-response law and its literature-grounded magnitude;
- deformation-range definition;
- baseline definition;
- primary statistic;
- threshold;
- predictions;
- falsifiers.

Only then generate the full Gate 1 renders.

---

## 12. What would make this paper-worthy?

The direction becomes genuinely promising if we can establish all of the following:

1. realistic deformation produces a material-response signal above practical noise;
2. a strong time-invariant material model cannot absorb it;
3. the signal survives novel illumination;
4. local strain predicts the change better than arbitrary time;
5. the learned law transfers to unseen deformation/motion;
6. the behavior exists in real material capture;
7. the final Gaussian representation retains enough physical structure to explain *why* it generalizes.

If only (1)–(2) hold, we have a phenomenon but not yet a method paper.

If (1)–(5) hold synthetically but (6) fails, the project is likely too synthetic.

If (1)–(7) hold, the project has a credible top-tier method-paper shape.

---

## 13. Current recommendation

Proceed.

But proceed in this order:

\[
\boxed{
\text{code audit}
\rightarrow
\text{exact strain extraction}
\rightarrow
\text{synthetic signal gate}
\rightarrow
\text{real-material gate}
\rightarrow
\text{minimal LumiMotion prototype}
\rightarrow
\text{anisotropic final model}
}
\]

The next task is **not training**.

The next task is to establish that we can compute the deformation state cleanly and identify exactly where a deformation-conditioned material state would enter LumiMotion.

---

## 14. Living log

### 2026-08-23 — direction selected

- Selected *deformation-conditioned / constitutive appearance* as the primary method direction.
- Chose LumiMotion as the likely method substrate.
- Decided not to modify training until the physical signal gate passes.
- Joanna's Blender drop identified as useful controlled infrastructure, but not evidence of deformation-dependent reflectance.
- Planned rigid-motion and exact-strain controls before any appearance test.
- Final novelty target defined around **unseen deformation generalization**, not merely better reconstruction of seen frames.

---

## 15. References / nearest-neighbour watchlist

- Kaleta et al., **LumiMotion: Improving Gaussian Relighting with Scene Dynamics**, CVPR 2026.
- Li et al., **DR-GS: Physically-Based Deformable and Relightable 2D Gaussians**, ECCV 2026.
- Nagano et al., **Measurement and Modeling of Microfacet Distributions under Deformation**, SIGGRAPH 2014 Talks / USC ICT.
- Matusik et al. and subsequent time-varying BRDF literature — relevant boundary: time-varying reflectance is not itself novel.
- Dynamic/relightable human/volumetric-video methods — monitor for pose-conditioned or strain-conditioned material models.
- Static anisotropic Gaussian inverse-rendering methods — relevant boundary: anisotropic BRDF alone is not novel.

**Literature watch requirement:** before the method implementation begins, repeat a targeted search for any 2025–2026 work explicitly modeling *strain-conditioned*, *deformation-conditioned*, or *pose-conditioned intrinsic BRDF/material parameters* in dynamic inverse rendering.
