# Constitutive Appearance — Material-Response Literature Review

## Stage-A closure, evidence consolidation, and Stage-B handoff

**Project:** Constitutive Appearance / LumiMotion  
**Branch:** `constitutive-appearance`  
**Status:** **Stage A closed by protocol reconciliation; Stage B quantitative calibration is next**  
**Closure scope:** protocol-compliant, practical/access-limited scholarly saturation as of **26 August 2026**; **not** a claim of globally exhaustive bibliometric coverage  
**Gate-1 status:** **NOT AUTHORIZED** by this document  
**Material choice:** **NOT MADE** — skin and cloth remain live Stage-B tracks

---

## 0. Executive summary

### 0.1 Why this document exists

This document is the canonical synthesis of the independent material-response literature campaign for the **Constitutive Appearance** direction. It consolidates the frozen calibration protocol, the initial Deep Research discovery pass, the repair pass, the closure-only pass, the final P-CAK micro-pass, and the subsequent closure-rule reconciliation.

The raw/interim reports remain provenance. They are not deleted or rewritten. This document supersedes their **framing and final Stage-A status**, not their detailed search logs.

The question was deliberately narrow:

> **What deformation-dependent reflectance response is independently supported by physical/material measurements under known deformation, strongly enough to justify later quantitative calibration for a controlled inverse-rendering signal test?**

The answer after Stage A is:

1. **The physical premise is real.** Multiple independent experimental families show that mechanical deformation can alter surface-normal distributions, surface microrelief/topography, specular or total reflectance, or related optical response.
2. **There is no universal deformation→roughness law.** Different materials — and even different textile constructions — can respond with opposite signs. The constitutive response is material-, construction-, loading-path-, and scale-dependent.
3. **Skin currently has the strongest renderer-proximal evidence.** Nagano et al. provide the only verified family in the review that cleanly reaches the frozen **Grade B** threshold: deformation-dependent, optically recovered surface-normal distributions with an explicit physical connection to specular appearance. The measured response is strongly directional.
4. **Cloth remains a genuine first-class contender.** Moria, Suzuki/Yamanobe, and Li/Mao/Zhou independently establish deformation-dependent textile surface structure. Static textile-optics work independently establishes strong directional angular reflectance. What is missing is the quantitative within-specimen bridge from **deformation → optical distribution**. This is a substantive Stage-B question, not a reason to discard cloth.
5. **Polymers/elastomers provide strong external physics controls.** Multiple AFM/topography families show both smoothing and roughening under deformation, sometimes with hysteresis or processing dependence. They reinforce material specificity and spatial-scale caution, but they are heterogeneous and are not currently preferred as the primary application material.
6. **No convincing Grade-A family was found** for ordinary deformable cloth, skin, leather, or generic elastomer under the frozen definition of direct deformation-conditioned BRDF/NDF measurement.
7. **No literature-supported GGX law has been selected.** Stage A did not fit curves, choose `alpha`, choose a Gate-1 material, or determine image observability.
8. **Stage A is now closed.** The final search loop remained formally open only because later prompts recursively treated every new `B? / mapping unresolved` morphology paper as a closure-triggering “new family.” That was stricter than the frozen A–D hierarchy. `B?` was introduced later as a screening flag, not as a fifth evidence grade. Restoring the closure criterion to newly discovered **eligible Grade A/B evidence** closes discovery without discarding any `B?` family from the record.

### 0.2 Final Stage-A verdict

```text
STAGE_A_CLOSED

scope:
protocol-compliant practical/access-limited saturation as of 2026-08-26

not claimed:
global bibliometric exhaustiveness
```

This closure **does not** mean the material calibration is complete. It means broad discovery and screening are complete enough to begin **Stage B: quantitative extraction and renderer-mapping adjudication**.

### 0.3 Immediate consequence

The next scientific task is not another literature search and not Gate 1. It is:

```text
Stage B — quantitative material-response calibration

skin:
    Nagano first
    + Maiti / NJIT / Huo as independent physical and optical support

cloth:
    Moria first
    + Kyoto as static optical mapping constraint
    + Suzuki/Yamanobe and Li/Mao/Zhou for mesogeometry/scale adjudication

polymer/elastomer:
    one or two high-information controls only
```

No final skin-versus-cloth choice is required before Stage B.

---

## 1. Relation to the wider research campaign

The previous June–August measurement campaign began from dynamic light transport and tested several candidate mechanisms. Those measurements eliminated or weakened the proposed explanations rather than yielding a working method framing. Importantly, **material change as a first-class temporal quantity — including anisotropy and cloth — remained open** in the authoritative handover. The current Constitutive Appearance direction is therefore not a rebranding of a mechanism already excluded by that campaign.

The new direction asks a qualitatively different question:

> Dynamic inverse-rendering systems deform geometry while usually treating intrinsic material parameters as deformation-invariant. For some deformable materials, does local physical deformation itself change intrinsic surface appearance in a structured, recoverable way?

The working scientific representation is:

\[
\theta_{i,t}=\theta_i^0+g_\psi(z_i,\epsilon_{i,t}),
\]

where `theta_i^0` is canonical material state, `z_i` represents material/local identity, and `epsilon_i,t` is a local physical deformation state. Direct time conditioning is not the intended scientific model.

Before the present literature campaign, the project completed the geometric/instrument side:

```text
LumiMotion substrate audit                    DONE
strain-interface specification                DONE
controlled Path-A strain validation           DONE
Joanna deformation-regime characterization    DONE
Blender 3.6.13 ↔ 4.4.0 geometry fidelity     DONE — PASS
independent material-response calibration      CURRENT
```

Thus Stage A did **not** ask whether Joanna deforms. That is already established. It asked whether independent material physics supports a response worth calibrating before a synthetic signal test.

The Joanna deformation variable remains **reference-relative**, not guaranteed stress-free physical strain. This limitation carries into Stage B: literature strain coordinates may not be mapped onto Joanna by inventing an unknown prestress/prestrain offset.

---

## 2. Frozen scientific boundary

The material-response protocol was frozen before quantitative literature extraction. Its purpose was to prevent an attractive rendering result from deciding the physics after the fact.

### 2.1 What Stage A was allowed to establish

Stage A could establish:

- whether deformation-dependent material/surface response has independent experimental support;
- which material classes have the strongest evidence;
- whether measured effects are scalar, directional, anisotropic, or unresolved;
- which evidence families are independent versus duplicate/reused programmes;
- which branches are direct optical evidence, physical morphology evidence, corroborative optical response, or confounded appearance;
- which families warrant later quantitative extraction.

### 2.2 What Stage A was not allowed to establish

Stage A did **not** authorize:

- a final material class;
- a constitutive response equation;
- a GGX `alpha` or anisotropic `(alpha_u, alpha_v)` curve;
- an arbitrary conversion from `Ra`, RMS height, groove depth, or AFM roughness to microfacet roughness;
- extrapolation outside source measurements;
- a synthetic shader selected for visual effect;
- Gate-1 rendering;
- Path-B Gaussian strain estimation;
- a training-code modification;
- a claim that the response is observable in LumiMotion images.

An outcome of **insufficient evidence** was allowed from the outset.

---

## 3. Evidence hierarchy and terminology

The frozen hierarchy has **four grades only**.

### Grade A — direct optical-distribution evidence

