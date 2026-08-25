# Constitutive Appearance — Blender-Version Fidelity Runbook

## 1. Scope and frozen contract

This runbook prepares the comparison frozen in:

```text
docs/constitutive_blender_version_fidelity_prereg.md
```

That preregistration is authoritative. The scripts do not change its assets,
object-selection rule, frame schedule, Path-A definition, statistics,
tolerances, or PASS/PARTIAL/FAIL rules. This is an evaluated-geometry and strain
fidelity check, not Gate 1, rendering, training, or an appearance experiment.

The full four-scene Blender 4.4.0 extraction was not launched while preparing
this runbook. No Joanna `.blend` file was opened.

## 2. Immutable baseline

The Blender 3.6.13 baseline is:

```text
/home/fmb/projects/LumiMotion/outputs_constitutive/deformation_regime_v1
```

It physically resolves under:

```text
/data/fmb/LumiMotion/outputs_constitutive/deformation_regime_v1
```

The extraction driver freezes and verifies SHA-256 identities for the baseline
run manifest, all four scene manifests, and baseline summary before any Blender
process can launch. It also verifies each current source asset against the
source SHA-256 recorded by the baseline. The comparison analyzer verifies every
referenced baseline reference/frame package hash as it consumes the packages.

Nothing writes inside the baseline tree. A baseline identity mismatch is a hard
error, not permission to regenerate it.

## 3. Private Blender 4.4.0 output

The new output root is:

```text
/home/fmb/projects/LumiMotion/outputs_constitutive/blender_version_fidelity_v1
```

The repository path `outputs_constitutive` is an existing symlink to
`/data/fmb/LumiMotion/outputs_constitutive`. The driver requires this exact
physical symlink target and rejects an output inside the immutable baseline.
The generated tree is outside Git's physical worktree and remains private. Do
not force-add, upload, or redistribute its evaluated geometry packages.

Expected structure after extraction and analysis:

```text
outputs_constitutive/blender_version_fidelity_v1/
├── full_run.log
├── run_manifest.json
├── deformation_regime_summary.json
├── blender_version_fidelity_comparison.json
└── scenes/
    ├── hook/
    ├── jumpingjacks/
    ├── mouse/
    └── standup/
        ├── scene_manifest.json
        ├── frames/frame_000001.json ... frame_000150.json
        └── objects/object_*/reference.npz and frame_*.npz
```

## 4. Scripts and fixed software

The comparison uses:

```text
scripts_local/constitutive/strain/mesh_strain.py
scripts_local/constitutive/strain/blender_extract_path_a.py
scripts_local/constitutive/strain/run_deformation_regime.py
scripts_local/constitutive/strain/analyze_deformation_regime.py
scripts_local/constitutive/strain/run_blender_version_fidelity.py
scripts_local/constitutive/strain/compare_blender_version_fidelity.py
```

`mesh_strain.py` remains the only Path-A mathematical implementation.
`run_blender_version_fidelity.py` is a contract wrapper around the existing
deformation-regime worker, reusing its evaluated dependency-graph extraction,
mechanical object resolution, topology checks, Path-A call, row-preserving
packages, and resume behavior. It does not duplicate Path-A mathematics.

The fixed comparator is:

```text
executable: /home/fmb/blender-4.4.0-linux-x64/blender
version:    Blender 4.4.0
build hash: 05377985c527
platform:   Linux
```

The driver invokes it in background mode with automatic embedded-script
execution disabled. Neither new script calls a Blender save or render operator.

## 5. Exact tmux-ready extraction command

Run from any directory:

```bash
tmux new-session -d -s constitutive-blender-fidelity "/bin/bash -lc 'mkdir -p /home/fmb/projects/LumiMotion/outputs_constitutive/blender_version_fidelity_v1 && /home/fmb/miniconda3/envs/lumimotion/bin/python /home/fmb/projects/LumiMotion/scripts_local/constitutive/strain/run_blender_version_fidelity.py --output-root /home/fmb/projects/LumiMotion/outputs_constitutive/blender_version_fidelity_v1 >> /home/fmb/projects/LumiMotion/outputs_constitutive/blender_version_fidelity_v1/full_run.log 2>&1'"
```

Monitor the log without modifying outputs:

```bash
tail -f /home/fmb/projects/LumiMotion/outputs_constitutive/blender_version_fidelity_v1/full_run.log
```

This command launches all four frozen scenes, with reference frames
`hook=1`, `jumpingjacks=1`, `mouse=1`, `standup=75`, and every integer target
frame 1–150. It is the long job and must be launched by the user.

## 6. Exact comparison-analysis command

Run only after the extraction command has completed:

```bash
/home/fmb/miniconda3/envs/lumimotion/bin/python /home/fmb/projects/LumiMotion/scripts_local/constitutive/strain/compare_blender_version_fidelity.py --comparator-root /home/fmb/projects/LumiMotion/outputs_constitutive/blender_version_fidelity_v1 --output /home/fmb/projects/LumiMotion/outputs_constitutive/blender_version_fidelity_v1/blender_version_fidelity_comparison.json
```

