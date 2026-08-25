# Constitutive Appearance — Independent Material-Response Calibration Protocol

**Status:** Frozen protocol before quantitative material-response extraction  
**Phase:** Independent material-response calibration  
**Not Gate 1:** No appearance rendering, image-observability test, or constitutive-law implementation is authorized here

## 1. Question

**QUESTION.** What deformation-dependent reflectance response is independently
supported by physical/material measurements over deformation states relevant to
the measured Joanna deformation regime?

**FROZEN BY THIS PROTOCOL.** The calibration must establish whether there is an
independently defensible physical material response worth placing into the later
synthetic signal gate. It must not choose evidence because it produces a desired
image effect, and it must not use Gate-1 rendering to select, amplify, or repair
the response.

**VERIFIED PROJECT FACT.** The Joanna animations contain nontrivial localized
reference-relative surface deformation, including extension and compression
tails, so a later signal test has deformation support
(`docs/constitutive_deformation_regime_results.md:33-62`). This establishes
available deformation states only. It does not establish stress-free physical
strain, material realism, deformation-dependent reflectance, or observability
(`docs/constitutive_deformation_regime_results.md:64-74`).

**VERIFIED PROJECT FACT.** The retained deformation characterization is
cross-version validated: Blender 3.6.13 and 4.4.0 produced identical evaluated
world-space geometry and Path-A strain summaries for the frozen population
(`docs/constitutive_blender_version_fidelity_results.md:37-66`). The geometry
instrument is therefore accepted for domain matching; this result says nothing
about shader or render equivalence (`docs/constitutive_blender_version_fidelity_results.md:68-81`).

## 2. Scope and non-goals

This protocol governs a later literature/data-evidence calibration. It freezes:

- what constitutes a candidate evidence record;
- the evidence hierarchy and minimum sufficiency conditions;
- how candidate materials are selected;
- how deformation coordinates are compared with Joanna's measured support;
- how scalar versus anisotropic response is decided;
- what must be reported before Gate 1 can be preregistered.

It does **not**:

- select a material class, paper, dataset, deformation descriptor, BRDF model,
  response law, interpolation, lookup table, or parameter magnitude;
- extract or digitize a quantitative response;
- download an external dataset;
- establish that a physical response is visible in images;
- authorize Gate-1 rendering;
- implement Path B, material frames, deformation-conditioned roughness, or any
  LumiMotion source change.

An admissible outcome of the later calibration is **insufficient independent
evidence**. In that case, no synthetic response law is authorized merely to keep
the project moving.

## 3. Unit of evidence and required extraction record

### 3.1 Evidence unit

**FROZEN.** One evidence record is one identifiable material sample or sample
class under one reported deformation/loading protocol and one optical
measurement protocol. Multiple plots from the same specimens and apparatus are
linked records, not independent corroborations. Multiple papers reusing the
same underlying data are one evidence family.

Each record receives a stable `evidence_id`, a source-family ID, an evidence
grade from Section 4, and one of:

```text
eligible_primary
eligible_corroborative
qualitative_only
excluded
unresolved
```

No record is omitted because its response is weak, null, opposite in sign,
non-monotonic, hysteretic, or inconvenient for GGX. Null and contradictory
measurements remain in the matrix.

### 3.2 Required fields for every candidate source/material

**FROZEN.** Eventually extract and report all of the following. An unavailable
field is recorded as `not reported` or `cannot determine`, never silently
inferred.

1. **Citation and provenance**
   - exact bibliographic citation, DOI/stable identifier, and precise
     page/section/figure/table/dataset location;
   - whether values are reported numerically, obtained from author data, or
     digitized from a figure;
   - extraction method, units, conversions, and any transcription/digitization
     uncertainty;
   - source-family relationships and whether corroboration is genuinely
     independent.
2. **Material identity**
   - material class and exact sample/specimen description;
   - composition, construction, weave/fiber direction, surface preparation,
     thickness, hydration, coating, preconditioning, or other reported state
     relevant to mechanics or optics;
   - number of material samples/specimens and whether results are sample-specific
     or pooled.
