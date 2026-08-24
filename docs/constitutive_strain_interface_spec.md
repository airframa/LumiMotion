# Constitutive Appearance — Strain Interface Specification

## 1. Question and scope

**Question.** What deformation-state interface can represent exact strain on an evaluated animated mesh and later estimated strain on fixed canonical Gaussian neighbourhoods, while preserving the same physical invariants and excluding arbitrary time conditioning?

This document is a design contract, not an implementation or experiment. It defines:

- **Path A:** exact reference-relative, face-level surface strain from evaluated animated meshes for controlled physics and signal studies;
- **Path B:** future estimated surface strain from fixed Stage-2 canonical Gaussian neighbourhoods for LumiMotion;
- a shared rotation-invariant descriptor and validity contract;
- validation and provenance requirements that must be satisfied before Joanna's animation strain is inspected or scientifically interpreted.

It does **not** select a strain-to-roughness law, inspect an animation strain distribution, define Gate 1 effect-size thresholds, modify LumiMotion, or authorize Blender execution.

### Status labels

- **VERIFIED:** established by the completed audit or current source.
- **DEFINED BY THIS SPEC:** normative interface requirement for future implementations.
- **PROPOSED:** a candidate implementation choice that remains to be frozen.
- **UNKNOWN:** cannot be established at this specification stage.

## 2. Shared physical contract

### 2.1 Surface deformation, not time or Gaussian scale

**DEFINED BY THIS SPEC.** Both paths represent a local map from one fixed reference surface configuration to a deformed surface configuration. Time/frame may select a configuration but is not an input component of the deformation descriptor. Equal local deformation states must produce equal descriptors even when reached at different frames or by different motions.

**DEFINED BY THIS SPEC.** Each valid local estimate exposes the two ordered in-plane principal stretches

\[
\lambda_{\max} \geq \lambda_{\min} > 0,
\]

obtained as the singular values of a local surface deformation map. Rigid translation cancels through relative coordinates. A rigid rotation left-multiplies the surface map by an orthogonal matrix and therefore leaves both singular values unchanged.

**VERIFIED.** LumiMotion predicts `d_scaling` but hard-zeroes it, and Stage-2 deformed centers are computed independently as `pc.get_xyz + d_xyz` (`utils/time_utils.py:186-204`; `gaussian_renderer/render_ir.py:79-97`). Gaussian scales are two-dimensional surfel support parameters, activated by `exp`, not measured material stretch (`scene/gaussian_model.py:143-153`).

**DEFINED BY THIS SPEC.** Neither `pc.get_scaling` nor `d_scaling` is admissible as physical strain evidence. Path B must estimate deformation from relative motion of fixed canonical center neighbourhoods.

### 2.2 Common invariant descriptor

**DEFINED BY THIS SPEC.** For every valid face or Gaussian center, both paths expose this common scalar tuple in the stated order:

\[
\epsilon =
\left[
\ell_{\max},
\ell_{\min},
\ell_{\mathrm{area}},
\ell_{\mathrm{aniso}}
\right]
=
\left[
\log\lambda_{\max},
\log\lambda_{\min},
\log(\lambda_{\max}\lambda_{\min}),
\log(\lambda_{\max}/\lambda_{\min})
\right].
\]

Thus:

- `log_stretch_max = log(lambda_max)`;
- `log_stretch_min = log(lambda_min)`;
- `log_area_change = log_stretch_max + log_stretch_min`;
- `log_anisotropy = log_stretch_max - log_stretch_min`, nonnegative because stretches are ordered.

The redundant tuple is intentional: the two log stretches are authoritative, while area change and anisotropy are explicit derived invariants for consumers and consistency checks.

**DEFINED BY THIS SPEC.** Identity and rigid motion map to `[0, 0, 0, 0]`. Isotropic expansion has equal positive log stretches and zero log anisotropy. Isotropic compression has equal negative log stretches. The descriptor must preserve the sign of extension/compression in the individual log stretches and area term.

**DEFINED BY THIS SPEC.** Principal direction vectors may be exported for diagnostics and future anisotropy, but their sign, ordering at repeated singular values, and coordinate frame are not part of the shared invariant interface. No constitutive model may depend on them until a material-frame contract is separately established.