Direct measured BRDF, or measured microfacet/NDF response under known deformation with an explicit quantitative deformation/reference convention.

Grade A does not mean “already GGX.” A GGX fit still requires fit quality, convention, angular domain, nuisance parameters, and uncertainty.

### Grade B — measured microgeometry with physical optical mapping

Measured surface microgeometry, slopes, or surface-normal distribution under known deformation **together with a documented, physically justified connection to a reflectance distribution**.

Merely measuring `Ra`, RMS height, a height map, or AFM topography does not automatically produce Grade B.

### Grade C — direct optical response without full decomposition

Measured specular/reflection/optical response under known deformation without enough angular decomposition to recover or uniquely identify BRDF/NDF/roughness. Grade C can corroborate existence/sign/scale but cannot alone define the primary constitutive law.

### Grade D — entangled visible appearance

Visible/color response in which geometry, openings, porosity, background visibility, projected density, lighting, exposure, camera response, or related effects are entangled. Grade D is qualitative/corroborative only.

### `B? / mapping unresolved` — screening flag, not a grade

During the search campaign a useful screening flag emerged:

```text
B? / mapping unresolved
```

It means:

> a real deformation-dependent surface/topography measurement exists, but the physical optical/scattering mapping required by actual Grade B is absent or unresolved.

This flag is retained because it is highly useful for Stage-B triage. It is **not** a fifth grade and is **not** itself `eligible_primary` under the frozen sufficiency rule.

This distinction is central to the final Stage-A closure decision in §11.

---

## 4. Search campaign chronology and corrections

### 4.1 Protocol freeze

Before the broad search, the project froze:

- evidence hierarchy;
- evidence-family identity rules;
- retention of null/weak/opposite results;
- material-agnostic discovery;
- scalar-versus-anisotropic adjudication;
- reference-state cautions;
- cloth-specific confound handling;
- quantitative extraction discipline;
- separation of Stage A discovery from Stage B extraction and Gate 1.

The protocol was committed on branch `constitutive-appearance` before the Deep Research discovery campaign.

### 4.2 Stage-A v1 — broad discovery and screening

The first broad search covered skin, woven/knitted textiles, elastomers, polymers, membranes, leather, and engineered surfaces using deformation terminology crossed with BRDF/reflectance/NDF/roughness/microgeometry/profilometry/AFM terminology.

The key v1 findings were:

- Nagano skin as the strongest renderer-proximal family;
- Moria as a serious textile deformation/topography family;
- independent static textile angular-optics work;
- NJIT and Huo as optical skin corroboration;
- TPU/photonic systems as direct but mechanism-mismatched optical examples;
- no convincing direct deformation-conditioned cloth BRDF/NDF family.

V1 initially described accessible discovery as operationally saturated. Subsequent audit showed this was premature.

### 4.3 Repair pass

The repair pass explicitly searched missed branches and added or clarified:

- Maiti et al. 2016 — direct DIC surface strain plus OCT/morphology;
- Ferguson & Barbenel 1981 — historical skin surface/mechanics branch, access-limited;
- Corcuff et al. 1991 — independent human skin microrelief branch;
- Suzuki/Yamanobe — independent stretched-textile 3D surface branch;
- Li/Mao/Zhou — stretched grooved-fabric morphology;
- Opdahl/Somorjai — in-situ polymer AFM roughening;
- van Tijum — strain-dependent statistical surface roughness;
- PDMS-Yang 2026 — strain-dependent AFM smoothing;
- Dasari, Nishino, Nishizawa and other polymer-film branches.

This pass strengthened the evidence landscape while invalidating the v1 saturation claim.

### 4.4 Closure-only pass

The closure-only pass repaired a second issue: grade drift. Several morphology papers had been called “Grade B” despite lacking the optical mapping required by the frozen definition.

The pass normalized them to `B? / mapping unresolved` and conservatively resolved Nagano to **Grade B**.

It also clarified the cloth spatial-scale problem:

- Moria: potentially bridgeable, but KES-style measurement is not automatically microfacet-scale;
- Suzuki/Yamanobe: largely millimetre/yarn/loop/groove-scale mesogeometry;
- Li/Mao/Zhou: explicitly millimetre-scale groove deformation plus finer roughness;
- Kyoto: static optical mapping support only, not deformation-conditioned optics.

The terminal search then surfaced Cakmak/Wang/Iwakura 1992 (PET/PPS), keeping the procedural loop open under the then-current closure prompt.

### 4.5 P-CAK micro-pass

The micro-pass screened Cakmak/Wang/Iwakura 1992 as far as accessible evidence allowed.

Verified at abstract/metadata level:

- biaxial stretching conditions were varied;
- PET became smoother with higher stretch ratio / lower processing temperature;
- PPS showed the opposite roughness tendency with increasing stretch;
- exact roughness measurement method, spatial scale, loading path, and in-load/post-processing state remained unavailable;
- no direct optical measurement or BRDF/NDF mapping was documented.

Final status:

```text
P-CAK:
B? / mapping unresolved + methods access-limited
not presently eligible_primary
P-CAK branch itself: access_limited_saturated
```

The required descendant search exposed further polymer-film morphology families (PMMA, PEEK, PVDF/PMMA, BOPP, PA510/SiO2, PA6, PLA/PBAT). Several were scientifically useful, but none supplied a new direct deformation-conditioned surface reflectance distribution suitable for promotion to an eligible renderer-calibration family under the frozen hierarchy.

The Deep Research micro-pass nevertheless returned `STAGE_A_REMAINS_OPEN` because its prompt recursively treated every new `B?` family as a closure trigger.

### 4.6 Closure-rule reconciliation

This final document makes an explicit project-level correction rather than silently rewriting the prior reports.

The frozen evidence hierarchy has Grades A–D. Its sufficiency rule requires an **eligible Grade A record or eligible Grade B record with a documented physical optical mapping** before a Gate-1 law may later be authorized.

`B?` was introduced **afterward** as a screening flag for morphology evidence lacking that mapping.

Later closure prompts expanded the terminal trigger from:

```text
new eligible Grade A/B family
```

to:

```text
new A/B/B? family
```

Those are not equivalent. The latter creates an effectively unbounded search over every polymer, coating, fibre, membrane, or textile for which stretching changes a roughness/topography statistic. That search can continue indefinitely while adding no new evidence capable of meeting the frozen calibration threshold.

**Project decision:** restore closure semantics to the frozen scientific hierarchy.

A newly discovered `B?` morphology family is retained and screened, but it does not recursively reopen discovery unless screening shows that it plausibly satisfies actual Grade A/B eligibility or materially changes the primary material landscape.

Under that reconciliation:

- P-CAK itself is screened and access-limited saturated;
- its descendants are retained below;
- BOPP transmission evidence is important scale/mapping evidence but is not a deformation-conditioned surface reflectance distribution;
- PA510/SiO2 concurrent optics are explicitly confounded by filler aggregation/orientation;
- the remaining descendants are morphology/processing evidence without the required reflectance-distribution mapping;
- no new eligible Grade A/B family emerged from the terminal loop.

Therefore Stage A closes without claiming global bibliometric exhaustiveness.

---

## 5. Final evidence landscape

## 5.1 Skin / biological rough surfaces

### 5.1.1 SKIN-NAGANO — primary Stage-B family

