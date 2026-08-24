#!/usr/bin/env python3
"""Orchestrate the frozen Joanna deformation-regime extraction.

Host mode launches one Blender process per preregistered scene.  Blender-worker
mode resolves the frozen object set, reuses the validated extraction helpers and
Path-A mathematics, and writes resumable private frame packages.  This script
never calls a Blender save or render operation.
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BLENDER = Path("/home/fmb/blender-3.6.13-linux-x64/blender")
EXPECTED_BLENDER_VERSION = "3.6.13"
EXPECTED_BLENDER_BUILD_HASH = "791bdfd03f07"
DEFAULT_OUTPUT = REPO_ROOT / "outputs_constitutive" / "deformation_regime_v1"
PREREG = REPO_ROOT / "docs" / "constitutive_deformation_regime_prereg.md"
FIRST_FRAME = 1
LAST_FRAME = 150
SUBFRAME = 0.0
IDENTITY_TOLERANCE = 1.0e-5

SCENES = {
    "hook": {
        "asset": REPO_ROOT / "blend_files/blendfiles_v5_specular32/hook150_v5_specular32.blend",
        "reference_frame": 1,
    },
    "jumpingjacks": {
        "asset": REPO_ROOT / "blend_files/blendfiles_v5_specular32/jumpingjacks_v5_specular32.blend",
        "reference_frame": 1,
    },
    "mouse": {
        "asset": REPO_ROOT / "blend_files/blendfiles_v5_specular32/mouse_v5_specular32.blend",
        "reference_frame": 1,
    },
    "standup": {
        "asset": REPO_ROOT / "blend_files/blendfiles_v5_specular32/standup150_v5_specular32.blend",
        "reference_frame": 75,
    },
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path, block_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(str(path), "rb") as stream:
        while True:
            block = stream.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(path))


def git_revision():
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def contract_identity():
    core = SCRIPT_DIR / "mesh_strain.py"
    wrapper = SCRIPT_DIR / "blender_extract_path_a.py"
    return {
        "preregistration": str(PREREG.relative_to(REPO_ROOT)),
        "preregistration_sha256": sha256_file(PREREG),
        "driver_sha256": sha256_file(SCRIPT_PATH),
        "path_a_core_sha256": sha256_file(core),
        "validated_wrapper_sha256": sha256_file(wrapper),
        "git_revision": git_revision(),
        "frames": [FIRST_FRAME, LAST_FRAME],
        "subframe": SUBFRAME,
        "blender_path": str(BLENDER),
        "blender_version": EXPECTED_BLENDER_VERSION,
        "blender_build_hash": EXPECTED_BLENDER_BUILD_HASH,
    }


def blender_version_check():
    if not BLENDER.is_file():
        raise RuntimeError("frozen Blender executable is missing: {}".format(BLENDER))
    output = subprocess.check_output([str(BLENDER), "--version"], text=True)
    first_line = output.splitlines()[0] if output.splitlines() else ""
    build_line = next((line.strip() for line in output.splitlines() if "build hash:" in line), "")
    if first_line != "Blender {}".format(EXPECTED_BLENDER_VERSION):
        raise RuntimeError("unexpected Blender version: {}".format(first_line))
    if EXPECTED_BLENDER_BUILD_HASH not in build_line:
        raise RuntimeError("unexpected Blender build hash: {}".format(build_line))
    return {"first_line": first_line, "build_hash_line": build_line}


def output_is_private(output_root):
    output_root = output_root.resolve()
    try:
        relative = output_root.relative_to(REPO_ROOT)
    except ValueError:
        return True, "outside_repository"
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", str(relative)],
        check=False,
    )
    return result.returncode == 0, "git_check_ignore"


def worker_command(scene_id, output_root):
    scene = SCENES[scene_id]
    return [
        str(BLENDER),
        "--background",
        "--disable-autoexec",
        str(scene["asset"]),
        "--python",
        str(SCRIPT_PATH),
        "--",
        "--blender-worker",
        "--scene-id",
        scene_id,
        "--output-root",
        str(output_root.resolve()),
    ]


def host_main(args):
    output_root = args.output_root.resolve()
    private, private_reason = output_is_private(output_root)
    if not private:
        raise RuntimeError("output path is inside Git and is not ignored: {}".format(output_root))
    version = blender_version_check()
    missing = [str(scene["asset"]) for scene in SCENES.values() if not scene["asset"].is_file()]
    if missing:
        raise RuntimeError("missing frozen source assets: {}".format(missing))

    commands = {scene_id: worker_command(scene_id, output_root) for scene_id in SCENES}
    if args.dry_run:
        print(json.dumps({
            "dry_run": True,
            "assets_opened": False,
            "output_root": str(output_root),
            "output_private_check": private_reason,
            "blender": version,
            "scenes": {
                scene_id: {
                    "asset": str(SCENES[scene_id]["asset"]),
                    "reference_frame": SCENES[scene_id]["reference_frame"],
                    "target_frames": [FIRST_FRAME, LAST_FRAME],
                    "command": command,
                }
                for scene_id, command in commands.items()
            },
        }, indent=2))
        return 0

    output_root.mkdir(parents=True, exist_ok=True)
    run_manifest_path = output_root / "run_manifest.json"
    identity = contract_identity()
    if run_manifest_path.exists():
        existing = json.loads(run_manifest_path.read_text(encoding="utf-8"))
        if existing.get("contract") != identity:
            raise RuntimeError("existing run manifest does not match the frozen contract; refusing overwrite")
    else:
        atomic_json(run_manifest_path, {
            "schema": "lumimotion.constitutive.deformation_regime_run",
            "schema_version": 1,
            "created_utc": utc_now(),
            "contract": identity,
            "scene_order": list(SCENES),
            "commands": commands,
            "output_private_check": private_reason,
        })

    failures = []
    for scene_id, command in commands.items():
        print("Launching frozen scene extraction: {}".format(scene_id), flush=True)
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            failures.append({"scene_id": scene_id, "returncode": completed.returncode})
            scene_manifest = output_root / "scenes" / scene_id / "scene_manifest.json"
            if not scene_manifest.exists():
                source = SCENES[scene_id]["asset"]
                atomic_json(scene_manifest, {
                    "schema": "lumimotion.constitutive.deformation_regime_scene",
                    "schema_version": 1,
                    "scene_id": scene_id,
                    "status": "unusable",
                    "created_utc": utc_now(),
                    "updated_utc": utc_now(),
                    "contract": identity,
                    "source": {
                        "path": str(source.resolve()),
                        "size": source.stat().st_size,
                        "sha256": sha256_file(source),
                    },
                    "failure": {
                        "reason": "Blender exited before creating a scene manifest",
                        "returncode": completed.returncode,
                        "frame": None,
                        "object_name": None,
                    },
                    "source_blend_saved_or_modified": False,
                })
    if failures:
        print(json.dumps({"scene_failures": failures}, indent=2), file=sys.stderr)
        return 2
    return 0


def _atomic_npz(path, arrays):
    import numpy as np

    path = Path(path)
    temporary = path.with_name(path.stem + ".tmp.npz")
    np.savez_compressed(str(temporary), **arrays)
    os.replace(str(temporary), str(path))


def _arrays_equal(path, arrays):
    import numpy as np

    try:
        with np.load(str(path), allow_pickle=False) as stored:
            if set(stored.files) != set(arrays):
                return False
            for name, expected in arrays.items():
                actual = stored[name]
                expected = np.asarray(expected)
                if actual.shape != expected.shape or actual.dtype != expected.dtype:
                    return False
                if np.issubdtype(actual.dtype, np.inexact):
                    equal = np.array_equal(actual, expected, equal_nan=True)
                else:
                    equal = np.array_equal(actual, expected)
                if not equal:
                    return False
    except (OSError, ValueError, KeyError):
        return False
    return True


def _safe_existing_npz(path, arrays):
    if path.exists():
        if not _arrays_equal(path, arrays):
            raise RuntimeError("existing output differs; refusing overwrite: {}".format(path))
    else:
        _atomic_npz(path, arrays)


def _reference_arrays(extracted, strain):
    import numpy as np

    polygon_flat = np.array(
        [index for polygon in extracted["polygons"] for index in polygon], dtype=np.int64
    )
    polygon_offsets = np.zeros(len(extracted["polygons"]) + 1, dtype=np.int64)
    polygon_offsets[1:] = np.cumsum(
        [len(polygon) for polygon in extracted["polygons"]], dtype=np.int64
    )
    return {
        "reference_positions": extracted["positions"],
        "triangles": extracted["triangles"],
        "polygon_vertices": polygon_flat,
        "polygon_offsets": polygon_offsets,
        "reference_matrix_world": extracted["matrix_world"],
        "reference_tangent_basis": strain["reference_tangent_basis"],
        "area_reference": strain["area_reference"],
        "q_area_reference": strain["q_area_reference"],
        "condition_number_reference": strain["condition_number_reference"],
        "reference_valid": strain["valid"],
        "reference_invalid_reason": strain["invalid_reason"],
    }


def _frame_arrays(extracted, strain):
    return {
        "target_positions": extracted["positions"],
        "target_matrix_world": extracted["matrix_world"],
        "F_surface": strain["F_surface"],
        "C_surface": strain["C_surface"],
        "lambda_max": strain["lambda_max"],
        "lambda_min": strain["lambda_min"],
        "log_strain": strain["log_strain"],
        "area_deformed": strain["area_deformed"],
        "area_ratio": strain["area_ratio"],
        "stretch_area": strain["stretch_area"],
        "area_identity_residual": strain["area_identity_residual"],
        "q_area_target": strain["q_area_target"],
        "valid": strain["valid"],
        "invalid_reason": strain["invalid_reason"],
        "roundoff_projection_count": strain["roundoff_projection_count"],
    }


def _invalid_counts(reason_values, reason_names):
    import numpy as np

    return {
        name: int(np.count_nonzero(reason_values & int(bit)))
        for bit, name in reason_names.items()
    }


def _validity_record(strain, area_reference, reason_names):
    import numpy as np

    finite_area = np.isfinite(area_reference) & (area_reference >= 0.0)
    finite_denominator = float(np.sum(area_reference[finite_area]))
    valid_area = float(np.sum(area_reference[strain["valid"]]))
    return {
        "total_face_count": int(strain["valid"].size),
        "valid_face_count": int(np.count_nonzero(strain["valid"])),
        "invalid_face_count": int(np.count_nonzero(~strain["valid"])),
        "valid_reference_area_numerator": valid_area,
        "finite_reference_area_denominator": finite_denominator,
        "valid_reference_area_fraction": (
            valid_area / finite_denominator if finite_denominator > 0.0 else None
        ),
        "nonfinite_reference_area_count": int(np.count_nonzero(~np.isfinite(area_reference))),
        "invalid_reason_counts": _invalid_counts(strain["invalid_reason"], reason_names),
        "roundoff_projection_count": int(strain["roundoff_projection_count"]),
    }


def _resolved_objects(bpy):
    armature = bpy.data.objects.get("Armature")
    if armature is None:
        raise RuntimeError("frozen target object 'Armature' is absent")
    names = []
    qualifying_modifiers = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        modifiers = [
            modifier.name
            for modifier in obj.modifiers
            if modifier.type == "ARMATURE" and getattr(modifier, "object", None) is armature
        ]
        if modifiers:
            names.append(obj.name)
            qualifying_modifiers[obj.name] = modifiers
    names.sort()
    if not names:
        raise RuntimeError("no MESH object has an ARMATURE modifier targeting 'Armature'")
    return names, qualifying_modifiers


def _mark_unusable(scene_manifest_path, manifest, reason, frame=None, object_name=None):
    manifest["status"] = "unusable"
    manifest["updated_utc"] = utc_now()
    manifest["failure"] = {
        "reason": str(reason),
        "frame": frame,
        "object_name": object_name,
    }
    atomic_json(scene_manifest_path, manifest)


def _verify_complete_scene_packages(scene_dir, manifest):
    object_records = manifest.get("objects", [])
    expected_object_ids = {record["object_id"] for record in object_records}
    if not object_records or manifest.get("completed_frame_count") != 150:
        raise RuntimeError("completed scene manifest is incomplete")
    for object_record in object_records:
        reference = scene_dir / object_record["reference_file"]
        if not reference.is_file() or sha256_file(reference) != object_record["reference_file_sha256"]:
            raise RuntimeError("completed reference package hash mismatch: {}".format(reference))
    for frame in range(FIRST_FRAME, LAST_FRAME + 1):
        status_path = scene_dir / "frames" / "frame_{:06d}.json".format(frame)
        if not status_path.is_file():
            raise RuntimeError("completed scene is missing frame status: {}".format(status_path))
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") != "complete" or status.get("frame") != frame:
            raise RuntimeError("completed scene has invalid frame status: {}".format(status_path))
        if {record["object_id"] for record in status.get("objects", [])} != expected_object_ids:
            raise RuntimeError("completed frame object set mismatch: {}".format(status_path))
        for record in status.get("objects", []):
            package = scene_dir / record["file"]
            if not package.is_file() or sha256_file(package) != record["sha256"]:
                raise RuntimeError("completed frame package hash mismatch: {}".format(package))


def blender_worker(args):
    import bpy
    import numpy as np

    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    from blender_extract_path_a import (
        extract_evaluated_object,
        hash_array,
        require_correspondence,
        set_configuration,
        topology_signature,
    )
    from mesh_strain import INVALID_REASON_NAMES, compute_face_strain

    scene_id = args.scene_id
    frozen = SCENES[scene_id]
    output_root = args.output_root.resolve()
    scene_dir = output_root / "scenes" / scene_id
    scene_dir.mkdir(parents=True, exist_ok=True)
    scene_manifest_path = scene_dir / "scene_manifest.json"
    actual_source = Path(bpy.data.filepath).resolve()
    expected_source = frozen["asset"].resolve()
    if actual_source != expected_source:
        raise RuntimeError("opened source path does not match frozen asset")
    actual_build_hash = (
        bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash)
    )
    if bpy.app.version_string != EXPECTED_BLENDER_VERSION or actual_build_hash != EXPECTED_BLENDER_BUILD_HASH:
        raise RuntimeError("Blender version/build does not match frozen contract")

    source_identity = {
        "path": str(actual_source),
        "size": actual_source.stat().st_size,
        "sha256": sha256_file(actual_source),
    }
    identity = contract_identity()
    if scene_manifest_path.exists():
        manifest = json.loads(scene_manifest_path.read_text(encoding="utf-8"))
        if manifest.get("contract") != identity or manifest.get("source") != source_identity:
            raise RuntimeError("existing scene output does not match source/contract; refusing overwrite")
        if manifest.get("status") == "complete":
            _verify_complete_scene_packages(scene_dir, manifest)
            print("Scene already complete and contract-matched: {}".format(scene_id))
            return 0
        if manifest.get("status") == "unusable":
            raise RuntimeError("scene is already marked unusable; use a new output root after review")
    else:
        manifest = {
            "schema": "lumimotion.constitutive.deformation_regime_scene",
            "schema_version": 1,
            "scene_id": scene_id,
            "status": "running",
            "created_utc": utc_now(),
            "updated_utc": utc_now(),
            "source": source_identity,
            "contract": identity,
            "reference_frame": frozen["reference_frame"],
            "target_frames": [FIRST_FRAME, LAST_FRAME],
            "subframe": SUBFRAME,
            "blender": {
                "executable": str(Path(bpy.app.binary_path).resolve()),
                "version": bpy.app.version_string,
                "build_hash": actual_build_hash,
                "platform": platform.platform(),
                "dependency_graph": "evaluated_get + to_mesh",
                "autoexec_disabled": True,
            },
            "scene": bpy.context.scene.name,
            "view_layer": bpy.context.view_layer.name,
            "source_blend_saved_or_modified": False,
        }
        atomic_json(scene_manifest_path, manifest)

    try:
        object_names, qualifying_modifiers = _resolved_objects(bpy)
        if manifest.get("objects_in_frozen_order") not in (None, object_names):
            raise RuntimeError("resolved object set/order changed across resume")
        manifest["objects_in_frozen_order"] = object_names
        manifest["qualifying_armature_modifiers"] = qualifying_modifiers
        set_configuration(frozen["reference_frame"], SUBFRAME)
        references = {name: extract_evaluated_object(name) for name in object_names}
        reference_strain = {
            name: compute_face_strain(
                references[name]["positions"],
                references[name]["positions"],
                references[name]["triangles"],
            )
            for name in object_names
        }
        manifest["objects"] = []
        for index, name in enumerate(object_names):
            object_id = "object_{:04d}".format(index)
            object_dir = scene_dir / "objects" / object_id
            object_dir.mkdir(parents=True, exist_ok=True)
            arrays = _reference_arrays(references[name], reference_strain[name])
            reference_path = object_dir / "reference.npz"
            _safe_existing_npz(reference_path, arrays)
            validity = _validity_record(
                reference_strain[name], reference_strain[name]["area_reference"], INVALID_REASON_NAMES
            )
            if validity["finite_reference_area_denominator"] <= 0.0:
                raise RuntimeError("finite reference-area denominator is zero for {}".format(name))
            if validity["valid_reference_area_numerator"] <= 0.0:
                raise RuntimeError("valid reference-area coverage is zero for {}".format(name))
            valid = reference_strain[name]["valid"]
            if np.any(valid):
                max_lmax = float(np.max(np.abs(reference_strain[name]["lambda_max"][valid] - 1.0)))
                max_lmin = float(np.max(np.abs(reference_strain[name]["lambda_min"][valid] - 1.0)))
                max_area = float(np.max(np.abs(reference_strain[name]["area_identity_residual"][valid])))
            else:
                max_lmax = max_lmin = max_area = float("inf")
            if max(max_lmax, max_lmin, max_area) > IDENTITY_TOLERANCE:
                raise RuntimeError("reference identity gate failed for {}".format(name))
            manifest["objects"].append({
                "object_id": object_id,
                "object_name": name,
                "reference_file": str(reference_path.relative_to(scene_dir)),
                "reference_file_sha256": sha256_file(reference_path),
                "vertex_count": references[name]["vertex_count"],
                "triangle_count": references[name]["triangle_count"],
                "topology_sha256": topology_signature(references[name])[0],
                "reference_positions_sha256_float64_le": hash_array(
                    references[name]["positions"], "<f8"
                ),
                "triangles_sha256_int64_le": hash_array(references[name]["triangles"], "<i8"),
                "reference_evaluation": references[name]["evaluation_provenance"],
                "reference_validity": validity,
                "identity_check": {
                    "max_abs_lambda_max_error": max_lmax,
                    "max_abs_lambda_min_error": max_lmin,
                    "max_abs_area_identity_residual": max_area,
                    "tolerance": IDENTITY_TOLERANCE,
                    "pass": True,
                },
            })
        manifest["updated_utc"] = utc_now()
        atomic_json(scene_manifest_path, manifest)

        object_by_name = {item["object_name"]: item for item in manifest["objects"]}
        for frame in range(FIRST_FRAME, LAST_FRAME + 1):
            frame_status_path = scene_dir / "frames" / "frame_{:06d}.json".format(frame)
            if frame_status_path.exists():
                status = json.loads(frame_status_path.read_text(encoding="utf-8"))
                if status.get("status") != "complete" or status.get("frame") != frame:
                    raise RuntimeError("invalid existing frame status: {}".format(frame_status_path))
                for record in status["objects"]:
                    package = scene_dir / record["file"]
                    if not package.is_file() or sha256_file(package) != record["sha256"]:
                        raise RuntimeError("completed frame package hash mismatch: {}".format(package))
                print("Resume: verified frame {:03d}".format(frame), flush=True)
                continue

            set_configuration(frame, SUBFRAME)
            targets = {name: extract_evaluated_object(name) for name in object_names}
            frame_records = []
            for name in object_names:
                try:
                    require_correspondence(references[name], targets[name], name)
                except Exception as error:
                    _mark_unusable(scene_manifest_path, manifest, error, frame=frame, object_name=name)
                    return 2
                strain = compute_face_strain(
                    references[name]["positions"], targets[name]["positions"], references[name]["triangles"]
                )
                object_record = object_by_name[name]
                package = (
                    scene_dir / "objects" / object_record["object_id"] / "frame_{:06d}.npz".format(frame)
                )
                arrays = _frame_arrays(targets[name], strain)
                _safe_existing_npz(package, arrays)
                frame_records.append({
                    "object_id": object_record["object_id"],
                    "object_name": name,
                    "file": str(package.relative_to(scene_dir)),
                    "sha256": sha256_file(package),
                    "target_positions_sha256_float64_le": hash_array(
                        targets[name]["positions"], "<f8"
                    ),
                    "topology_status": "pass",
                    "target_evaluation": targets[name]["evaluation_provenance"],
                    "validity": _validity_record(strain, reference_strain[name]["area_reference"], INVALID_REASON_NAMES),
                })
            atomic_json(frame_status_path, {
                "schema_version": 1,
                "scene_id": scene_id,
                "frame": frame,
                "subframe": SUBFRAME,
                "status": "complete",
                "objects": frame_records,
                "completed_utc": utc_now(),
            })
            print("Completed frame {:03d}".format(frame), flush=True)

        manifest["status"] = "complete"
        manifest["completed_utc"] = utc_now()
        manifest["updated_utc"] = utc_now()
        manifest["completed_frame_count"] = LAST_FRAME - FIRST_FRAME + 1
        atomic_json(scene_manifest_path, manifest)
        return 0
    except Exception as error:
        if manifest.get("status") != "unusable":
            _mark_unusable(scene_manifest_path, manifest, error)
        print("Scene unusable: {}: {}".format(scene_id, error), file=sys.stderr)
        return 2


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run or dry-run the frozen four-scene deformation-regime extraction."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true", help="Validate paths/version and print commands; open no assets.")
    parser.add_argument("--blender-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--scene-id", choices=list(SCENES), help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "bpy" in sys.modules and "--" in sys.argv else None
    args = parse_args(argv)
    if args.blender_worker:
        if args.scene_id is None:
            raise RuntimeError("--scene-id is required in Blender-worker mode")
        return blender_worker(args)
    return host_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