The analyzer first independently recomputes the exact frozen deformation-regime
summary from the 4.4 packages and writes
`deformation_regime_summary.json`. It then computes structural equality,
4.4 reference integrity, jointly/singly valid accounting, weighted local
`d_epsilon`, every frozen summary comparison, raw evaluated-world-geometry
diagnostics, and the global frozen verdict.

No pooled four-scene statistic, alignment, rematching, frame removal, or
alternate percentile convention is used.

## 7. Restart and resume behavior

Rerun the exact extraction command to resume an interrupted extraction.

- The output run manifest must match the fidelity-preregistration hash, driver
  hash, Path-A/core and wrapper hashes, exact Blender identity, frame schedule,
  source hashes, and immutable baseline hashes. A mismatch is refused.
- A completed frame is skipped only after its status, object set, package
  presence, and SHA-256 are verified.
- An interrupted package lacking a completed frame record is recomputed and is
  accepted only if its arrays, shapes, dtypes, and values equal the existing
  file; otherwise overwrite is refused.
- A completed scene is skipped only after all 150 frame packages and reference
  packages are hash-verified.
- A scene marked unusable is not silently retried, repaired, or weakened into a
  partial scene. Review it before authorizing a new output root.
- The analysis refuses to overwrite a differing existing 4.4 summary or
  comparison result. An exactly identical result is retained.

Because script hashes are part of the run contract, do not edit the extraction,
Path-A, wrapper, or preregistration files after beginning a run and then resume
into the same output root.

## 8. Integrity and comparison checks

Before source access, the extraction driver checks:

- baseline top-level/scene manifest and summary SHA-256 values;
- baseline scene completeness, reference frames, subframe, and target range;
- current source-asset SHA-256 values against the immutable baseline;
- the exact Blender 4.4.0 version/build;
- the `outputs_constitutive` symlink target and separation from the baseline.

During extraction, the reused worker checks:

- the exact mechanical `MESH` plus `ARMATURE -> Armature` object rule and sorted
  name order;
- evaluated dependency-graph geometry in world coordinates;
- vertex, polygon, loop, triangle, winding, and row correspondence at all 150
  frames;
- reference identity and area residuals against `1e-5`;
- positive finite reference-area coverage;
- immutable package/hash and resume rules.

During analysis, the comparator checks:

- exact object/source/schedule agreement;
- exact canonical polygon/triangle integer values, shape, winding, and row
  order; integer storage dtype is reported but is diagnostic only;
- transitive all-frame topology equality: each version must match its own exact
  canonical topology and the two canonical topologies must match each other;
- independently recomputed 4.4 reference integrity;
- all package hashes and canonical row shapes;
- frozen baseline-area-weighted `p50/p95/p99/max(d_epsilon)`, with `p99 <= 1e-4`;
- every weighted/unweighted percentile and descriptive fraction against `1e-4`;
- scene valid-reference-area fraction against `1e-6`;
- unaligned raw world-vertex `d_x` diagnostics per scene/object.

## 9. Frozen verdict semantics

`PASS` requires structural equality, 4.4 reference integrity, every scene's
local `p99(d_epsilon) <= 1e-4`, and all frozen-summary fidelity gates. The
completed 3.6.13 characterization is then cross-version validated and retained.

`PARTIAL` requires structural equality, 4.4 reference integrity, and all
frozen-summary gates, but at least one local p99 gate fails. The descriptive
3.6.13 characterization is retained, but its per-face strain cannot be used for
later local constitutive/material coupling; future quantitative work uses 4.4
geometry.

`FAIL` results from any structural mismatch, 4.4 reference-integrity failure,
or frozen scene-summary failure. The 3.6.13 characterization is then not
canonical and must be recomputed/replaced with 4.4 output before proceeding.

No threshold may be relaxed after results are observed without preserving the
original verdict and creating a new preregistration version.

## 10. Files to bring back for review

Bring back these compact/private records after both commands finish:

1. `outputs_constitutive/blender_version_fidelity_v1/full_run.log`;
2. `outputs_constitutive/blender_version_fidelity_v1/run_manifest.json`;
3. all four new `scenes/*/scene_manifest.json` files, including any unusable
   scene record;
4. `outputs_constitutive/blender_version_fidelity_v1/deformation_regime_summary.json`;
5. `outputs_constitutive/blender_version_fidelity_v1/blender_version_fidelity_comparison.json`;
6. extraction and analysis exit codes.

Do not copy, commit, upload, or redistribute the per-frame NPZ geometry
packages. They remain private locally and are referenced by hash from the
compact comparison evidence.

## 11. Cheap preparation checks

Preparation is limited to syntax compilation, both `--help` paths, synthetic
topology/percentile/verdict tests, a no-asset driver dry run, exact Blender
`--version`, output-symlink/private-path verification, current source SHA-256
verification, and immutable baseline manifest/summary SHA-256 verification.
No actual 4.4 comparison, asset opening, geometry extraction, render, training,
or GPU job is part of preparation.