**Reference family:**

- Nagano et al., *Skin Microstructure Deformation with Displacement Map Convolution*, ACM TOG 34(4), 2015, DOI `10.1145/2766894`.
- SIGGRAPH 2014 preliminary presentation, released sample data, and GLSL implementation belong to the same measurement family and must not be counted as independent replications.

**Measured evidence:** in-vivo skin patches were stretched/compressed in controlled directions; polarised photometric measurements recovered dense surface-normal maps at approximately 10 µm sampling, and deformation-dependent normal/orientation distributions were analysed.

**Response:** stretching narrows/smooths the surface-normal distribution preferentially along the loading direction; compression broadens/roughens and produces directional furrowing. The effect is therefore fundamentally directional. A mean/isotropic component may exist, but Stage A does not justify discarding anisotropy.

**Grade:** **B**.

**Why not A:** the measured quantity is an optically recovered spatial surface-normal distribution with strong appearance interpretation, not a directly measured far-field BRDF; Stage A does not establish numerical identity between that distribution and a specific renderer's microfacet NDF.

**Why it matters:** this is the closest literature family to the representation a physical renderer needs.

**Stage-B unknowns:** exact per-state deformation coordinate/reference, measured-vs-modelled separation, sample count, uncertainty, source histogram/data representation, appropriate anisotropic fit or measured lookup, and supported deformation range.

### 5.1.2 SKIN-MAITI — deformation-coordinate anchor

**Reference:** Maiti et al., *In vivo measurement of skin surface strain and sub-surface layer deformation induced by natural tissue stretching*, J. Mech. Behav. Biomed. Mater. 62 (2016), DOI `10.1016/j.jmbbm.2016.05.035`.

**Measured evidence:** DIC directly measured surface Lagrange strain during forearm extension; OCT measured surface/subsurface morphology and roughness. Reported surface strain is typically around 25% and reaches roughly 30%; substantial reductions in surface roughness accompany extension.

**Status:** `B? / mapping unresolved`.

**Value:** unusually clean deformation-coordinate evidence independent of Nagano. It can corroborate deformation scale and physical sign even if it cannot itself define renderer roughness.

**Limitation:** no direct deformation-conditioned BRDF/NDF mapping.

### 5.1.3 SKIN-CORCUFF — independent directional microrelief

**Reference:** Corcuff, de Lacharrière & Lévêque, J. Gerontology 46 (1991), DOI `10.1093/geronj/46.6.M223`.

**Measured evidence:** human forearm replicas/image analysis show extension-dependent changes in furrow orientation/depth/density, with age-dependent directional response.

**Status:** `B? / mapping unresolved`.

**Limitation:** exact local deformation/reference details and quantitative extraction require primary-text work; no direct optical mapping.

### 5.1.4 SKIN-FERGUSON — historical, access-limited

**Reference:** Ferguson & Barbenel, *Skin surface patterns and the directional mechanical properties of the dermis*, in *Bioengineering and the Skin*, 1981, pp. 83–92.

The chapter's bibliographic identity and historical role are supported by later work, but authoritative full methods/results were not recovered in Stage A.

**Status:** `unresolved / access-limited historical family`.

It is not promoted to Grade B and is not required to block Stage B.

### 5.1.5 SKIN-NJIT — optical corroboration

**Family:**

- Federici et al., Applied Optics 38 (1999), DOI `10.1364/AO.38.006653`;
- Guzelsu et al., J. Biomedical Optics 8 (2003), DOI `10.1117/1.1527936`;
- Schulkin et al., Applied Optics 42 (2003), DOI `10.1364/AO.42.005198`.

These publications belong to one overlapping experimental/research programme rather than three independent replications.

**Evidence:** polarised/specular reflectivity increases with stretch; decreasing interface roughness is a source interpretation supported/tested against alternatives but BRDF/NDF is not directly recovered.

**Grade:** **C**.

**Role:** independent optical corroboration for sign/existence, not the primary constitutive law.

### 5.1.6 SKIN-HSI — independent spectral corroboration

**Reference:** Huo et al., Biomedical Optics Express 15 (2024), DOI `10.1364/BOE.507361`.

**Evidence:** strain-modulated hyperspectral total reflectance in vivo under extension/compression.

**Grade:** **C**.

**Limitation:** total spectral reflectance mixes surface roughness, thickness and subsurface transport, so it cannot identify a unique surface NDF response.

### 5.1.7 Skin conclusion

Skin has the strongest complete evidence package because it combines:

```text
renderer-proximal normal-distribution evidence     Nagano
clean independent deformation-coordinate evidence  Maiti
independent directional microrelief evidence        Corcuff/Ferguson lineage
independent optical corroboration                   NJIT + Huo
```

The strongest warning is also clear: **directionality is first-order**. A scalar-only model is not justified by convenience.

---

## 5.2 Cloth and textiles

Cloth survived Stage A on evidence, not preference. The key distinction is between **intrinsic/sub-resolution scattering change** and **explicit evolving mesogeometry**.

### 5.2.1 TEXTILE-MORIA — highest-priority cloth family

**Reference family:** Moria et al., *Aerodynamic behaviour of stretchable sports fabrics*, Sports Technology 4, DOI `10.1080/19346182.2012.725412`, plus related Procedia/thesis work from the same programme.

**Measured evidence:** commercial knitted and woven fabrics were measured across multiple extension states using textile surface roughness/profiling and microscopy.

The broader programme reports construction-dependent sign:

- knitted samples can become rougher under extension;
- woven samples can become smoother.

Examples reported in the discovery review include knitted K1 increasing from approximately 12.1 µm to 30.7 µm `Ra` over the tested elongation sequence, while woven W1 decreases from approximately 14.6 µm to 11.7 µm.

**Status:** `B? / mapping unresolved`.

**Why this is not yet Grade B:** KES-style contact roughness operates over substantial textile structure. Stage A did not establish that the available raw profiles contain the spatial bandwidth/slope statistics needed for an optical NDF. `Ra -> GGX alpha` would be arbitrary.

**Why it remains high priority:** it is genuine within-specimen deformation-dependent surface change, includes both woven and knitted constructions, and the opposite signs make construction dependence scientifically explicit.

**Stage-B question:** can the underlying measurement be reduced to a physically meaningful slope/normal distribution, or is the dominant signal yarn/weave-scale explicit geometry?

### 5.2.2 TEXTILE-SUZUKI — independent mesogeometry family

**References:** Suzuki & Yamanobe 2021, DOI `10.1299/jsmeshd.2021.A-4-1`; later peer-reviewed continuation DOI `10.5997/sposun.33.1_39`.

**Evidence:** 3D surface measurements of stretched knitted sports fabrics; later work explicitly discusses millimetre-scale grooves/dimples and construction-dependent feature response.

**Status:** `B? / mapping unresolved`.

**Interpretation:** strong evidence for deformation-dependent textile **mesogeometry**. It may still matter to appearance, but representing it purely as intrinsic BRDF roughness risks double-counting structure that belongs in explicit geometry/normals/porosity.

### 5.2.3 TEXTILE-LI — controlled grooved-fabric family

**Reference:** Li/Mao/Zhou 2024–2025, later AIAA Journal DOI `10.2514/1.J065006`.