### 2.3 Shared record contract

**DEFINED BY THIS SPEC.** Each local record exposes:

- stable local element ID within its frozen source (`face_id` or `gaussian_row`);
- configuration ID and reference-configuration ID;
- `lambda_max`, `lambda_min`;
- the four-component `log_strain` tuple above;
- local reference and deformed area proxies;
- a Boolean `valid` flag;
- a machine-readable invalidity/quality bitmask;
- conditioning diagnostics sufficient to reproduce validity decisions;
- estimator/path name and schema version.

**DEFINED BY THIS SPEC.** Invalid records remain present in row order. They are never silently dropped, clamped into validity, replaced by identity, or included in aggregates. Numeric descriptor fields for invalid records must be `NaN`; reason flags remain populated.

## 3. Path A — exact reference-relative mesh strain

### 3.1 Reference configuration semantics

**DEFINED BY THIS SPEC.** Path A is exact with respect to the chosen reference
configuration and mesh correspondence, but the chosen reference is not assumed
to be a physically stress-free material state. Therefore these quantities are
authoritative reference-relative surface stretches. Claims about absolute
physical/material strain require an independently justified rest configuration.

**DEFINED BY THIS SPEC.** The reference configuration is one explicitly designated, evaluated animation configuration of one explicitly designated mesh object after the complete geometry evaluation stack relevant to rendering. It is not implicitly Blender frame 0, frame 1, bind/rest pose, undeformed datablock coordinates, or the first frame encountered by a loop.

**DEFINED BY THIS SPEC.** The exact scene file, object identity, reference frame/subframe, evaluation mode, modifier state, shape-key state, armature action, object/world transform convention, and Blender binary/version must be frozen in the extraction manifest before evaluating any target configuration.

**UNKNOWN.** The correct reference frame and exact evaluated object(s) for each Joanna scene have not been established without Blender-level inspection. They must not be selected using observed strain magnitude or visual attractiveness.

**DEFINED BY THIS SPEC.** Changing the reference configuration defines a different strain dataset and requires a new manifest/dataset ID. Results from different references may not be pooled as if their log strains shared the same zero state.

### 3.2 Required topology-stability checks

**DEFINED BY THIS SPEC.** Before any strain computation, the evaluated reference mesh and every target configuration must pass all of the following per object:

1. identical vertex count;
2. identical polygon/loop/triangle count after one frozen triangulation convention;
3. identical triangle vertex-index array in identical face order;
4. identical object identity and extraction order;
5. no evaluated topology-generating/remeshing operation that changes correspondence;
6. finite vertex coordinates at every configuration;
7. a recorded hash of the canonical triangle-index array and a recorded hash/checksum of canonical positions.

**DEFINED BY THIS SPEC.** Triangulation must be frozen once in the reference configuration and reused by vertex indices. A target configuration must not be independently triangulated if that could choose different diagonals. If stable reuse is impossible, that object/configuration fails the interface; nearest-surface or spatial rematching is not an acceptable repair for ground truth.

**DEFINED BY THIS SPEC.** Winding must be identical. A winding reversal, reordered vertex array, or reordered face array is a topology/correspondence failure even when geometry appears identical.

**UNKNOWN.** Joanna's evaluated animation topology has not yet been checked. Historical evidence that character scenes are armature-driven does not prove evaluated index stability.

### 3.3 Evaluated-mesh coordinate convention

**DEFINED BY THIS SPEC.** The authoritative positions are evaluated mesh vertices transformed into a single right-handed scene/world coordinate system:

\[
\mathbf X_a = M_0\,\mathbf v^{\mathrm{eval}}_{a,0},
\qquad
\mathbf x_a(t) = M_t\,\mathbf v^{\mathrm{eval}}_{a,t},
\]

where `M_t` is the evaluated object's object-to-world transform at configuration `t`. This includes object-level rigid motion consistently and makes the rigid-motion gate meaningful. Coordinates from undeformed mesh datablocks, armature-local space, camera space, normalized LumiMotion space, and render passes must not be mixed.

