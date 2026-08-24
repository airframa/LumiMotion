# Constitutive Appearance — Deformation-Regime Measurement Runbook

## 1. Scope and frozen contract

This runbook prepares the descriptive deformation-regime measurement preregistered in:

```text
docs/constitutive_deformation_regime_prereg.md
```

That document is authoritative. The scripts do not select scenes, objects, frames, formulas, thresholds, or statistics from observed strain. This is not Gate 1, an appearance experiment, or a scientific pass/fail test.

The full run was not launched while preparing this runbook. No author `.blend` file was opened and no Joanna strain value was computed.

## 2. Scripts involved

```text
scripts_local/constitutive/strain/mesh_strain.py
scripts_local/constitutive/strain/blender_extract_path_a.py
scripts_local/constitutive/strain/run_deformation_regime.py
scripts_local/constitutive/strain/analyze_deformation_regime.py
```

`mesh_strain.py` remains the single Path-A mathematical implementation. It was not duplicated or modified for this pipeline. The driver imports the validated evaluated-mesh and topology helpers from `blender_extract_path_a.py` and the Path-A function from `mesh_strain.py`.

`run_deformation_regime.py` has two internal roles:

- host orchestration: verifies the frozen binary/assets/output path and launches exactly one Blender process for each of the four frozen scenes;
- Blender worker: resolves all qualifying meshes, freezes the reference state, evaluates frames 1–150, checks topology, computes Path A, and writes resumable private packages.

`analyze_deformation_regime.py` verifies package hashes/accounting and computes only the frozen per-scene summaries. Its percentile routine is the preregistered non-interpolated inverse empirical CDF; it does not call `numpy.percentile`.

## 3. Private output directory

The frozen default is:

```text
/home/fmb/projects/LumiMotion/outputs_constitutive/deformation_regime_v1
```

The existing `.gitignore` rule `outputs*/` ignores this tree. A dry run confirmed that Git treats the path as ignored. It contains private evaluated geometry and must not be force-added, committed, uploaded, or redistributed.

## 4. Expected output structure

```text
outputs_constitutive/deformation_regime_v1/
├── run_manifest.json
├── deformation_regime_summary.json          # created only by analysis
└── scenes/
    ├── hook/
    ├── jumpingjacks/
    ├── mouse/
    └── standup/
        ├── scene_manifest.json
        ├── frames/
        │   ├── frame_000001.json
        │   └── ... frame_000150.json
        └── objects/
            ├── object_0000/
            │   ├── reference.npz
            │   ├── frame_000001.npz
            │   └── ... frame_000150.npz
            └── ...
```

Object directory IDs are storage identifiers only. Every manifest records the exact resolved Blender object name, qualifying Armature modifier(s), and frozen sorted object order.

Each frame NPZ preserves every canonical face row, including invalid rows with NaN strain descriptors and explicit reason bits. Frame JSON is written only after all object packages for that frame are complete and hashed.

## 5. Exact tmux-ready full-run command

Run from any directory:

```bash
tmux new-session -d -s constitutive-deformation-regime "/bin/bash -lc 'mkdir -p /home/fmb/projects/LumiMotion/outputs_constitutive/deformation_regime_v1 && /home/fmb/miniconda3/envs/lumimotion/bin/python /home/fmb/projects/LumiMotion/scripts_local/constitutive/strain/run_deformation_regime.py --output-root /home/fmb/projects/LumiMotion/outputs_constitutive/deformation_regime_v1 >> /home/fmb/projects/LumiMotion/outputs_constitutive/deformation_regime_v1/full_run.log 2>&1'"
```

Attach to monitor it:

```bash
tmux attach -t constitutive-deformation-regime
```

This command processes all four frozen scenes, with references `hook=1`, `jumpingjacks=1`, `mouse=1`, `standup=75`, and every integer target frame 1–150. It invokes the frozen `/home/fmb/blender-3.6.13-linux-x64/blender` with background mode and auto-execution disabled. It performs geometry extraction only; it does not render or save a `.blend` file.

Progress and errors are appended to the private `full_run.log`, so the same command remains suitable for a resume.

## 6. Exact subsequent analysis command

Run only after the extraction command finishes:

```bash
/home/fmb/miniconda3/envs/lumimotion/bin/python /home/fmb/projects/LumiMotion/scripts_local/constitutive/strain/analyze_deformation_regime.py --input-root /home/fmb/projects/LumiMotion/outputs_constitutive/deformation_regime_v1 --output /home/fmb/projects/LumiMotion/outputs_constitutive/deformation_regime_v1/deformation_regime_summary.json
```