**Evidence:** controlled transverse stretch of a grooved technical fabric; 3D scanning and confocal measurements show stretch-dependent groove width/depth and roughness. The groove structures are explicitly millimetre-scale.

**Status:** `B? / mapping unresolved`.

**Interpretation:** excellent constitutive mesogeometry evidence; weak evidence for a sub-resolution microfacet law.

### 5.2.4 TEXTILE-KYOTO — static optical mapping support

**Reference:** Endo et al., J. Textile Engineering 59 (2013), DOI `10.4188/jte.59.75`, plus related static orientation work.

**Evidence:** gonio-spectrophotometric angular reflectance distributions vary strongly with weave structure and fabric rotation/orientation.

**Status:** not primary deformation evidence.

**Role:** proves that textile structure/orientation has strong directional optical consequences, but it cannot be quantitatively combined with Moria/Suzuki/Li as though the same specimens were measured optically under deformation.

The correct logical statement is:

\[
\text{deformation} \to \text{textile surface structure}
\]

and independently

\[
\text{textile structure/orientation} \to \text{angular optical response}.
\]

Stage A does **not** establish the direct within-specimen bridge

\[
\text{deformation} \to \text{BRDF/NDF change}.
\]

### 5.2.5 TEXTILE-STRETCH-COLOR — useful Grade-D counterexample

**Reference:** Woelfle et al., Frontiers in Computer Science (24 Aug 2026), DOI `10.3389/fcomp.2026.1841037`.

A stretched knit reveals an increasingly visible coloured background as the fabric opens. The measured color response is therefore materially affected by porosity/openings/background visibility.

**Grade:** **D**.

This source is valuable precisely because it demonstrates why a large repeatable image effect is not automatically intrinsic reflectance change.

### 5.2.6 Cloth conclusion

The cloth evidence supports:

> **deformation changes textile surface structure, and textile structure is optically directional.**

It does not yet support:

> **a calibrated deformation-conditioned microfacet/BRDF law for ordinary cloth.**

That missing bridge is the main Stage-B cloth question.

Woven and knitted cloth must remain separate material/construction classes; “cloth gets smoother under stretch” is already falsified as a generic claim by construction-dependent opposite signs.

---

## 5.3 Polymers and elastomers — external physics controls

This branch expanded significantly during repair and closure. It should not be interpreted as one coherent material class or pooled law.

### 5.3.1 POLYMER-OPDAHL

**Reference:** Opdahl & Somorjai, J. Polymer Science B 39 (2001), DOI `10.1002/polb.1200`.

In-situ AFM measures LDPE/HDPE surface evolution across elastic/plastic/fibrillar tensile regimes. Surfaces roughen; reversibility differs between regimes.

**Status:** `B? / mapping unresolved`.

**Role:** strong physical control for hysteresis/path dependence and counterexample to universal stretch→smoothing.

### 5.3.2 POLYMER-VAN-TIJUM

**Reference:** van Tijum, Vellinga & De Hosson, Acta Materialia 55 (2007), DOI `10.1016/j.actamat.2006.12.013`.

A glassy polymer coating co-deformed with a metal substrate exhibits evolution in RMS roughness amplitude, correlation length and Hurst exponent.

**Status:** `B? / mapping unresolved`.

**Role:** important because the surface is characterised with richer statistics than scalar `Ra`, but substrate-coupled processing/mechanics limit direct application to cloth/skin.

### 5.3.3 PDMS-YANG

**Reference:** Yang et al., Frontiers in Pharmacology 17 (2026), DOI `10.3389/fphar.2026.1857290`.

AFM measurements compare PDMS at 0 and 20% controlled stretch; the reported roughness decreases substantially while modulus is comparatively unchanged under the tested condition.

**Status:** `B? / mapping unresolved`.

**Role:** clean opposite-sign control to polyethylene roughening.

### 5.3.4 POLYMER-DASARI

**Reference:** Dasari et al., Materials Science and Technology 18 (2002), DOI `10.1179/026708302225003550`.

AFM shows tensile-plastic-deformation-induced nanoscale fibril/microfibril restructuring with strain-rate dependence.

**Status:** `B? / mapping unresolved`.

### 5.3.5 POLYMER-NISHINO

**Reference:** Nishino et al., Review of Scientific Instruments 71 (2000), DOI `10.1063/1.1150585`.

In-situ AFM tracks local distances/strain and transverse response in polymer film.

**Status:** support only / excluded primary.

It is strong local-deformation methodology but does not establish a changing roughness/NDF distribution.

### 5.3.6 POLYMER-NISHIZAWA

**Reference:** Nishizawa et al., ACS Applied Materials & Interfaces 16 (2024), DOI `10.1021/acsami.4c16013`.

In-situ AFM shows non-affine surface-particle structural evolution in a slightly cross-linked microparticle film under elongation.

**Status:** `B? / mapping unresolved`.

### 5.3.7 POLYMER-MOREHOUSE

**Reference:** Morehouse et al., Journal of Membrane Science 280 (2006), DOI `10.1016/j.memsci.2006.02.027`.

AFM/SEM measurements show large morphology/pore changes under stretching; conventional RMS/`Ra` can fail to represent the structural change.

**Status:** `B? / mapping unresolved`.

**Role:** strong warning against collapsing multiscale morphology into one roughness number.

### 5.3.8 NBR-SHADRINOV

**Reference:** Shadrinov & Fedorov, Plastics, Rubber and Composites 51 (2022), DOI `10.1080/14658011.2021.2008704`.

AFM measures strain- and temperature-dependent NBR morphology/microroughness.

**Status:** `B? / mapping unresolved`.

### 5.3.9 P-CAK — PET/PPS processing branch

**Reference:** Cakmak, Wang & Iwakura, International Polymer Processing 7 (1992), DOI `10.3139/217.920327`.

Accessible records establish biaxial-stretching-dependent final roughness: PET and PPS show opposite tendencies. Full methods, exact strain convention, spatial measurement scale, and in-load versus processing-state timing were not available.

**Status:** `B? / mapping unresolved + methods access-limited`; not eligible primary.

**Role:** strong material-specific sign/process-history control.

### 5.3.10 P-CAK descendants retained after the micro-pass

These sources were discovered while closing P-CAK and are retained for provenance rather than recursively reopening Stage A:

| Family | Evidence | Final Stage-A role |
|---|---|---|
| Wang & Cakmak 1993 PMMA, DOI `10.3139/217.930143` | Biaxial stretching associated with improved PMMA surface smoothness; full methods access-limited | `B?`, processing/morphology control |
| Cakmak & Simhambhatla 1995 PEEK, DOI `10.1002/pen.760351910` | Uni/biaxial processing conditions affect surface roughness/thickness | `B?`, processing-state morphology |
| Zhou & Cakmak 2007 PVDF/PMMA, DOI `10.1002/pen.20935` | Uni/biaxial deformation linked to topography/thickness | `B?`, no direct BRDF/NDF mapping |
| Lin et al. 2007 BOPP, DOI `10.1002/pen.20850` | AFM roughness plus 633-nm light transmission; larger-scale roughness affects transparency while submicron roughness may not | high-information **scale/mapping control**, not a deformation-conditioned surface reflectance distribution |
| Cui et al. 2021 PA510/SiO2, DOI `10.3390/ma14040705` | explicit biaxial stretch ratios; AFM + haze/transmission/gloss; optical change also attributed to filler aggregation/orientation | `B? / optical mapping confounded` |
| Harrell et al. 2024 PA6, DOI `10.1007/s10965-024-04017-0` | 10–50% stretch followed by release before AFM/XRD | `B?`, post-load/residual morphology |
| PLA/PBAT 2023 family | uni/biaxial stretching with non-monotonic roughness and optical characterization | `B?`, mapping/process/crystallisation confounded |