3. **Evidence origin**
   - measured, simulated, or hybrid;
   - apparatus or simulation model;
   - whether a simulation is independently calibrated to measurements from the
     same material and deformation domain.
4. **Deformation definition**
   - exact deformation variable: stretch ratio, engineering strain, true/log
     strain, principal stretches, area ratio, deformation gradient, stress,
     displacement, bend, or another quantity;
   - reference/rest convention and whether the reference is claimed stress-free;
   - deformation range and sample points;
   - loading direction(s), biaxial/uniaxial condition, transverse constraint or
     measured transverse response, shear, compression/tension convention, and
     strain rate if reported;
   - load/unload ordering, precycles, and whether deformation is controlled by
     force, displacement, or another variable.
5. **Optical quantity actually measured**
   - BRDF;
   - microfacet or normal distribution function (NDF);
   - surface-normal/slope distribution;
   - specular reflectance;
   - diffuse reflectance;
   - displacement or microgeometry;
   - or another explicitly named quantity;
   - spectral bands/wavelengths, polarization, incident/view angle coverage,
     illumination, and normalization convention where available.
6. **Response**
   - quantitative response magnitude at each supported deformation state, in
     the source quantity before any renderer mapping;
   - sign under stretch and compression separately;
   - monotonic, non-monotonic, thresholded, saturating, discontinuous, or null
     behavior;
   - directional/anisotropic response, including axes and how they relate to
     loading and material directions;
   - repeatability, specimen/trial count, within- and between-sample variation;
   - uncertainty, confidence intervals, error bars, calibration error, or an
     explicit statement that none is available;
   - hysteresis, residual change, rate dependence, path dependence, and
     reversibility if reported.
7. **Confounds and intrinsic-status assessment**
   - whether the reported change is an intrinsic scattering/microgeometry
     response or is entangled with macrogeometry, changing normals, shadowing,
     porosity, fabric openings, background visibility, thickness, projected
     area, illumination, exposure, camera response, or other capture effects;
   - controls used to separate those effects;
   - which interpretation is directly supported and which is inferred.
8. **Renderer mapping and domain**
   - whether and how the measured quantity can be mapped to a microfacet/GGX or
     other renderer parameterization;
   - mapping assumptions, fit objective, angular/spectral domain, parameter
     convention, fit residuals, identifiability, and uncertainty propagation;
   - supported interpolation domain;
   - unsupported extrapolation domain;
   - deformation coordinates that remain unknown after mapping.

## 4. Frozen evidence hierarchy

### Grade A — direct optical distribution evidence

Direct measured BRDF, or an NDF/microfacet distribution recovered from direct
optical-scattering measurements, under known deformation.

### Grade B — measured microgeometry with physical optical mapping

Surface height, slope, normal, or microgeometry distributions measured
geometrically (for example by profilometry, microscopy, photometric surface
measurement, or equivalent) under known deformation, followed by an explicit
physical mapping to optical scattering.

### Grade C — direct reflection response without full decomposition

Direct optical/specular/reflection response measured under known deformation,
but without sufficient angular decomposition to recover a BRDF/NDF or uniquely
identify roughness. Grade C is corroborative. It may support sign, existence,
or scale of an optical effect but is not sufficient alone to define the primary
constitutive law.

### Grade D — entangled visible/color appearance

Visible or color appearance change in which geometry, openings/background,
illumination, projected area, camera response, or other effects are entangled.
Grade D is qualitative/corroborative only and cannot set a quantitative law.

### Synthetic/procedural evidence

Synthetic, procedural, or purely simulated appearance behavior is not primary
evidence unless its material response is independently calibrated to Grade A or
B measurements over the relevant deformation domain. A simulation may explain
or interpolate measurements, but an uncalibrated simulation does not establish
that the physical response exists or has the simulated magnitude.

## 5. Minimum evidence sufficient to authorize a Gate-1 law

