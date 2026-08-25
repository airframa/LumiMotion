#!/usr/bin/env python3
"""Analyze the frozen Blender-3.6.13 versus 4.4.0 fidelity comparison."""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BASELINE_ROOT = REPO_ROOT / "outputs_constitutive" / "deformation_regime_v1"
DEFAULT_COMPARATOR_ROOT = REPO_ROOT / "outputs_constitutive" / "blender_version_fidelity_v2"
DEFAULT_OUTPUT_NAME = "blender_version_fidelity_comparison.json"
COMPARATOR_SUMMARY_NAME = "deformation_regime_summary.json"
SCENES = ("hook", "jumpingjacks", "mouse", "standup")
FRAMES = tuple(range(1, 151))
REFERENCE_FRAMES = {"hook": 1, "jumpingjacks": 1, "mouse": 1, "standup": 75}
IDENTITY_TOLERANCE = 1.0e-5
LOCAL_TOLERANCE = 1.0e-4
SUMMARY_PERCENTILE_TOLERANCE = 1.0e-4
SUMMARY_AREA_FRACTION_TOLERANCE = 1.0e-4
SUMMARY_VALID_AREA_TOLERANCE = 1.0e-6


if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_deformation_regime import (  # noqa: E402
    analyze as analyze_deformation_regime,
    atomic_json_no_overwrite_or_equal,
    inverse_ecdf_percentiles,
    sha256_file,
)
from run_blender_version_fidelity import (  # noqa: E402
    EXPECTED_BASELINE_HASHES,
    EXPECTED_BLENDER_BUILD_HASH,
    EXPECTED_BLENDER_VERSION,
    EXPECTED_SOURCE_HASHES,
    verify_baseline,
    verify_output_root,
    _load_regime_driver,
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def same_integer_topology(left, right):
    """Compare topology values/shape; record storage dtype separately."""
    left = np.asarray(left)
    right = np.asarray(right)
    if not np.issubdtype(left.dtype, np.integer) or not np.issubdtype(right.dtype, np.integer):
        return False
    return left.shape == right.shape and bool(np.array_equal(left, right))


def checked_npz(path, expected_hash):
    path = Path(path)
    if not path.is_file():
        raise RuntimeError("missing package: {}".format(path))
    actual = sha256_file(path)
    if actual != expected_hash:
        raise RuntimeError(
            "package hash mismatch: {} expected={} actual={}".format(path, expected_hash, actual)
        )
    return np.load(str(path), allow_pickle=False)


def frame_status(scene_root, frame):
    path = scene_root / "frames" / "frame_{:06d}.json".format(frame)
    if not path.is_file():
        raise RuntimeError("missing frame status: {}".format(path))
    status = load_json(path)
    if status.get("status") != "complete" or status.get("frame") != frame:
        raise RuntimeError("incomplete or wrong frame status: {}".format(path))
    return status


def records_by_name(records):
    result = {record["object_name"]: record for record in records}
    if len(result) != len(records):
        raise RuntimeError("duplicate object name in manifest/frame records")
    return result


def scalar_gate(value, tolerance):
    passed = bool(np.isfinite(value) and value <= tolerance)
    return {"value": float(value), "tolerance": tolerance, "pass": passed}


def reference_integrity(scene_root, manifest):
    reference_frame = manifest["reference_frame"]
    status = frame_status(scene_root, reference_frame)
    frame_by_name = records_by_name(status["objects"])
    per_object = []
    maxima = {"lambda_max": 0.0, "lambda_min": 0.0, "area": 0.0}
    total_valid = 0
    for object_record in manifest["objects"]:
        name = object_record["object_name"]
        frame_record = frame_by_name[name]
        package_path = scene_root / frame_record["file"]
        with checked_npz(package_path, frame_record["sha256"]) as package:
            valid = package["valid"].astype(np.bool_, copy=False)
            if not np.any(valid):
                raise RuntimeError("no valid reference-frame faces for {}".format(name))
            lmax = float(np.max(np.abs(package["lambda_max"][valid] - 1.0)))
            lmin = float(np.max(np.abs(package["lambda_min"][valid] - 1.0)))
            area = float(np.max(np.abs(package["area_identity_residual"][valid])))
            maxima["lambda_max"] = max(maxima["lambda_max"], lmax)
            maxima["lambda_min"] = max(maxima["lambda_min"], lmin)
            maxima["area"] = max(maxima["area"], area)
            total_valid += int(np.count_nonzero(valid))
            per_object.append({
                "object_name": name,
                "valid_face_count": int(np.count_nonzero(valid)),
                "max_abs_lambda_max_error": lmax,
                "max_abs_lambda_min_error": lmin,
                "max_abs_area_identity_residual": area,
                "tolerance": IDENTITY_TOLERANCE,
                "pass": max(lmax, lmin, area) <= IDENTITY_TOLERANCE,
            })
    gates = {
        "max_abs_lambda_max_error": scalar_gate(maxima["lambda_max"], IDENTITY_TOLERANCE),
        "max_abs_lambda_min_error": scalar_gate(maxima["lambda_min"], IDENTITY_TOLERANCE),
        "max_abs_area_identity_residual": scalar_gate(maxima["area"], IDENTITY_TOLERANCE),
    }
    return {
        "reference_frame": reference_frame,
        "valid_face_count": total_valid,
        "per_object": per_object,
        "gates": gates,
        "pass": all(item["pass"] for item in gates.values()),
    }


def compare_structure(scene_id, baseline_root, comparator_root, base_manifest, new_manifest):
    checks = []

    def check(name, passed, baseline=None, comparator=None, diagnostic=None):
        record = {"name": name, "pass": bool(passed)}
        if baseline is not None:
            record["baseline"] = baseline
        if comparator is not None:
            record["comparator"] = comparator
        if diagnostic is not None:
            record["diagnostic"] = diagnostic
        checks.append(record)

    base_names = base_manifest.get("objects_in_frozen_order")
    new_names = new_manifest.get("objects_in_frozen_order")
    check("selected_object_names_and_order", base_names == new_names, base_names, new_names)
    check(
        "source_asset_sha256",
        base_manifest.get("source", {}).get("sha256") == new_manifest.get("source", {}).get("sha256") == EXPECTED_SOURCE_HASHES[scene_id],
        base_manifest.get("source", {}).get("sha256"),
        new_manifest.get("source", {}).get("sha256"),
    )
    base_schedule = [base_manifest.get("reference_frame"), base_manifest.get("subframe"), base_manifest.get("target_frames")]
    new_schedule = [new_manifest.get("reference_frame"), new_manifest.get("subframe"), new_manifest.get("target_frames")]
    check("frame_schedule", base_schedule == new_schedule == [REFERENCE_FRAMES[scene_id], 0.0, [1, 150]], base_schedule, new_schedule)
    check("baseline_complete", base_manifest.get("status") == "complete" and base_manifest.get("completed_frame_count") == 150)
    check("comparator_complete", new_manifest.get("status") == "complete" and new_manifest.get("completed_frame_count") == 150)

    base_records = records_by_name(base_manifest.get("objects", []))
    new_records = records_by_name(new_manifest.get("objects", []))
    object_details = []
    if base_names == new_names and set(base_records) == set(new_records):
        for name in base_names:
            base_record = base_records[name]
            new_record = new_records[name]
            base_reference_path = baseline_root / "scenes" / scene_id / base_record["reference_file"]
            new_reference_path = comparator_root / "scenes" / scene_id / new_record["reference_file"]
            with checked_npz(base_reference_path, base_record["reference_file_sha256"]) as base_ref, checked_npz(
                new_reference_path, new_record["reference_file_sha256"]
            ) as new_ref:
                base_triangles = base_ref["triangles"]
                new_triangles = new_ref["triangles"]
                base_polygon_vertices = base_ref["polygon_vertices"]
                new_polygon_vertices = new_ref["polygon_vertices"]
                base_polygon_offsets = base_ref["polygon_offsets"]
                new_polygon_offsets = new_ref["polygon_offsets"]
                counts_base = {
                    "vertex": int(base_ref["reference_positions"].shape[0]),
                    "polygon": int(base_polygon_offsets.size - 1),
                    "loop": int(base_polygon_vertices.size),
                    "triangle": int(base_triangles.shape[0]),
                }
                counts_new = {
                    "vertex": int(new_ref["reference_positions"].shape[0]),
                    "polygon": int(new_polygon_offsets.size - 1),
                    "loop": int(new_polygon_vertices.size),
                    "triangle": int(new_triangles.shape[0]),
                }
                triangles_equal = same_integer_topology(base_triangles, new_triangles)
                polygons_equal = same_integer_topology(base_polygon_vertices, new_polygon_vertices) and same_integer_topology(base_polygon_offsets, new_polygon_offsets)
                object_pass = counts_base == counts_new and triangles_equal and polygons_equal
                object_details.append({
                    "object_name": name,
                    "counts_baseline": counts_base,
                    "counts_comparator": counts_new,
                    "polygon_indices_and_order_equal": polygons_equal,
                    "canonical_triangle_values_shape_winding_row_order_equal": triangles_equal,
                    "triangle_dtype_baseline_diagnostic": str(base_triangles.dtype),
                    "triangle_dtype_comparator_diagnostic": str(new_triangles.dtype),
                    "pass": object_pass,
                })
        check("reference_topology", all(item["pass"] for item in object_details), diagnostic=object_details)
    else:
        check("reference_topology", False, diagnostic="object set mismatch prevents comparison")

    frame_failures = []
    checked_frames = 0
    if base_names == new_names:
        for frame in FRAMES:
            try:
                base_status = frame_status(baseline_root / "scenes" / scene_id, frame)
                new_status = frame_status(comparator_root / "scenes" / scene_id, frame)
                base_frame = records_by_name(base_status["objects"])
                new_frame = records_by_name(new_status["objects"])
                if list(base_frame) != list(new_frame) or set(base_frame) != set(base_names):
                    raise RuntimeError("frame object set/order mismatch")
                for name in base_names:
                    if base_frame[name].get("topology_status") != "pass" or new_frame[name].get("topology_status") != "pass":
                        raise RuntimeError("non-pass topology status for {}".format(name))
                checked_frames += 1
            except Exception as error:
                frame_failures.append({"frame": frame, "reason": str(error)})
    check(
        "all_frame_topology_correspondence",
        checked_frames == 150 and not frame_failures,
        diagnostic={"scheduled": 150, "checked": checked_frames, "failed": frame_failures},
    )
    return {"checks": checks, "objects": object_details, "pass": all(item["pass"] for item in checks)}


def compare_local_and_geometry(scene_id, baseline_root, comparator_root, base_manifest, new_manifest):
    base_scene = baseline_root / "scenes" / scene_id
    new_scene = comparator_root / "scenes" / scene_id
    base_objects = records_by_name(base_manifest["objects"])
    new_objects = records_by_name(new_manifest["objects"])
    names = base_manifest["objects_in_frozen_order"]
    d_epsilon_chunks = []
    weight_chunks = []
    validity_counts = {"valid_in_both": 0, "valid_only_36": 0, "valid_only_44": 0, "invalid_in_both": 0}
    geometry_chunks = {name: [] for name in names}
    geometry_nonfinite = {name: 0 for name in names}
    geometry_expected_samples = {name: 0 for name in names}
    geometry_vertices_per_frame = {}
    bbox_diagonals = {}

    for name in names:
        base_record = base_objects[name]
        new_record = new_objects[name]
        with checked_npz(base_scene / base_record["reference_file"], base_record["reference_file_sha256"]) as base_ref, checked_npz(
            new_scene / new_record["reference_file"], new_record["reference_file_sha256"]
        ) as new_ref:
            if not same_integer_topology(base_ref["triangles"], new_ref["triangles"]):
                raise RuntimeError("triangle mismatch reached local comparison")
            reference_positions = base_ref["reference_positions"].astype(np.float64, copy=False)
            diagonal = float(np.linalg.norm(np.max(reference_positions, axis=0) - np.min(reference_positions, axis=0)))
            bbox_diagonals[name] = diagonal
            geometry_vertices_per_frame[name] = int(reference_positions.shape[0])
            if not np.isfinite(diagonal) or diagonal <= 0.0:
                raise RuntimeError("undefined baseline reference bbox diagonal for {}".format(name))
            base_area = base_ref["area_reference"].astype(np.float64, copy=False).copy()

        for frame in FRAMES:
            base_status = records_by_name(frame_status(base_scene, frame)["objects"])[name]
            new_status = records_by_name(frame_status(new_scene, frame)["objects"])[name]
            with checked_npz(base_scene / base_status["file"], base_status["sha256"]) as base_package, checked_npz(
                new_scene / new_status["file"], new_status["sha256"]
            ) as new_package:
                valid36 = base_package["valid"].astype(np.bool_, copy=False)
                valid44 = new_package["valid"].astype(np.bool_, copy=False)
                if valid36.shape != valid44.shape or valid36.shape != base_area.shape:
                    raise RuntimeError("face-row validity shape mismatch for {} frame {}".format(name, frame))
                joint = valid36 & valid44
                only36 = valid36 & ~valid44
                only44 = ~valid36 & valid44
                neither = ~valid36 & ~valid44
                validity_counts["valid_in_both"] += int(np.count_nonzero(joint))
                validity_counts["valid_only_36"] += int(np.count_nonzero(only36))
                validity_counts["valid_only_44"] += int(np.count_nonzero(only44))
                validity_counts["invalid_in_both"] += int(np.count_nonzero(neither))
                if np.any(joint):
                    log36 = base_package["log_strain"][joint, :2].astype(np.float64, copy=False)
                    log44 = new_package["log_strain"][joint, :2].astype(np.float64, copy=False)
                    differences = np.max(np.abs(log44 - log36), axis=1)
                    weights = base_area[joint]
                    if np.any(~np.isfinite(differences)) or np.any(~np.isfinite(weights)) or np.any(weights <= 0.0):
                        raise RuntimeError("invalid local-fidelity values or baseline weights")
                    d_epsilon_chunks.append(differences.copy())
                    weight_chunks.append(weights.copy())

                x36 = base_package["target_positions"].astype(np.float64, copy=False)
                x44 = new_package["target_positions"].astype(np.float64, copy=False)
                if x36.shape != x44.shape:
                    raise RuntimeError("world-position shape mismatch for {} frame {}".format(name, frame))
                dx = np.linalg.norm(x44 - x36, axis=1) / bbox_diagonals[name]
                geometry_expected_samples[name] += int(dx.size)
                geometry_nonfinite[name] += int(np.count_nonzero(~np.isfinite(dx)))
                geometry_chunks[name].append(dx[np.isfinite(dx)].copy())

    if not d_epsilon_chunks:
        raise RuntimeError("no jointly valid observations for {}".format(scene_id))
    d_epsilon = np.concatenate(d_epsilon_chunks)
    weights = np.concatenate(weight_chunks)
    local_percentiles = inverse_ecdf_percentiles(d_epsilon, (0.50, 0.95, 0.99), weights)
    local_percentiles["max"] = float(np.max(d_epsilon))
    local_gate = scalar_gate(local_percentiles["p99"], LOCAL_TOLERANCE)

    raw = []
    for name in names:
        values = np.concatenate(geometry_chunks[name]) if geometry_chunks[name] else np.empty(0)
        if values.size == 0:
            raise RuntimeError("no finite raw-geometry diagnostic values for {}".format(name))
        percentiles = inverse_ecdf_percentiles(values, (0.50, 0.95, 0.99))
        raw.append({
            "object_name": name,
            "reference_bbox_diagonal_36": bbox_diagonals[name],
            "frame_count": 150,
            "vertex_count_per_frame": geometry_vertices_per_frame[name],
            "total_sample_count": geometry_expected_samples[name],
            "finite_sample_count": int(values.size),
            "nonfinite_count": geometry_nonfinite[name],
            "median": percentiles["p50"],
            "p95": percentiles["p95"],
            "p99": percentiles["p99"],
            "max": float(np.max(values)),
            "diagnostic_only": True,
            "alignment_applied": False,
        })
    return {
        "validity_accounting": validity_counts,
        "d_epsilon": {
            "definition": "max(abs(log_stretch_max_44-log_stretch_max_36), abs(log_stretch_min_44-log_stretch_min_36))",
            "weight": "immutable Blender-3.6.13 canonical reference face area",
            "jointly_valid_sample_count": int(d_epsilon.size),
            "reference_area_weight_sum": float(np.sum(weights)),
            "weighted_percentiles": local_percentiles,
            "primary_gate": local_gate,
        },
        "raw_geometry_diagnostic": raw,
        "local_pass": local_gate["pass"],
    }


def difference_record(path, base_value, new_value, tolerance, provenance36=None, provenance44=None):
    difference = float(new_value) - float(base_value)
    return {
        "path": path,
        "blender_3_6_13": float(base_value),
        "blender_4_4_0": float(new_value),
        "signed_difference_44_minus_36": difference,
        "absolute_difference": abs(difference),
        "tolerance": tolerance,
        "pass": abs(difference) <= tolerance,
        "provenance_36": provenance36,
        "provenance_44": provenance44,
    }


def compare_summaries(scene_id, base_scene, new_scene):
    if base_scene.get("status") != "characterized" or new_scene.get("status") != "characterized":
        return {"pass": False, "reason": "both scene summaries must be characterized", "comparisons": []}
    comparisons = []
    for group in ("primary_reference_area_weighted", "secondary_unweighted"):
        for quantity, base_record in base_scene[group].items():
            new_record = new_scene[group][quantity]
            provenance_keys = [key for key in base_record if key != "percentiles"]
            provenance36 = {key: base_record[key] for key in provenance_keys}
            provenance44 = {key: new_record[key] for key in provenance_keys}
            for percentile, base_value in base_record["percentiles"].items():
                comparisons.append(difference_record(
                    "{}.{}.{}".format(group, quantity, percentile),
                    base_value,
                    new_record["percentiles"][percentile],
                    SUMMARY_PERCENTILE_TOLERANCE,
                    provenance36,
                    provenance44,
                ))
    for label, base_record in base_scene["descriptive_reference_area_fractions"].items():
        new_record = new_scene["descriptive_reference_area_fractions"][label]
        comparisons.append(difference_record(
            "descriptive_reference_area_fractions.{}.fraction".format(label),
            base_record["fraction"],
            new_record["fraction"],
            SUMMARY_AREA_FRACTION_TOLERANCE,
            {key: value for key, value in base_record.items() if key != "fraction"},
            {key: value for key, value in new_record.items() if key != "fraction"},
        ))
    comparisons.append(difference_record(
        "scene_valid_reference_area_fraction",
        base_scene["scene_valid_reference_area_fraction"],
        new_scene["scene_valid_reference_area_fraction"],
        SUMMARY_VALID_AREA_TOLERANCE,
        {
            "valid_weight": base_scene["total_valid_reference_area_weight"],
            "finite_weight": base_scene["total_finite_reference_area_weight"],
            "valid_samples": base_scene["valid_observation_count"],
            "invalid_samples": base_scene["invalid_observation_count"],
        },
        {
            "valid_weight": new_scene["total_valid_reference_area_weight"],
            "finite_weight": new_scene["total_finite_reference_area_weight"],
            "valid_samples": new_scene["valid_observation_count"],
            "invalid_samples": new_scene["invalid_observation_count"],
        },
    ))
    return {"scene_id": scene_id, "comparisons": comparisons, "pass": all(item["pass"] for item in comparisons)}


def frozen_verdict(structural_pass, reference_pass, local_pass, summary_pass):
    if not structural_pass or not reference_pass or not summary_pass:
        return "FAIL"
    if not local_pass:
        return "PARTIAL"
    return "PASS"


def analyze(comparator_root):
    comparator_root = verify_output_root(comparator_root)
    baseline_root = BASELINE_ROOT.resolve()
    baseline_hashes = verify_baseline(_load_regime_driver())
    run_manifest_path = comparator_root / "run_manifest.json"
    if not run_manifest_path.is_file():
        raise RuntimeError("missing 4.4 run manifest: {}".format(run_manifest_path))
    run_manifest = load_json(run_manifest_path)
    contract = run_manifest.get("contract", {})
    if contract.get("immutable_baseline_hashes") != baseline_hashes:
        raise RuntimeError("4.4 run manifest is not bound to the immutable baseline hashes")
    if contract.get("blender_version") != EXPECTED_BLENDER_VERSION or contract.get("blender_build_hash") != EXPECTED_BLENDER_BUILD_HASH:
        raise RuntimeError("4.4 run manifest Blender identity mismatch")

    baseline_summary_path = baseline_root / "deformation_regime_summary.json"
    baseline_summary = load_json(baseline_summary_path)
    comparator_summary = analyze_deformation_regime(comparator_root)
    comparator_summary_path = comparator_root / COMPARATOR_SUMMARY_NAME
    atomic_json_no_overwrite_or_equal(comparator_summary_path, comparator_summary)

    scenes = {}
    structural_all = reference_all = local_all = summary_all = True
    for scene_id in SCENES:
        base_manifest = load_json(baseline_root / "scenes" / scene_id / "scene_manifest.json")
        new_manifest = load_json(comparator_root / "scenes" / scene_id / "scene_manifest.json")
        structure = compare_structure(scene_id, baseline_root, comparator_root, base_manifest, new_manifest)
        structural_all = structural_all and structure["pass"]
        if structure["pass"]:
            reference = reference_integrity(comparator_root / "scenes" / scene_id, new_manifest)
            local = compare_local_and_geometry(scene_id, baseline_root, comparator_root, base_manifest, new_manifest)
        else:
            reference = {"pass": False, "not_computed_reason": "structural gate failed"}
            local = {"local_pass": False, "not_computed_reason": "structural gate failed"}
        summaries = compare_summaries(
            scene_id, baseline_summary["scenes"][scene_id], comparator_summary["scenes"][scene_id]
        )
        reference_all = reference_all and reference["pass"]
        local_all = local_all and local["local_pass"]
        summary_all = summary_all and summaries["pass"]
        scenes[scene_id] = {
            "source_sha256_36": base_manifest.get("source", {}).get("sha256"),
            "source_sha256_44": new_manifest.get("source", {}).get("sha256"),
            "objects_in_frozen_order_36": base_manifest.get("objects_in_frozen_order"),
            "objects_in_frozen_order_44": new_manifest.get("objects_in_frozen_order"),
            "frame_accounting": {
                "scheduled": 150,
                "completed_36": base_manifest.get("completed_frame_count"),
                "completed_44": new_manifest.get("completed_frame_count"),
            },
            "structural": structure,
            "reference_integrity_44": reference,
            "local_and_raw_geometry": local,
            "summary_fidelity": summaries,
            "scene_gate_state": {
                "structural_pass": structure["pass"],
                "reference_integrity_pass": reference["pass"],
                "local_p99_pass": local["local_pass"],
                "summary_pass": summaries["pass"],
            },
        }

    verdict = frozen_verdict(structural_all, reference_all, local_all, summary_all)
    return {
        "schema": "lumimotion.constitutive.blender_version_fidelity_comparison",
        "schema_version": 1,
        "preregistration": "docs/constitutive_blender_version_fidelity_prereg.md",
        "baseline_root": str(baseline_root),
        "comparator_root": str(comparator_root),
        "immutable_baseline_hashes": baseline_hashes,
        "comparator_run_manifest_sha256": sha256_file(run_manifest_path),
        "baseline_summary_sha256": sha256_file(baseline_summary_path),
        "comparator_summary_sha256": sha256_file(comparator_summary_path),
        "analysis_script_sha256": sha256_file(SCRIPT_PATH),
        "blender_36": {"version": "3.6.13", "build_hash": "791bdfd03f07"},
        "blender_44": {"version": EXPECTED_BLENDER_VERSION, "build_hash": EXPECTED_BLENDER_BUILD_HASH},
        "tolerances": {
            "reference_integrity": IDENTITY_TOLERANCE,
            "local_p99_d_epsilon": LOCAL_TOLERANCE,
            "summary_strain_percentile": SUMMARY_PERCENTILE_TOLERANCE,
            "summary_area_fraction": SUMMARY_AREA_FRACTION_TOLERANCE,
            "summary_valid_reference_area_fraction": SUMMARY_VALID_AREA_TOLERANCE,
        },
        "scenes": scenes,
        "global_gates": {
            "structural_pass": structural_all,
            "reference_integrity_pass": reference_all,
            "local_p99_pass": local_all,
            "summary_fidelity_pass": summary_all,
        },
        "verdict": verdict,
    }


def self_test():
    triangles64 = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    triangles32 = triangles64.astype(np.int32)
    if not same_integer_topology(triangles64, triangles32):
        raise AssertionError("same-value int32/int64 topology must pass")
    changed_winding = np.array([[0, 2, 1], [0, 2, 3]], dtype=np.int64)
    if same_integer_topology(triangles64, changed_winding):
        raise AssertionError("changed winding must fail")
    values = np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float64)
    weights = np.array([1.0, 7.0, 1.0, 1.0], dtype=np.float64)
    percentiles = inverse_ecdf_percentiles(values, (0.50, 0.95, 0.99), weights)
    if percentiles != {"p50": 1.0, "p95": 3.0, "p99": 3.0}:
        raise AssertionError("frozen inverse-ECDF synthetic test failed")
    verdicts = {
        "PASS": frozen_verdict(True, True, True, True),
        "PARTIAL": frozen_verdict(True, True, False, True),
        "FAIL_structural": frozen_verdict(False, True, True, True),
        "FAIL_reference": frozen_verdict(True, False, True, True),
        "FAIL_summary": frozen_verdict(True, True, True, False),
    }
    expected = {
        "PASS": "PASS",
        "PARTIAL": "PARTIAL",
        "FAIL_structural": "FAIL",
        "FAIL_reference": "FAIL",
        "FAIL_summary": "FAIL",
    }
    if verdicts != expected:
        raise AssertionError("frozen verdict synthetic tests failed")
    result = {
        "pass": True,
        "topology_same_values_int32_int64": True,
        "topology_changed_winding_rejected": True,
        "percentiles": percentiles,
        "verdicts": verdicts,
        "numpy_version": np.__version__,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Compute the frozen Blender-version structural, strain, summary, and geometry comparison."
    )
    parser.add_argument("--comparator-root", type=Path, default=DEFAULT_COMPARATOR_ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        help="Default: <comparator-root>/{}".format(DEFAULT_OUTPUT_NAME),
    )
    parser.add_argument("--self-test", action="store_true", help="Run synthetic comparison tests only.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.self_test:
        return self_test()
    comparator_root = verify_output_root(args.comparator_root)
    output = args.output.resolve() if args.output else comparator_root / DEFAULT_OUTPUT_NAME
    try:
        output.relative_to(comparator_root)
    except ValueError:
        raise RuntimeError("comparison output must remain inside the private 4.4 output tree")
    result = analyze(comparator_root)
    atomic_json_no_overwrite_or_equal(output, result)
    print("Wrote frozen Blender-version fidelity comparison: {}".format(output))
    print("Verdict: {}".format(result["verdict"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