The BOPP result is especially useful conceptually: the optical importance of “roughness” depends on **spatial scale**. This reinforces the cloth-scale concern.

### 5.3.11 Polymer/elastomer conclusion

The polymer evidence establishes a broad physical fact:

> mechanical deformation can reorganize surface statistics at micro/nanoscales, with sign, reversibility, and path dependence determined by material microstructure and processing regime.

It does **not** establish one transferable deformation→reflectance law for the project.

For Stage B, only one or two high-information polymer families should be retained as controls. Raw paper count is not a material-selection criterion.

---

## 5.4 Specialist / excluded mechanisms

### TPU nanofibre membranes

**Reference:** Li et al., Chemical Engineering Journal 461 (2023), DOI `10.1016/j.cej.2023.142095`.

Large reversible spectral reflectance/transmittance changes occur under stretch, but the mechanism is fibrous multiple scattering/porosity/transmission rather than a clean surface microfacet response.

**Grade:** C / specialist.

### Photonic/Bragg/mechanochromic systems

Example: Martusciello & Comoretto 2024, DOI `10.1021/acsami.4c13447`.

Direct deformation-dependent optical response exists, but interference/layer spacing/resonance is the mechanism. These systems prove deformation→optics broadly, not the rough-surface constitutive law sought here.

### Engineered wrinkles

Directional prestrain/buckling can produce strong anisotropic topography. These are useful dimensionality/existence examples but deliberately engineered instability systems and are poor ordinary-material analogues.

### Leather

Leather tensile mechanics and SAXS work (e.g. DOI `10.1021/jf2039586`) strongly characterize internal collagen reorientation, but Stage A did not find a competitive same-specimen deformation-dependent visible-surface optical/topography family.

### Theoretical gel roughening

Wang & Liu 2024, DOI `10.1039/D4SM00139G`, is theoretical rather than primary measurement evidence. It remains useful as a warning that even the *sign* of roughness response can depend on elastocapillary/osmocapillary physics.

---

## 6. Cross-cutting scientific conclusions

### 6.1 There is no universal `stretch -> smoother` law

The literature contains:

- skin smoothing under stretch;
- woven-fabric smoothing in one programme;
- knitted-fabric roughening in the same broader programme;
- polyethylene roughening;
- PDMS smoothing;
- PET/PPS opposite-sign responses within one processing programme;
- non-monotonic polymer-blend responses.

Therefore the evidence supports a material-specific formulation such as:

\[
\theta_t = g(\text{material identity},\ \text{deformation state},\ \text{loading path},\ \text{microstructural state}),
\]

not a universal deformation-only law.

This is consistent with the intended constitutive appearance representation:

\[
\theta_{i,t}=\theta_i^0+g_\psi(z_i,\epsilon_{i,t}).
\]

The material/local code `z_i` is not cosmetic; the physical literature gives a reason it is necessary.

### 6.2 Directionality is not optional physics

Nagano is strongly directional. Textile optics is strongly orientation-dependent. Textile deformation itself is construction- and direction-dependent.

Thus the strongest evidence points toward an eventual **material-frame / anisotropic** model.

However, this does **not** automatically authorize implementing anisotropy now. Stage B must quantify whether a meaningful mean/isotropic component survives strongly enough for a scalar first signal gate, or whether scalar reduction removes most of the measured response.

### 6.3 Spatial scale is first-order

“Surface roughness” is not a renderer parameter until its spatial/slope band and optical role are identified.

The literature contains measurements from:

- approximately 10 µm skin normal maps;
- AFM nanoscale polymer morphology;
- KES/contact textile profiles spanning yarn/weave structure;
- millimetre textile grooves/dimples;
- explicit porosity/opening changes;
- larger-scale film roughness that affects optical transmission while finer roughness may not.

A valid Stage-B mapping must distinguish:

```text
sub-resolution scattering statistics
vs
explicit geometry / mesogeometry / porosity
```

otherwise the later model may double-count geometry as BRDF roughness.

### 6.4 Reference state remains unresolved

The literature may define stress-free strain, holder displacement, engineering stretch ratio, Lagrange strain, processing stretch ratio, or post-load state.

Joanna uses a frozen animation reference configuration that is **not known stress-free**.

Therefore:

- no literature zero may be silently equated to Joanna `lambda = 1`;
- no unreported transverse stretch may be invented from incompressibility or Poisson ratio;
- no stress variable may be substituted for strain;
- no processing/post-load morphology may be treated as an instantaneous reversible constitutive response without justification.

### 6.5 Direct optical evidence and morphology evidence must remain distinct

The campaign repeatedly encountered the temptation to combine:

```text
A: deformation changes morphology
B: morphology affects optics
therefore
C: deformation changes BRDF by a known law
```

A and B can make C physically plausible, but they do not determine C quantitatively unless the bridge is measured or physically mapped with a testable model.

This distinction is especially important for cloth.

### 6.6 Large appearance change can be the wrong signal

The stretched-knit color study and specialist porous/photonic systems show that large, clean, reproducible appearance changes can arise from:

- background visibility;
- openings/porosity;
- projected density;
- transmission;
- filler aggregation;
- interference/resonance;
- bulk multiple scattering.

A strong image effect is therefore not an evidence-selection criterion.

---

## 7. Final family-level screening matrix

`B?` below means **mapping unresolved screening flag**, not a frozen grade.

| ID | Material class | Deformation evidence | Measured response | Final Stage-A status | Stage-B role |
|---|---|---|---|---|---|
| S-NAG | skin | directional stretch/compression | optically recovered surface-normal distributions | **Grade B, eligible primary** | **high** |
| S-MAI | skin | DIC Lagrange strain ~25–30% | OCT/morphology/roughness reduction | B? | high physical-coordinate support |
| S-COR | skin | extension states | directional microrelief/furrows | B? | medium |
| S-FER | skin | directional mechanics | historical surface-pattern response | unresolved/access-limited | low unless source recovered |
| S-NJIT | skin | stretch/strain | polarised/specular reflectivity | **Grade C** | medium corroboration |
| S-HSI | skin | extension/compression | hyperspectral total reflectance | **Grade C** | medium corroboration |
| T-MOR | woven/knit | multiple elongations | contact surface profiles/roughness/morphology | B? | **high cloth** |
| T-SUZ | knit | controlled stretch | 3D grooves/dimples/surface features | B?; mainly mesogeometry | medium-high cloth |
| T-LI | technical grooved knit | transverse stretch ratio | groove geometry + confocal roughness | B?; explicit mesogeometry | medium cloth |
| T-KYO | static textile | no deformation | angular reflectance vs structure/orientation | not primary | medium mapping support |
| T-COLOR | knit | 0–100% strain | camera color with exposed background | **Grade D** | none; confound control |
| P-OPD | polyethylene | tensile elastic→plastic | AFM roughening/reversibility | B? | medium physics control |
| P-VT | polymer coating | uniaxial co-deformation | RMS/correlation/Hurst evolution | B? | medium-low control |
| P-PDMS | PDMS | 0 vs 20% stretch | AFM smoothing | B? | medium control |
| P-DAS | polyethylene | tensile plastic deformation | AFM fibril restructuring | B? | low-medium |
| P-NIS | polymer film | in-situ tensile | local feature distances/strain | support only | none |
| P-NIZ | latex particle film | uniaxial elongation | AFM non-affine surface structure | B? | low-medium |
| P-MORE | membrane | uniaxial stretch | AFM/SEM pore/roughness change | B? | low; scale warning |
| P-SHAD | NBR | strain + temperature | AFM microroughness | B? | medium-low |
| P-CAK | PET/PPS | biaxial processing stretch | final surface roughness | B? + access-limited | low; sign/process control |
| P-BOPP | polypropylene film | biaxial orientation | AFM roughness + light transmission | B?/optical-scale support | medium control |
| P-PA510 | filled polymer film | explicit biaxial ratios | AFM + haze/transmission/gloss | B? confounded | low-medium control |
| TPU | nanofibre membrane | large stretch | spectral reflectance/transmission | **Grade C specialist** | low for surface law |
| photonic | engineered elastomer | tensile strain | spectral resonance/reflectance | **Grade C specialist** | excluded primary |
| leather | leather | tensile strain | internal collagen mechanics | excluded primary | none |