**FROZEN SUFFICIENCY CONDITIONS.** A later calibration may recommend a material
response for Gate 1 only when all conditions below hold:

1. At least one eligible Grade A record, or one eligible Grade B record with a
   documented and physically justified optical mapping, quantitatively supports
   deformation-dependent response.
2. The evidence identifies the material, deformation variable, reference
   convention, numerical deformation range, optical quantity, and quantitative
   response magnitude. Unknown deformation axes/ranges are disqualifying for
   primary calibration.
3. The relationship between the source deformation domain and Joanna's measured
   deformation support must be stated without inventing a stress-free
   correspondence.

   A Gate-1 law may use Joanna deformation directly only if either:

   a. the source response is defined in compatible reference-relative deformation
      coordinates; or

   b. an independently justified correspondence exists between the source
      reference/rest state and Joanna's frozen reference configuration.

   If neither holds, Joanna may be used only to show that comparable deformation
   excursions exist. The later Gate 1 must then use a source-defined controlled
   synthetic deformation/reference state rather than pretending that Joanna's
   lambda = 1 is the source material's stress-free state.

   This limitation is not repaired by shifting, rescaling, or fitting the source
   law to Joanna after observing image effects.
4. A renderer representation can reproduce the supported measured quantity with
   reported fit residual/error, or the later Gate 1 uses the measured quantity
   through a lookup/representation that does not pretend an unsupported GGX fit.
5. Scalar-versus-anisotropic disposition is resolved under Section 7. An
   unavailable material tangent frame cannot be hidden by relabeling a
   directional response as scalar.
6. Measurement uncertainty, sample variability, confounds, and unsupported
   extrapolation are recorded. The selected magnitude may not exceed the
   measurement-supported range to increase image visibility.
7. Conflicting eligible evidence is retained and reconciled by material/sample,
   deformation, optical protocol, and uncertainty. It may not be discarded
   solely because it weakens the response.

**FROZEN.** Grade C or D evidence may corroborate an eligible Grade A/B
calibration but cannot rescue the absence of Grade A/B support. Authored curves,
uncalibrated simulations, or Joanna's Blender materials cannot fill a missing
primary evidence requirement.

**FROZEN.** Independent corroboration is desirable and must be sought and
reported, but is not fabricated by counting multiple publications from one
data family. If only one eligible A/B source exists, the calibration must label
the resulting law `single-source` and carry that limitation into Gate 1.

## 6. Candidate discovery and evidence review procedure

**FROZEN.** The later review begins material-agnostically. It must search across
deformable material classes and optical measurement terminology rather than
starting with cloth, skin, elastomer, or another convenient scene material.
Search and screening records must preserve:

- databases/indexes and exact query strings;
- search date and coverage limits;
- title/abstract candidates;
- full-text candidates available for review;
- inclusion/exclusion decision and reason;
- duplicate and shared-data-family links;
- follow-up citations found by backward/forward chaining.

The review must include terminology spanning deformation/stretch/compression,
BRDF/scattering/specular response, NDF/microfacet/surface slopes/normals, and
microgeometry. Search order cannot be modified after seeing a promising effect
to suppress competing material classes or null results.

This protocol does not authorize downloading external datasets. Any later need
for bulk or restricted data acquisition requires separate authorization and
provenance handling. Quantitative extraction may use legitimately available
reported tables, figures, and supplementary values, with the extraction method
recorded.

### 6.1 Frozen review stages and stopping rule

The review proceeds in two stages.

#### Stage A — discovery and screening

Run the complete predeclared query family across every selected search/index
channel before quantitative effect-size extraction begins.

Record all plausible candidates, including null, weak, contradictory, and
confounded results.

For every candidate Grade-A/B source family, perform:

- backward citation chaining;
- forward citation chaining where available.

Perform at least two chaining rounds unless a branch terminates earlier.

Discovery stops only after:

1. every predeclared search-query family has been executed;
2. every selected search/index channel has been covered;
3. required backward/forward chaining has been completed for all provisional
   Grade-A/B families; and