**DEFINED BY THIS SPEC.** Units and axis handedness are recorded exactly as exposed by the chosen Blender binary. No per-frame recentering, Procrustes alignment, global rotation removal, normalization to a bounding box, or unit rescaling is applied before face strain. Rigid invariance must arise from the definition, not preprocessing.

**DEFINED BY THIS SPEC.** Object/world matrices and vertex positions are evaluated at the same exact frame/subframe and dependency-graph state. The extraction manifest records frame-to-configuration mapping independently of camera index or JSON `time`.

### 3.4 Triangle-level surface deformation

For reference triangle `f = (a,b,c)`, define reference and target edge matrices:

\[
D_m = [\mathbf X_b-\mathbf X_a\;\;\mathbf X_c-\mathbf X_a] \in \mathbb R^{3\times2},
\qquad
D_s(t) = [\mathbf x_b(t)-\mathbf x_a(t)\;\;\mathbf x_c(t)-\mathbf x_a(t)] \in \mathbb R^{3\times2}.
\]

Choose a deterministic orthonormal reference tangent basis `T_f=[t_1,t_2]` spanning `D_m`: `t_1` follows the normalized first nonzero reference edge and `t_2` completes a right-handed basis with the reference oriented normal. Define reference 2D coordinates

\[
B_f = T_f^\top D_m \in \mathbb R^{2\times2}.
\]

**DEFINED BY THIS SPEC.** For a nondegenerate reference triangle, the authoritative surface deformation map is

\[
F_f(t) = D_s(t) B_f^{-1} \in \mathbb R^{3\times2}.
\]

It maps reference tangent coordinates to target world-space edge vectors. Equivalent QR/SVD solves are permitted numerically; explicit matrix inversion is notation, not an implementation requirement.

The right Cauchy–Green surface tensor is

\[
C_f(t)=F_f(t)^\top F_f(t) \in \mathbb R^{2\times2}.
\]

**DEFINED BY THIS SPEC.** `C_f`, not the world-space orientation of `F_f`, is authoritative for intrinsic strain. Under any target rigid rotation `Q`, `F'_f=QF_f` and `C'_f=C_f`.

### 3.5 Principal stretches and log strain

Let `mu_max >= mu_min >= 0` be the eigenvalues of symmetric `C_f`. Then

\[
\lambda_{\max}=\sqrt{\mu_{\max}},
\qquad
\lambda_{\min}=\sqrt{\mu_{\min}}.
\]

Equivalently, they are the singular values of `F_f`. The common log descriptor is then computed exactly as Section 2.2.

**DEFINED BY THIS SPEC.** Stretch ordering is by value, not by authored axis. For the known uniaxial control, the expected ordered result is approximately `(1.10, 1.00)`. If axis recovery is evaluated, the principal vector corresponding to `lambda_max` must additionally align with the authored stretch direction up to sign; this diagnostic is separate from the invariant gate.

**DEFINED BY THIS SPEC.** Face area change provides a mandatory internal identity:

\[
\frac{A_f(t)}{A_f(0)} = \lambda_{\max}\lambda_{\min}
\]

for valid affine triangles, up to numerical error. Implementations must record both sides and their residual.

### 3.6 Degeneracy and conditioning

**DEFINED BY THIS SPEC.** A face is invalid for a configuration if any of these conditions holds:

- reference or target coordinates are nonfinite;
- reference area is zero or below the preregistered absolute/relative scale criterion;
- `B_f` has insufficient rank or exceeds the frozen condition-number criterion;
- target area is zero/below criterion, so the local map is collapsed or rank deficient;
- either eigenvalue of `C_f` is nonpositive beyond permitted numerical roundoff;
- topology/correspondence checks fail;
- SVD/eigendecomposition fails or outputs nonfinite values.

**DEFINED BY THIS SPEC.** Near-degenerate but computable faces carry conditioning diagnostics and may be excluded only by criteria frozen before inspection of Joanna's animation results. No epsilon, condition-number cutoff, area cutoff, stretch clamp, or winsorization bound may be selected from that distribution.

**DEFINED BY THIS SPEC.** Small negative eigenvalues caused solely by floating-point roundoff may be projected to zero only under a frozen relative tolerance and must be counted/flagged. A materially negative eigenvalue is an error, not a clamp case. Since log strain requires strictly positive stretches, a projected-zero face remains invalid.