---

## 8. What Stage A establishes

### VERIFIED BY THE LITERATURE CAMPAIGN

1. **Deformation-dependent material/surface response exists in physical measurements.**
2. **The response is material- and construction-specific.** Opposite signs occur across materials and even within related systems.
3. **Directional response is common and central.** It is clearly present in the strongest renderer-proximal skin evidence and in textile structure/optics.
4. **Skin has one verified renderer-proximal Grade-B family.** Nagano is the strongest primary Stage-B extraction target.
5. **Cloth has multiple independent deformation-dependent surface-structure families.** It is scientifically justified to keep cloth alive through Stage B.
6. **No direct deformation-conditioned cloth BRDF/NDF family was found.**
7. **Static textile structure is optically directional.** This supports physical plausibility but not a quantitative deformation→BRDF law.
8. **Spatial scale matters.** Scalar height roughness cannot be assumed to equal renderer roughness.
9. **Polymers/elastomers provide independent sign/reversibility/path-dependence controls.**
10. **Large optical effects can arise through the wrong mechanism.** Porosity/background visibility, transmission, photonic interference, bulk scattering and filler structure must be separated from intrinsic surface scattering.

---

## 9. What Stage A does NOT establish

### OPEN / DEFERRED TO STAGE B OR LATER GATES

1. A quantitative strain→GGX curve.
2. A final scalar-versus-anisotropic representation.
3. A final material class for Gate 1.
4. A valid `Ra -> alpha` conversion for cloth.
5. That Moria/Suzuki/Li textile morphology is primarily sub-resolution BRDF change rather than explicit mesogeometry.
6. Exact compatibility between literature deformation coordinates and Joanna's reference-relative principal stretches.
7. That the literature-supported response is large enough to matter in LumiMotion images.
8. That a strong time-invariant material oracle cannot absorb the effect.
9. That strain conditioning generalizes better than arbitrary time conditioning.
10. That Gaussian-estimated strain will be accurate enough for the final method.
11. That a lab material experiment is necessary.
12. That the final paper should use skin rather than cloth, or vice versa.
13. That a scalar roughness-only prototype is physically adequate.
14. Any Gate-1 response magnitude, threshold, prediction, or falsifier.

---

## 10. Null, conflicting, and inconvenient evidence retained

The campaign deliberately preserves evidence that makes the story less simple.

### 10.1 Opposite signs

- skin: stretch-associated smoothing in the strongest normal/morphology families;
- woven fabric: smoothing in Moria's broader programme;
- knitted fabric: roughening in the same broader programme;
- polyethylene: roughening in AFM studies;
- PDMS: smoothing under the identified stretched condition;
- PET/PPS: opposite roughness tendencies within one processing family.

This rejects any universal sign law.

### 10.2 Null/weak response

The skin/stratum-corneum literature includes structural/functional quantities that do not change significantly over moderate extension. Response specificity must be preserved rather than assuming every optical/material variable moves with strain.

### 10.3 Path dependence

Polymer evidence includes elastic reversibility, partial irreversibility, plastic deformation, processing-state roughness, and post-stretch residual morphology. A later constitutive model must not silently equate these regimes.

### 10.4 Cloth confounds

Knitted-fabric extension can change:

- pore size;
- yarn spacing;
- projected density;
- loop/groove geometry;
- background visibility;
- macroscopic normals and self-shadowing.

These are physical appearance effects, but not necessarily intrinsic BRDF change.

### 10.5 Optical confounds

Concurrent roughness/optics studies can still be non-identifiable when transmission, thickness, filler aggregation, subsurface transport, or photonic mechanisms change simultaneously.

---

## 11. Stage-A closure decision

### 11.1 Why the final Deep Research report still said `STAGE_A_REMAINS_OPEN`

The final closure-only audit had reduced the remaining obligation to P-CAK. The P-CAK micro-pass then completed access-limited chaining of that family, but the descendant/terminal search found additional polymer-film morphology papers.

The micro-pass prompt required closure only if **no new A/B/B? family** appeared. Since several new `B?` morphology families appeared, it correctly returned `STAGE_A_REMAINS_OPEN` under that prompt.

### 11.2 Why this document closes Stage A

That recursive criterion is not identical to the frozen scientific hierarchy.

The original hierarchy has Grades A–D. `B?` is explicitly a later screening convenience for morphology evidence that **does not yet satisfy actual Grade B** because optical mapping is missing or unresolved.

Treating every new `B?` paper as a full closure-triggering family turns Stage A into a search for every material whose topography changes under mechanical processing. Such a search is not bounded by the original calibration question and can continue indefinitely without producing additional evidence eligible to define the later response law.

The P-CAK descendants were nevertheless screened rather than ignored. Their disposition is:

- morphology/processing evidence without direct deformation-conditioned reflectance distribution;
- optical transmission or haze evidence where present, not a surface BRDF/NDF;
- confounded optical mapping where fillers/crystallisation/processing also change;
- no newly established eligible Grade-A/B constitutive-reflectance family.

Therefore the search result that matters under the frozen hierarchy is:

> **No new eligible Grade-A/B family emerged after normalization of the terminal discoveries.**

### 11.3 Final scope statement

```text
STAGE_A_CLOSED
```

Meaning:

> broad material-agnostic discovery and evidence-family screening are sufficiently saturated, within the accessible scholarly channels and documented access/recency limits, to proceed to Stage-B quantitative extraction without another general literature search.

Not meaning:

> every paper ever published has been found.

New literature encountered later may of course be added, but it does not retrospectively invalidate this closure unless it materially changes the evidence hierarchy or directly supplies a previously missing deformation-conditioned reflectance distribution.

---

## 12. Stage-B handoff

Stage B is **quantitative extraction and mapping adjudication**, not another discovery review.

### 12.1 Priority 1 — SKIN-NAGANO

**Why:** only verified Grade-B, renderer-proximal family.

**Extract next:**