4. one final saturation search/chaining round produces no new eligible Grade-A/B
   evidence family.

The stopping rule cannot depend on whether the currently identified material
response is large, small, favorable, unfavorable, scalar, or anisotropic.

#### Stage B — quantitative extraction

Only after Stage-A discovery/screening is frozen may quantitative material-
response values be extracted or digitized from the eligible candidate set.

Per-source extraction rules remain governed by Section 10.

## 7. Material-selection and scalar-versus-anisotropic rules

### 7.1 Material-selection rule

**FROZEN.** Do not preselect cloth, skin, elastomer, or any other material
because it is convenient, visually attractive, already present in Blender, or
expected to yield a large image-space effect.

The primary Gate-1 material is the material class with the strongest
quantitative deformation-to-reflectance evidence that:

1. ranks highest under the hierarchy and sufficiency conditions above;
2. overlaps the measured Joanna deformation domain in compatible coordinates;
3. requires no unjustified extrapolation;
4. has the clearest intrinsic-versus-confounded interpretation;
5. can be represented faithfully enough for a controlled signal gate; and
6. has uncertainty and repeatability adequate to state a defensible response
   range.

Selection must be documented as a comparison across all eligible candidates,
not as a narrative about only the winner. Response magnitude is reported, but
the candidate is not selected merely because it gives the strongest desired
rendering effect. If evidence quality and domain compatibility do not identify
a defensible primary material, the result is insufficient evidence.

### 7.2 Scalar-versus-anisotropic decision

**FROZEN.** Do not assume scalar roughness. For each eligible A/B source, the
calibration must determine whether the measurements support:

```text
a. meaningful deformation-dependent isotropic/mean roughness change;
b. predominantly directional anisotropic roughness change;
c. both isotropic/mean and directional components;
d. cannot determine from the available measurement.
```

Where directional measurements permit, report the deformation response of both
principal optical axes and a mean/isotropic component separately. State the
axis convention, relationship to loading/material directions, and uncertainty.
If reducing an anisotropic distribution to a scalar, freeze and justify the
reduction from the measured quantity—such as a declared fit to an isotropic
NDF—not from rendered appearance. Report the residual and the directional
response lost by the reduction.

A scalar first Gate 1 is allowed only when the independent data support a
nontrivial isotropic/mean roughness response or a clearly justified scalar
reduction that retains the measured deformation-dependent effect within its
uncertainty. If the effect is fundamentally anisotropic and scalar reduction
removes most of it, the calibration must recommend revising the scalar-first
plan. It must not force anisotropic evidence into scalar roughness.

**VERIFIED PROJECT LIMITATION.** The current shared strain descriptor contains
rotation-invariant stretches but its principal directions are not a stable
material frame (`docs/constitutive_strain_interface_spec.md:41-73`). LumiMotion
also lacks an intrinsic tangent/material frame for future Path B. A required
directional law therefore implies an explicit material-frame prerequisite; it
is not silently implementable through the present scalar interface.

## 8. Deformation-domain matching to Joanna

### 8.1 Compatible coordinates

**FROZEN.** Joanna's characterization may be used only to assess domain overlap.
The authoritative common invariants are:

```text
lambda_max
lambda_min
log_stretch_max = log(lambda_max)
log_stretch_min = log(lambda_min)
log_area_change = log(lambda_max * lambda_min)
log_anisotropy = log(lambda_max / lambda_min)
```

These definitions are fixed by the strain interface
(`docs/constitutive_strain_interface_spec.md:29-71`). For every supported
material law, eventually report which numerical portions/ranges of
`lambda_max`, `lambda_min`, `log_area_change`, and `log_anisotropy` are
physically in-domain.

### 8.2 Conversion rules

Conversions from source deformation variables must be explicit:

- engineering strain may map to stretch ratio as `lambda = 1 + e` only when the
  source's strain convention supports that conversion;
- true/log strain may map as `lambda = exp(e_log)` only when its reference and
  axis match;