**PROPOSED.** Compute extraction and validation in float64. The eventual storage dtype may remain float64 for authoritative archives; any float32 derivative must be explicitly labeled and checked against it.

### 3.7 Authoritative face-level outputs

**DEFINED BY THIS SPEC.** Face-level results are ground truth. For `F` faces and `T` target configurations, the authoritative arrays are:

- `triangles [F,3] int64`: canonical vertex indices;
- `reference_positions [V,3] float64`;
- `positions [T,V,3] float64` or per-frame equivalent files;
- `F_surface [T,F,3,2] float64` (optional to omit only if exactly reproducible from archived positions/basis);
- `C_surface [T,F,2,2] float64` (same reproducibility rule);
- `lambda_max [T,F]`, `lambda_min [T,F]`;
- `log_strain [T,F,4]` in Section 2.2 order;
- `area_reference [F]`, `area_deformed [T,F]`, `area_ratio [T,F]`;
- `condition_number_reference [F]` and any target quality measures;
- `valid [T,F] bool` and `invalid_reason [T,F] uint32`;
- optional reference/target geometric normals and principal directions, labeled diagnostic rather than invariant material frames.

**DEFINED BY THIS SPEC.** Face IDs are canonical triangle row indices and remain fixed across all configurations in one dataset. All summaries, visualizations, and downstream mappings must preserve access to the authoritative face rows and validity flags.

### 3.8 Optional face-to-vertex aggregation

**DEFINED BY THIS SPEC.** Vertex strain is a derived convenience view, never ground truth. It must be stored separately and labeled with `derived_from=face_ground_truth` plus the aggregation method.

**PROPOSED.** If required, aggregate only valid incident faces using frozen nonnegative weights (for example canonical face area or corner angle). Aggregate `log_stretch_max` and `log_stretch_min` in log space, then recompute `lambda` and derived invariants. Do not average principal direction vectors without a separately defined sign/frame transport procedure.

**DEFINED BY THIS SPEC.** The aggregation exports weight sum, number of valid incident faces, and a vertex-valid flag. Boundary vertices and vertices with insufficient valid support must be identifiable. No aggregation choice may be tuned using appearance results.

### 3.9 Mesh output package and manifest

**DEFINED BY THIS SPEC.** The proposed portable package is immutable numeric data plus a UTF-8 JSON manifest:

```text
<dataset_id>/
├── manifest.json
├── reference.npz
├── frame_<configuration_id>.npz
└── vertex_derived/                 # optional, clearly non-authoritative
```

`reference.npz` contains topology, canonical world positions, reference bases/areas, and reference quality values. Each frame file contains target positions, face strain outputs, validity flags, and diagnostics in canonical row order. NPZ is an interchange choice, not permission to package or redistribute the source `.blend` assets.

**DEFINED BY THIS SPEC.** `manifest.json` records at minimum:

- schema name/version and dataset ID;
- extractor code revision/commit and command line;
- creation timestamp and numeric library versions;
- absolute source path in a private local field or a redacted stable asset ID for shareable manifests;
- source file size and cryptographic hash without embedding asset content;
- Blender binary absolute path, version, build hash, and platform;
- scene, view layer, evaluated object names and stable extraction order;
- reference frame/subframe and all target configuration IDs;
- object-to-world convention, units, axes, handedness, and matrix convention;
- modifier/evaluation/triangulation policy;
- counts and hashes for vertices and triangle indices;
- dtype and all frozen validity/conditioning tolerances;
- descriptor order and units;
- validation-suite version and pass/fail summary;
- explicit `authoritative_level: face`;
- any exclusions with reason, never just an omitted object/frame list.

## 4. Path B — future Gaussian-estimated strain

### 4.1 Checkpoint-local identity

**VERIFIED.** Stage 1 changes topology through densification, splitting, and pruning (`scene/gaussian_model.py:442-477`; `scene/gaussian_model.py:479-602`; `scripts/train_stage1.py:229-241`). After a selected Stage-1 PLY is loaded, Stage 2 fixes `N`, removes geometry/feature groups from its optimizer, and performs no densification (`scripts/train_stage2.py:61-98`). PLY serialization has no persistent semantic Gaussian ID (`scene/gaussian_model.py:289-340`).