- exact sample/patch identities and counts;
- deformation-state indexing for every measured normal distribution;
- exact relationship among holder displacement, strain/stress variables, and measured states;
- source normal histograms/maps or released sample data;
- principal/directional widths and mean component;
- compression versus extension range;
- sample-to-sample and orientation variability;
- uncertainty/repeatability if available;
- whether a measured/tabulated representation is preferable to GGX;
- if GGX is attempted, anisotropic fit convention and residuals.

**Decision Stage B must make:** does the physical response support a scalar first Gate 1, or is anisotropy so dominant that material-frame modeling must move earlier?

### 12.2 Priority 2 — TEXTILE-MORIA

**Why:** strongest potentially bridgeable ordinary-cloth deformation family and directly aligned with the intended application.

**Extract next:**

- exact fabric construction/composition;
- sample/gauge dimensions;
- elongation/reference convention;
- woven versus knitted series separately;
- all roughness/profile quantities and standard deviations;
- KES probe geometry, sampling/filtering and spatial bandwidth;
- whether raw 1-D profiles or only summary values are available;
- whether slope statistics can be recovered without an arbitrary model;
- transverse response if measured;
- construction-specific response signs/ranges.

**Decision Stage B must make:** can this family support a physically constrained sub-resolution scattering law, or is the measured response mainly explicit yarn/weave mesogeometry?

### 12.3 Priority 3 — independent skin support

#### Maiti

Extract quantitative strain/roughness/morphology states and uncertainty. Use primarily to anchor deformation-scale plausibility and independent physical sign, not to invent an optical mapping.

#### NJIT

Extract polarised reflectivity-vs-stretch response and what controls were used to support the roughness interpretation. Treat the three papers as one family.

#### Huo

Extract exact strain convention and total spectral response, but retain thickness/subsurface confounds explicitly.

#### Corcuff/Ferguson

Use as historical/directional support only where primary evidence is accessible. Do not allow inaccessible historical detail to block the calibration.

### 12.4 Priority 4 — cloth mapping/scale support

#### Kyoto / Endo

Extract the relationship between textile structure/orientation and measured angular reflectance. Do not couple it numerically to Moria unless a justified cross-specimen model exists.

#### Suzuki/Yamanobe

Extract feature scales/resolution and determine whether any sub-yarn roughness information survives beyond explicit grooves/dimples.

#### Li/Mao/Zhou

Use mainly to quantify the mesogeometry branch and to avoid double-counting explicit groove geometry as BRDF roughness.

### 12.5 Priority 5 — one or two polymer controls

Do not quantitatively extract the entire polymer literature.

Recommended control candidates:

- **Opdahl/Somorjai** for in-load AFM roughening + reversibility/path dependence;
- **BOPP Lin** or **PDMS-Yang** for spatial-scale or opposite-sign control.

The goal is not to create a polymer law; it is to protect the final interpretation against universal-sign and scale mistakes.

---

## 13. Material-selection state after Stage A

No material is selected.

### Skin

Advantages:

- strongest renderer-proximal evidence;
- measured directional surface-normal distributions;
- independent morphology and optical corroboration;
- likely easiest path to an externally defensible measured response.

Risks:

- biological specificity;
- strong anisotropy/material-frame dependence;
- reference-state/deformation-coordinate complexity;
- less aligned with the preferred clothing application.

### Cloth

Advantages:

- directly aligned with dynamic characters/clothing;
- multiple independent deformation/topography families;
- construction-specific response itself supports a constitutive framing;
- strong independent evidence that textile optics is directional.

Risks:

- no direct deformation-conditioned BRDF/NDF family found;
- severe microgeometry-vs-mesogeometry ambiguity;
- woven and knitted fabrics cannot share one generic response;
- porosity/opening/explicit geometry may dominate.

### Project decision

Carry **both** through Stage B. Evidence quality, domain compatibility, and representability — not preference — decide what can enter Gate 1.

If both survive, there is no requirement that the final paper use only one material class. That decision belongs later and should be made based on experimental clarity and the paper's method/evaluation design, not Stage-A search convenience.

---

## 14. Implications for the Constitutive Appearance method

The literature strengthens the central conceptual framing but also narrows what would count as a serious method.

### 14.1 The response must be material-specific

A model of the form

```text
roughness = f(strain)
```

for every surface is physically unsupported.

The literature instead favors:

```text
canonical material identity
+
shared/low-dimensional response conditioned on physical deformation
```

which is consistent with

\[
\theta_{i,t}=\theta_i^0+g_\psi(z_i,\epsilon_{i,t}).
\]

### 14.2 Time must remain a control, not the scientific variable

Nothing in the material literature suggests arbitrary animation time is the causal state. The later method must therefore preserve deformation conditioning and evaluate unseen deformation/motion.

### 14.3 Material frame may become essential

The strongest physical evidence is directional. If Stage B shows scalar reduction removes most of the response, the planned scalar-first prototype should be revised rather than forcing the evidence into scalar roughness.

### 14.4 Cloth may imply a richer representation than BRDF-only change

If Stage B shows that the dominant cloth response is yarn/loop/groove mesogeometry rather than microfacet-scale scattering, this does not make the constitutive concept false. It changes the representation question:

> should a constitutive appearance model predict both intrinsic scattering state and sub-resolution/effective surface structure?

That would be a later method-design decision and must not be made before the quantitative calibration.

---

## 15. Lab-experiment status

No material lab experiment is authorized or required at this checkpoint.

Stage B may resolve the physical law entirely from published measurements/released data, especially for the Nagano skin family.

A targeted material experiment becomes justified only if Stage B identifies a precise missing link that blocks an otherwise compelling material track — most plausibly cloth, where the current gap is:

```text
measured deformation-dependent textile morphology
                ->
quantitative deformation-dependent optical distribution
```

If that happens, the experiment must be designed specifically to close that gap and preregistered before collection. It should not be used merely to manufacture a larger visual effect.

This is separate from any later real-material validation capture required by the final paper.

---

## 16. Search coverage and limitations

### Covered in Stage A

Searches spanned, at minimum:

- skin / biological rough surfaces;
- woven textiles;
- knitted textiles;
- fibrous fabrics;
- coated/technical fabrics;
- elastomers / PDMS / rubber;
- polymer films/coatings;
- membranes;
- leather;
- engineered wrinkled/photonic/fibrous systems.

Search terminology crossed deformation concepts (`strain`, `stretch`, `compression`, `tension`, `uniaxial`, `biaxial`, `mechanical loading`) with optical/material concepts (`BRDF`, `reflectance`, `specular`, `roughness`, `NDF`, `surface normals`, `slope distribution`, `profilometry`, `AFM`, `microgeometry`, `angular scattering`, `polarization`).

Primary/publisher/institutional channels included ACM/USC ICT, PubMed/PMC, Optica, Elsevier/ScienceDirect, Taylor & Francis, ACS, RSC, J-STAGE, Springer, NIST, institutional repositories and author/project pages where available.

### Limitations retained

- no complete proprietary Scopus/Web of Science citation graph;
- incomplete forward-citation history for 2025–2026 papers;
- inaccessible historical full texts such as Ferguson/Barbenel;
- some older polymer full methods available only through abstract/metadata;
- this was not a formal PRISMA systematic review;
- no claim of global bibliometric exhaustiveness.