- a reported loading-axis stretch does not determine transverse stretch, area
  change, or anisotropy unless those quantities are measured or constrained by
  a stated mechanical model;
- stress, force, actuator displacement, bend angle, and nominal sample extension
  are not silently converted to local surface stretch;
- uniaxial evidence does not establish a biaxial/shear response outside its
  loading path;
- tension measurements do not establish compression response, and vice versa;
- a material-axis directional law is not matched using ordered principal
  stretches alone unless the material/loading-axis correspondence is known.

Every conversion records the original values, converted values, equations,
units, assumptions, and propagated uncertainty. Unknown coordinates remain
unknown; they are not filled using incompressibility, Poisson ratio, or another
assumption unless the source independently justifies that model for the sample.

### 8.3 Overlap report

For each eligible law, report:

- source-supported deformation domain in original and common coordinates;
- Joanna scene-by-scene intersection with that domain;
- which invariant axes are directly matched, model-derived, or unavailable;
- area-weighted Joanna prevalence within the supported intersection, using only
  the already completed characterization;
- lower/upper boundary inclusion and interpolation rule;
- unsupported Joanna regions and all extrapolation that would otherwise be
  required.

No literature/data source is selected after searching for whichever response
best matches a desired image effect. Joanna values rank domain compatibility,
not image impact or material-response strength.

### 8.4 Reference-state limitation

**FROZEN LIMITATION.** Path A is exact relative to each chosen Joanna reference
configuration, but that reference is not assumed to be a stress-free physical
material state (`docs/constitutive_strain_interface_spec.md:93-107`). Therefore:

- Joanna's `lambda=1` means “same as the frozen animation reference,” not zero
  physical material strain;
- absolute matching to a measurement whose zero is stress-free requires an
  independently justified reference-state correspondence;
- absent that correspondence, overlap claims are limited to compatible
  reference-relative excursions/loading paths and must carry an unknown offset;
- the calibration cannot infer prestrain from the observed animation
  distribution.

The measured scene tails—for example those summarized at
`docs/constitutive_deformation_regime_results.md:35-46`—may define the query
range for overlap reporting but cannot define a material response or a
stress-free zero.

## 9. Exclusion rules

The following cannot serve as the primary constitutive calibration:

1. authored Blender roughness values or static scene materials;
2. apparent changes caused mainly by fabric gaps, porosity/opening, or changing
   background visibility;
3. static BRDF differences between different materials, specimens, coatings, or
   preparations without within-material deformation measurements;
4. deformation simulations or procedural shaders with no independent
   measurement calibration;
5. arbitrary hand-authored roughness curves, including curves chosen for image
   visibility;
6. time-dependent appearance without an observed deformation variable;
7. evidence whose deformation axis, range, or reference convention is unknown;
8. macrogeometry, normal, silhouette, shading, exposure, or illumination change
   presented as intrinsic reflectance without a separation/control;
9. a single highlight intensity or image color treated as GGX roughness without
   angular/photometric identifiability;
10. static roughness fitted separately at different frames when geometry,
    normals, lighting, and visibility are not controlled;
11. extrapolation beyond the measured deformation or optical domain presented as
    measured support.

Excluded evidence remains in the matrix with its grade and exclusion reason. It
may be reported qualitatively when useful, but it cannot set the primary law's
form, magnitude, sign, anisotropy, or supported domain.

## 10. Quantitative extraction and mapping discipline

Before extracting values from an eligible source, freeze per source:

- target table/figure/data fields and all series to extract, including controls
  and null/opposite responses;
- digitization or parsing procedure;
- units and deformation/optical conventions;
- aggregation across trials/specimens;
- uncertainty treatment;
- interpolation method within measured support;
- model-fit family and objective, if a renderer mapping is attempted;
- quality/residual statistics and rejection criteria;
- handling of loading versus unloading branches;
- prohibition on extrapolation.

Do not choose these after inspecting which option yields the largest response.
Preserve source-reported values before transformation and make every derived
value reproducible.

### GGX/microfacet mapping requirements