**DEFINED BY THIS SPEC.** A Gaussian strain package is valid only for one exact loaded Stage-1 checkpoint. Its identity key must include:

- canonical PLY path, iteration, file size, and cryptographic hash;
- deformation checkpoint path/iteration and hash;
- model/config identity required to reproduce canonical coordinates and `d_xyz`;
- canonical row count `N`;
- hash of canonical xyz bytes in documented dtype/order;
- row-order/schema version.

Any mismatch invalidates the neighbour graph and all derived strain. Graph transfer between checkpoints, even when `N` matches, is forbidden without an explicit verified row correspondence.

### 4.2 Graph construction time and invariance

**VERIFIED.** Current code has no stored neighbour-index graph. `distCUDA2` is used only during initialization to obtain nearest-neighbour distance for scale initialization (`scene/gaussian_model.py:23`; `scene/gaussian_model.py:219-239`). Canonical and deformed centers coexist at the Stage-2/render seam (`scripts/train_stage2.py:142-168`; `gaussian_renderer/render_ir.py:79-97`).

**DEFINED BY THIS SPEC.** The canonical neighbour graph is built exactly once:

1. after the exact Stage-1 PLY and deformation checkpoint have been loaded;
2. after canonical xyz row order has been hashed;
3. before any Stage-2 material optimization or per-frame strain query;
4. using canonical centers only.

It remains immutable across time, camera, illumination, train/eval split, and material optimization. It must never be recomputed, filtered, or reordered from deformed positions.

### 4.3 Required neighbourhood data

**DEFINED BY THIS SPEC.** For each center `i`, the graph package stores:

- `center_row = i`;
- ordered neighbour row indices `J_i`, excluding `i`;
- canonical relative offsets `X_j-X_i` or a reproducible reference to canonical xyz;
- fixed nonnegative weights or all inputs and the exact rule needed to reproduce them;
- canonical local tangent basis `T_i in R^{3x2}` and unoriented normal line, or inputs needed to reproduce them bit-for-bit;
- canonical projected coordinates `q_ij = T_i^T(X_j-X_i)`;
- reference covariance/normal matrix, singular values, rank, condition number, support radius, and validity flags;
- graph method/version and all hyperparameters;
- graph/checkpoint hashes.

**PROPOSED.** Estimate the canonical tangent plane by weighted PCA of fixed canonical relative offsets. Treat the normal as an unoriented line for scalar invariant strain; do not use camera-facing normal flips. The tracer currently view-flips normals (`scene/gaussian_model.py:648-658`), so those normals are inadmissible as canonical material-frame input.

**PROPOSED.** Candidate graph constructions include fixed-`k` kNN, radius support with minimum/maximum neighbours, or a hybrid. The exact method, `k`/radius, weights, static/dynamic filtering policy, and boundary policy must be frozen before implementation validation and may not be chosen from Joanna strain or appearance distributions.

### 4.4 Surface-local least-squares deformation

Let canonical and deformed centers be

\[
\mathbf X_i = \texttt{pc.get_xyz}_i,
\qquad
\mathbf x_i(t)=\mathbf X_i+\mathbf d_i(t).
\]

For each fixed neighbour `j in J_i`, define canonical tangent coordinate and deformed relative offset

\[
\mathbf q_{ij}=T_i^\top(\mathbf X_j-\mathbf X_i)\in\mathbb R^2,
\qquad
\mathbf y_{ij}(t)=\mathbf x_j(t)-\mathbf x_i(t)\in\mathbb R^3.
\]

**DEFINED BY THIS SPEC.** Estimate the surface map `A_i(t) in R^{3x2}` by weighted least squares:

\[
A_i(t)=\arg\min_A\sum_{j\in J_i}w_{ij}\|\mathbf y_{ij}(t)-A\mathbf q_{ij}\|_2^2.
\]

Use the identical solve on the canonical offsets to obtain

\[
A_i(0)=\arg\min_A\sum_{j\in J_i}w_{ij}
\|(\mathbf X_j-\mathbf X_i)-A\mathbf q_{ij}\|_2^2.
\]

The fitted reference and target metrics are