The analysis emits separate summaries for each scene and explicitly emits no pooled four-scene statistic or scientific threshold. Complete scenes receive statistics; unusable, running, or missing scenes receive status/failure records without partial primary statistics.

## 7. Restart and resume behavior

Rerun the exact full-run command to resume after interruption.

- The run manifest must match the current preregistration hash, driver hash, Path-A core hash, validated-wrapper hash, Git revision, Blender identity, frame range, and source identity. A mismatch causes refusal rather than overwrite.
- A frame is considered completed only when its status JSON exists, says `complete`, names the full frozen object set, and every referenced NPZ matches its SHA-256 hash.
- Verified completed frames are skipped.
- If an NPZ exists without final frame status because interruption occurred between writes, the worker recomputes that frame in memory and accepts the file only if every stored array, dtype, and shape matches exactly. It otherwise refuses to overwrite it.
- A scene marked `complete` is skipped only after all reference/frame packages and hashes are reverified.
- A scene marked `unusable` is not silently retried or weakened into partial statistics. Review the failure before authorizing any new output root or revised contract.
- Neither extraction nor analysis silently overwrites a differing valid output. Re-running analysis retains an existing summary only when it is structurally identical.

## 8. Integrity checks

Before source access, the host checks:

- Blender executable exists and reports version `3.6.13`, build hash `791bdfd03f07`;
- all four exact preregistered asset paths exist;
- the output path is outside Git tracking or matches an ignore rule.

For each scene, the worker checks and records:

- source path, size, and SHA-256;
- exact object `Armature` and every mechanically qualifying `MESH` object;
- sorted resolved object names and qualifying modifier names;
- evaluated object-to-world geometry and evaluation provenance;
- canonical face topology and stable target correspondence at every frame;
- nonzero finite and valid reference-area coverage;
- same-reference identity and area residuals against the frozen `1e-5` integration tolerance;
- source/extractor/preregistration hashes and software provenance;
- per-object/per-frame counts, valid reference-area coverage, invalid-reason bit counts, roundoff counts, and package hashes.

Analysis re-verifies the run/scene contract, all reference and frame hashes, object/frame accounting, canonical row shapes, NaN invalid fields, finite valid fields, and positive reference-area weights before computing summaries.

The asymmetric percentiles are encoded explicitly:

- primary `lambda_max`: `p50/p75/p90/p95/p99`;
- primary `lambda_min`: `p01/p05/p10/p25/p50`;
- primary magnitudes: `p50/p75/p90/p95/p99`;
- secondary `lambda_max`: `p50/p90/p95/p99`;
- secondary `lambda_min`: `p01/p05/p10/p50`;
- secondary magnitudes: `p50/p90/p95/p99`.

## 9. What constitutes an unusable scene

The driver marks a scene unusable rather than producing partial primary statistics when any preregistered condition occurs, including:

- the frozen asset cannot be opened by the frozen binary or source identity changes;
- `Armature` is absent or no qualifying mesh exists;
- a qualifying object cannot be evaluated at any scheduled configuration;
- vertex/polygon/loop/triangle count, index, winding, object identity, or row order changes;
- required coordinates, transforms, hashes, or provenance cannot be recorded without repair/rematching;
- finite or valid reference-area coverage is zero;
- the reference-frame identity/area check exceeds `1e-5`;
- all 150 scheduled frames cannot be preserved and accounted for.

Ordinary face-level invalidity is retained and reported and does not alone make a scene unusable when the frozen coverage/correspondence requirements remain satisfied.

## 10. What to bring back for scientific review

After extraction and analysis, bring back:

1. `outputs_constitutive/deformation_regime_v1/run_manifest.json`;
2. all four `scene_manifest.json` files, including any unusable/failure record;
3. `outputs_constitutive/deformation_regime_v1/deformation_regime_summary.json`;
4. the extraction and analysis exit codes and any Blender/Python error output;
5. confirmation that the output package remains private and untracked.

Do not manually select frames, objects, percentiles, or “representative” extremes for review. The compact summary and manifests are sufficient for the first scientific review; private per-face geometry packages remain local unless a targeted diagnostic is explicitly authorized.

## 11. Cheap preparation checks completed

The following were run without opening an author asset or computing Joanna strain:

- Python syntax compilation for both new scripts;
- `--help` for both scripts;
- synthetic inverse-ECDF self-test, including the lower-tail `lambda_min` probability sets;
- driver `--dry-run`, which verified fixed paths/configuration and printed all four Blender commands without launching them;
- `git check-ignore -v` for the private output tree;
- frozen Blender `--version` verification.

No full or partial scene measurement was launched.