A mapping to GGX is permitted only if the measured quantity and angular domain
identify the relevant parameter(s) sufficiently. The calibration must report:

- GGX convention and whether alpha denotes slope width or another roughness
  parameter;
- isotropic `alpha` or anisotropic `alpha_u, alpha_v`;
- fitting domain, angular weights, masking-shadowing/Fresnel treatment, and
  nuisance parameters;
- fit residuals against each deformation state;
- whether parameter change reflects NDF width rather than changing specular
  albedo, Fresnel response, multiple scattering, porosity, or capture scale;
- uncertainty on both the fit and deformation response.

If the measurements support an NDF/BRDF change but GGX is a poor or
non-identifiable fit, retain a measured lookup/tabulated representation or
report that the current renderer parameterization is inadequate. Do not force
the data into GGX for implementation convenience.

## 11. Calibration deliverable

The later calibration document must contain:

1. complete evidence matrix, including excluded, null, conflicting, and
   unresolved records;
2. strongest primary Grade A/B source or source family, with exact extracted
   evidence;
3. independent corroborating sources and explicit independence assessment;
4. selected material class—or `insufficient evidence`;
5. selected deformation descriptor and reference convention;
6. quantitative response law/range or lookup representation, including source
   quantity before renderer mapping;
7. scalar-versus-anisotropic decision and any material-frame consequence;
8. domain-overlap report against Joanna's `lambda_max`, `lambda_min`,
   `log_area_change`, and `log_anisotropy` support;
9. response uncertainty, sample variability, mapping residuals, confounds,
   hysteresis/path dependence, interpolation support, and unsupported
   extrapolation;
10. recommendation for Gate 1:
    - proceed with a scalar response;
    - proceed with an anisotropic/material-frame response;
    - revise the representation before Gate 1;
    - or do not proceed because evidence is insufficient.

The deliverable must distinguish measured facts, source-author inference,
project inference, and decisions. It must preserve an auditable citation from
every selected numeric value back to its source location and extraction step.

No Gate-1 rendering is authorized by the calibration deliverable itself. Gate 1
requires a separate frozen preregistration specifying the response input,
rendering protocol, baseline, primary statistic, threshold, predictions,
falsifiers, controls, exclusions, and analysis convention.

## 12. Scientific boundary

This calibration can establish only whether independent material evidence
supports a deformation-dependent optical response of known sign, magnitude,
directionality, and domain that can defensibly parameterize a later controlled
signal test.

It cannot establish:

- that the response is observable under LumiMotion cameras, lighting, image
  formation, or noise;
- that a time-invariant material model cannot absorb it;
- that strain conditioning improves held-out deformation or illumination;
- that the Joanna characters possess the selected physical material;
- that their frozen reference configurations are stress-free;
- that Path-B Gaussian strain is accurate;
- that a learned constitutive model is identifiable.

Those image-observability and baseline-absorption questions belong to Gate 1.
The purpose of this protocol is narrower: ensure that Gate 1, if authorized,
tests an independently supported material response rather than a procedural
effect invented for the experiment.

## 13. Protocol provenance

This protocol was prepared on branch `constitutive-appearance` from:

- `AGENTS.md`;
- `docs/CONSTITUTIVE_APPEARANCE_DIRECTION.md`;
- `docs/constitutive_deformation_regime_results.md`;
- `docs/constitutive_blender_version_fidelity_results.md`;
- `docs/constitutive_strain_interface_spec.md`.

Only read-only repository inspection commands were used before writing this
file. Before this protocol was frozen, preliminary conversational scoping had already
identified a small number of possible candidate sources/material classes.
No quantitative response values were extracted, no source was selected as the
primary calibration, and no constitutive law was chosen.

Those pre-known sources are treated as ordinary discovery seeds. They receive no
preferential evidence grade, material-selection priority, or exemption from the
complete material-agnostic search and stopping procedure above.

During preparation of this document itself, Codex performed no external
literature search, dataset download, quantitative extraction, Blender execution,
rendering, training, or constitutive-law selection.