\[
G_i(0)=A_i(0)^\top A_i(0),
\qquad
G_i(t)=A_i(t)^\top A_i(t).
\]

**DEFINED BY THIS SPEC.** The squared principal stretches are the ordered generalized eigenvalues `mu` of

\[
G_i(t)\mathbf v=\mu\,G_i(0)\mathbf v,
\]

equivalently the eigenvalues of the symmetrically whitened relative metric

\[
C_i^{\mathrm{rel}}(t)=G_i(0)^{-1/2}G_i(t)G_i(0)^{-1/2}.
\]

The square roots of those eigenvalues define `lambda_max`, `lambda_min`, and the exact shared log descriptor from Section 2.2. Solves must use stable symmetric factorizations; the inverse square-root notation does not require forming an explicit inverse.

**DEFINED BY THIS SPEC.** The Gaussian reference/deformed area proxies are `sqrt(det(G_i(0)))` and `sqrt(det(G_i(t)))`; their ratio must equal `lambda_max*lambda_min` up to numerical error. They are local fitted-support measures, not literal mesh-face areas, and must be labeled accordingly.

**DEFINED BY THIS SPEC.** The solve uses relative offsets centered on row `i`, making it translation invariant. For identity, `A_i(t)=A_i(0)` and therefore `C_i^{rel}=I`. Under an exact rigid transform, `A_i(t)=R A_i(0)`, so `G_i(t)=G_i(0)`, `C_i^{rel}=I`, and both stretches equal one. This reference-metric normalization is mandatory: it preserves the invariants even when a curved/noisy canonical neighbourhood is not represented exactly by its two-dimensional tangent projection.

**PROPOSED.** A centered affine fit with an explicit intercept may be compared during implementation validation, but only one estimator may become authoritative. It must satisfy the same gates and retain fixed row correspondence. Robust reweighting based on deformed residuals is deferred because it can make the effective neighbourhood time-dependent.

### 4.5 Gaussian conditioning and validity

**DEFINED BY THIS SPEC.** Gaussian records use the same validity principles as faces, adapted to neighbourhood fitting. A center is invalid if:

- checkpoint/xyz/graph identity does not match;
- any referenced row is absent or reordered;
- neighbour indices are duplicated, include the center unexpectedly, or are out of range;
- canonical support has insufficient samples or rank below two;
- the weighted canonical normal matrix is singular or exceeds the frozen condition-number criterion;
- canonical or deformed coordinates are nonfinite;
- the fitted map is rank deficient/collapsed;
- `G_i(0)`, `G_i(t)`, or `C_i^{rel}` is not finite positive definite within the frozen numerical tolerance;
- residual or leverage diagnostics violate a criterion frozen before Joanna analysis.

**DEFINED BY THIS SPEC.** Invalid centers remain in `[N]` row order with `NaN` descriptors and explicit reason bits. No deformed-space neighbour replacement is allowed.

**UNKNOWN.** Learned Gaussian clouds may not be locally planar or uniformly sample the physical surface; neighbourhoods may cross nearby but materially disconnected surface sheets, joints, clothing layers, or static/dynamic boundaries. These are estimator limitations to measure after validation, not grounds for silent post-hoc filtering.

### 4.6 Compatibility and non-equivalence to mesh ground truth

**DEFINED BY THIS SPEC.** Mesh and Gaussian paths share the semantic fields and invariant formulas:

```text
lambda_max
lambda_min
log_stretch_max
log_stretch_min
log_area_change
log_anisotropy
valid / invalid_reason / conditioning diagnostics
```

The mesh path estimates an exact piecewise-affine map from known triangle correspondence. The Gaussian path estimates a best-fit local map from learned centers. Equal field names mean equal physical interpretation, not equal accuracy or spatial support.

**DEFINED BY THIS SPEC.** Gaussian estimates may be compared to mesh ground truth only through an explicitly defined spatial association/mapping with its own coverage and uncertainty report. Gaussian row `i` is not assumed to correspond to a mesh face or vertex.

**UNKNOWN.** Whether Gaussian neighbourhood stretch is accurate enough for the learned method, and how it varies with sampling density and deformation-network error, requires future validated measurement.

### 4.7 Material-frame limitation