These limitations are compatible with the closure claim because the goal is practical scientific saturation for the frozen calibration question, not proof that every remotely related morphology paper has been enumerated.

---

## 17. Campaign provenance and supersession

### Source documents used to build this synthesis

The literature campaign proceeded through the following records:

1. `docs/constitutive_material_response_calibration_protocol.md` — frozen evidence/calibration protocol.
2. Stage-A v1 Deep Research report — broad discovery and first evidence-family map.
3. Stage-A repair and closure audit — repaired missed families and saturation overclaim.
4. Final Stage-A closure-only audit — normalized grades, completed most open chains, clarified cloth scale, exposed P-CAK.
5. P-CAK Stage-A closure micro-pass — screened/chained P-CAK and its polymer descendants.
6. This document — explicit closure-rule reconciliation and canonical Stage-A synthesis.

### Supersession rule

- The raw reports remain authoritative for their **search traces and what was known at each pass**.
- This document is authoritative for the **final evidence grading, closure status, material-class interpretation, and Stage-B handoff**.
- If a later primary-source extraction contradicts a Stage-A abstract-level statement, append a correction; do not silently rewrite the history.

---

## 18. Key references

This is a working reference list for the primary families carried forward. It is not intended as a complete bibliography of every screened paper.

### Skin

- Nagano et al. *Skin Microstructure Deformation with Displacement Map Convolution*. ACM Transactions on Graphics 34(4), 2015. DOI: `10.1145/2766894`.
- Maiti et al. *In vivo measurement of skin surface strain and sub-surface layer deformation induced by natural tissue stretching*. Journal of the Mechanical Behavior of Biomedical Materials 62, 2016. DOI: `10.1016/j.jmbbm.2016.05.035`.
- Corcuff, de Lacharrière & Lévêque. Human skin microrelief / extension study. Journal of Gerontology 46, 1991. DOI: `10.1093/geronj/46.6.M223`.
- Ferguson & Barbenel. *Skin surface patterns and the directional mechanical properties of the dermis*. In *Bioengineering and the Skin*, 1981, pp. 83–92. Full experimental text access-limited in Stage A.
- Federici et al. Applied Optics 38, 1999. DOI: `10.1364/AO.38.006653`.
- Guzelsu et al. Journal of Biomedical Optics 8, 2003. DOI: `10.1117/1.1527936`.
- Schulkin et al. Applied Optics 42, 2003. DOI: `10.1364/AO.42.005198`.
- Huo et al. Biomedical Optics Express 15, 2024. DOI: `10.1364/BOE.507361`.

### Textiles

- Moria et al. *Aerodynamic behaviour of stretchable sports fabrics*. Sports Technology 4. DOI: `10.1080/19346182.2012.725412`.
- Suzuki & Yamanobe. 2021 stretched-fabric surface study. DOI: `10.1299/jsmeshd.2021.A-4-1`.
- Suzuki/Yamanobe continuation. DOI: `10.5997/sposun.33.1_39`.
- Li/Mao/Zhou. Grooved technical-fabric stretch programme; AIAA Journal continuation. DOI: `10.2514/1.J065006`.
- Endo et al. Static textile angular-reflectance study. Journal of Textile Engineering 59, 2013. DOI: `10.4188/jte.59.75`.
- Woelfle et al. Stretched-knit color/background sensing. Frontiers in Computer Science, 2026. DOI: `10.3389/fcomp.2026.1841037`.

### Polymers / elastomers / controls

- Opdahl & Somorjai. Journal of Polymer Science B 39, 2001. DOI: `10.1002/polb.1200`.
- Dasari et al. Materials Science and Technology 18, 2002. DOI: `10.1179/026708302225003550`.
- van Tijum, Vellinga & De Hosson. Acta Materialia 55, 2007. DOI: `10.1016/j.actamat.2006.12.013`.
- Nishino et al. Review of Scientific Instruments 71, 2000. DOI: `10.1063/1.1150585`.
- Nishizawa et al. ACS Applied Materials & Interfaces 16, 2024. DOI: `10.1021/acsami.4c16013`.
- Morehouse et al. Journal of Membrane Science 280, 2006. DOI: `10.1016/j.memsci.2006.02.027`.
- Shadrinov & Fedorov. Plastics, Rubber and Composites 51, 2022. DOI: `10.1080/14658011.2021.2008704`.
- Yang et al. Stretched PDMS AFM study. Frontiers in Pharmacology 17, 2026. DOI: `10.3389/fphar.2026.1857290`.
- Cakmak, Wang & Iwakura. *Effect of Biaxial Stretching on Thickness Uniformity and Surface Roughness of PET and PPS Films*. International Polymer Processing 7, 1992. DOI: `10.3139/217.920327`.
- Wang & Cakmak. PMMA biaxial-stretch surface roughness. International Polymer Processing 8, 1993. DOI: `10.3139/217.930143`.
- Cakmak & Simhambhatla. PEEK uni/biaxial deformation and surface roughness. Polymer Engineering & Science 35, 1995. DOI: `10.1002/pen.760351910`.
- Zhou & Cakmak. PVDF/PMMA stretch/topography. Polymer Engineering & Science 47, 2007. DOI: `10.1002/pen.20935`.
- Lin et al. *Surface roughness and light transmission of biaxially oriented polypropylene films*. Polymer Engineering & Science 47, 2007. DOI: `10.1002/pen.20850`.
- Cui et al. PA510/SiO2 biaxial stretching, morphology and optical properties. Materials 14, 2021. DOI: `10.3390/ma14040705`.
- Harrell et al. PA6 stretch, crystallinity and surface roughness. Journal of Polymer Research 31, 2024. DOI: `10.1007/s10965-024-04017-0`.
- Li et al. Stretchable TPU nanofibre optical membrane. Chemical Engineering Journal 461, 2023. DOI: `10.1016/j.cej.2023.142095`.

### Specialist/context

- Martusciello & Comoretto. Stretchable distributed Bragg reflectors. ACS Applied Materials & Interfaces, 2024. DOI: `10.1021/acsami.4c13447`.
- Wang & Liu. *Deformation-dependent gel surface topography due to the elastocapillary and osmocapillary effects*. Soft Matter 20, 2024. DOI: `10.1039/D4SM00139G`.
- Basil-Jones et al. Leather collagen deformation under tensile strain. Journal of Agricultural and Food Chemistry, 2012. DOI: `10.1021/jf2039586`.

---

## 19. Final project checkpoint

As of this closure:

```text
old dynamic-light-transport mechanism campaign     COMPLETE / historical
Constitutive Appearance direction                  ACTIVE
LumiMotion substrate audit                         DONE
mesh strain interface + validation                 DONE
Joanna deformation characterization                DONE
Blender-version geometry fidelity                  DONE — PASS
material-response Stage A discovery                DONE — CLOSED
material-response Stage B quantitative calibration NEXT
Gate-1 preregistration                             NOT YET
Gate-1 rendering                                   NOT AUTHORIZED
material lab experiment                            NOT YET JUSTIFIED
method implementation                              NOT YET AUTHORIZED
```

The conceptual state is now clean:

> **We have a trustworthy deformation variable and independent physical evidence that deformation can change appearance-relevant surface state. We do not yet have the calibrated constitutive response needed to test whether that effect is observable and irreducible in inverse rendering. Stage B is the bridge between those two facts.**