**VERIFIED.** LumiMotion stores no tangent, bitangent, UV, or intrinsic material axis, and its current GGX is isotropic (`scene/gaussian_model.py:60-75`; `scene/gaussian_model.py:289-340`; `gaussian_renderer/render_ir.py:581-614`). Quaternion deformation is additive in raw coefficients followed by normalization, not a physical deformation gradient (`scene/gaussian_model.py:147-153`).

**DEFINED BY THIS SPEC.** Path B's PCA tangent basis is only a geometric coordinate device for computing rotation-invariant singular values. It is not an intrinsic material frame and must not define anisotropic roughness axes.

**UNKNOWN.** A future anisotropic method needs a stable, oriented material tangent frame with a transport rule, sign/axis disambiguation, serialization, and correspondence to any mesh-side material directions. That is outside the scalar interface and intentionally unresolved.

## 5. Mandatory numerical validation gates

These gates apply before inspecting Joanna's animation strain distribution. They must be run on deliberately constructed inputs whose expected deformation is known independently of the extractor.

### 5.1 Identity

**DEFINED BY THIS SPEC.** Feed the identical geometry/centers as reference and target, preserving the same topology/row order.

Expected for every valid local element:

\[
\lambda_{\max}=1,\qquad\lambda_{\min}=1,
\qquad\epsilon=[0,0,0,0]
\]

within a preregistered numerical tolerance. This gate must exercise the complete export/load/compute path, not only an isolated formula.

### 5.2 Rigid transformation

**DEFINED BY THIS SPEC.** Apply a known nontrivial 3D rotation and translation to all target positions without changing topology/row order or neighbourhoods. Use more than one rotation axis and a nonzero translation in the validation suite.

Expected for every valid local element:

\[
\lambda_{\max}=1,\qquad\lambda_{\min}=1,
\qquad\epsilon=[0,0,0,0].
\]

The test fails if a pre-alignment step is required to obtain this result.

### 5.3 Known uniaxial stretch

**DEFINED BY THIS SPEC.** Use a planar patch with a known authored in-plane deformation `diag(1.10, 1.00)`, with sufficient nondegenerate triangles/neighbour support. Test it without and with a subsequent arbitrary rigid rotation/translation.

Expected ordered stretches:

\[
\lambda_{\max}\approx1.10,\qquad\lambda_{\min}\approx1.00,
\]

and expected invariants:

\[
\log\_area\_change\approx\log(1.10),
\qquad
\log\_anisotropy\approx\log(1.10).
\]

If principal directions are exported, the maximum-stretch direction must align with the authored axis up to sign before the optional subsequent rigid transform, and rotate with that transform afterward.

### 5.4 Gate protocol

**DEFINED BY THIS SPEC.** Before validation results are generated, freeze:

- numeric dtype;
- test geometry and exact transforms;
- per-element and aggregate error statistics;
- absolute/relative tolerances and pass/fail thresholds;
- allowed invalid count/fraction;
- degeneracy fixtures that must be rejected;
- software/version manifest.

Thresholds must be based on floating-point/numerical requirements and controlled-fixture scale, not observed Joanna outputs. All three positive gates and the planned degeneracy rejection fixtures must pass before any real animation frame distribution is computed.

**DEFINED BY THIS SPEC.** Path A and Path B run the same identity, rigid, and uniaxial fixtures wherever their input structures permit. A pass by one path does not waive failure by the other.

## 6. Interface hazards and explicit exclusions

- **DEFINED BY THIS SPEC:** no direct frame/time value is included in `epsilon`; frame IDs are provenance only.
- **DEFINED BY THIS SPEC:** no per-frame Procrustes alignment is permitted; it could hide correspondence or coordinate errors.
- **DEFINED BY THIS SPEC:** no use of Gaussian scale, scale ratio, `d_scaling`, rotation magnitude, or normal angle as a strain proxy.
- **DEFINED BY THIS SPEC:** no deformed-space kNN and no time-varying neighbour replacement.
- **DEFINED BY THIS SPEC:** no silent clamp of extreme stretches. Invalid/ill-conditioned estimates are flagged; valid extreme values remain values until a preregistered analysis exclusion says otherwise.
- **DEFINED BY THIS SPEC:** no face-to-vertex or mesh-to-Gaussian interpolation is called ground truth.
- **DEFINED BY THIS SPEC:** no view-dependent normal flip may establish an intrinsic tangent/material frame.
- **VERIFIED:** Stage-2 deformation is evaluated under `torch.no_grad()` and canonical/deformed centers coexist before rasterization (`scripts/train_stage2.py:142-168`; `gaussian_renderer/render_ir.py:79-101`). This is compatible with a fixed strain input, but a future differentiability decision must be explicit.
- **VERIFIED:** dynamic NVS and relighting evaluation retain a stale first-frame BVH (`scripts/eval_nvs_dynamic.py:69-95`; `scripts/eval_relight_dynamic.py:80-107`). Strain extraction itself does not use the BVH, but no future image-space result may depend on those paths without an explicit scoped correction/control.

## 7. Specification provenance

**DEFINED BY THIS SPEC.** This document was prepared from `AGENTS.md`, `docs/CONSTITUTIVE_APPEARANCE_DIRECTION.md`, and `docs/constitutive_code_audit.md` on branch `constitutive-appearance`. No Blender file, animation strain distribution, render, training job, GPU job, or extractor implementation was accessed or run.

Read-only commands used before writing were `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git status --short`, `wc -l`, and `sed -n`.

## 8. Decisions that must be frozen before implementation

1. The Path-A extractor must be asset-independent. Before the first extraction
   from Joanna's assets, freeze the exact source asset ID, evaluated object
   set/order, and reference frame/subframe without inspecting strain magnitude.
2. Blender binary/version/build and dependency-graph evaluation procedure.
3. World-coordinate, units, handedness, matrix, and triangulation conventions.
4. Topology hashes and exact failure policy for any object/configuration mismatch.
5. Numeric dtype and stable linear-algebra routines.
6. Reference/target degeneracy, area, rank, conditioning, eigenvalue, residual, and validity criteria.
7. Invalid-reason bit assignments and schema version.
8. Authoritative file layout, array names/shapes/dtypes, hash algorithm, and manifest schema.
9. Exact controlled identity, rigid, uniaxial, and degeneracy fixtures; primary validation statistics and pass/fail tolerances.
10. Exact Stage-1 PLY and deformation checkpoint identity for Path B, including byte and canonical-xyz hashes.
11. Canonical graph construction method, `k`/radius, weights, boundary/static-dynamic policy, tie-breaking, and neighbour ordering.
12. Canonical tangent-plane estimator, orientation treatment, least-squares formulation, and quality diagnostics.
13. Whether authoritative Path-B computation is offline/precomputed or on-demand at the shared `render_ir` seam; this must not alter descriptor semantics.
14. Whether strain tensors are detached or differentiable in the eventual method; geometry/deformation must remain controlled for the oracle stage.
15. Versioned spatial association procedure and coverage metrics for any mesh-to-Gaussian accuracy comparison.

## 9. Decisions intentionally deferred until Gate 1 preregistration

1. Any mapping from strain, stretch, area change, or anisotropy to roughness or another BRDF parameter.
2. Which subset/order/normalization of the shared invariant tuple a constitutive model consumes.
3. Constitutive-law capacity, parameter sharing, material code `z_i`, regularization, zero-response anchor, and physical bounds.
4. Literature-grounded magnitude and sign of the synthetic material response.
5. Which Joanna scene, animation frames, strain ranges, camera views, and illuminations enter Gate 1 after extractor validation and deformation-regime measurement.
6. Primary appearance statistic, practical effect-size threshold, kill criterion, controls, exclusions, and analysis convention.
7. Definition and fitting procedure for the strongest time-invariant material oracle and matched-capacity time-conditioned control.
8. Handling of LumiMotion's time-conditioned Stage-1 shadow/radiance compensation in future image experiments.
9. Unified propagation of a future oracle material field through primary rasterization and secondary traced material features.
10. Scoped correction/control of the stale dynamic-evaluation BVH before quantitative dynamic image comparisons.
11. Any anisotropic BRDF, intrinsic material tangent frame, material-frame transport, or directional constitutive response.
12. Any empirical clipping, normalization, binning, or sampling based on a validated Joanna strain distribution.
