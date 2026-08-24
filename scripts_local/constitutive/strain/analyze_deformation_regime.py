#!/usr/bin/env python3
"""Compute the frozen deformation-regime summaries from private Path-A packages."""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from mesh_strain import INVALID_REASON_NAMES


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_INPUT = REPO_ROOT / "outputs_constitutive" / "deformation_regime_v1"
DEFAULT_SUMMARY_NAME = "deformation_regime_summary.json"
SCENE_ORDER = ("hook", "jumpingjacks", "mouse", "standup")
FRAME_RANGE = range(1, 151)

PRIMARY_PROBABILITIES = {
    "lambda_max": (0.50, 0.75, 0.90, 0.95, 0.99),
    "lambda_min": (0.01, 0.05, 0.10, 0.25, 0.50),
    "abs_log_stretch_max": (0.50, 0.75, 0.90, 0.95, 0.99),
    "abs_log_stretch_min": (0.50, 0.75, 0.90, 0.95, 0.99),
    "abs_log_area_change": (0.50, 0.75, 0.90, 0.95, 0.99),
    "log_anisotropy": (0.50, 0.75, 0.90, 0.95, 0.99),
    "max_abs_log_stretch": (0.50, 0.75, 0.90, 0.95, 0.99),
}
SECONDARY_PROBABILITIES = {
    "lambda_max": (0.50, 0.90, 0.95, 0.99),
    "lambda_min": (0.01, 0.05, 0.10, 0.50),
    "abs_log_stretch_max": (0.50, 0.90, 0.95, 0.99),
    "abs_log_stretch_min": (0.50, 0.90, 0.95, 0.99),
    "abs_log_area_change": (0.50, 0.90, 0.95, 0.99),
    "log_anisotropy": (0.50, 0.90, 0.95, 0.99),
    "max_abs_log_stretch": (0.50, 0.90, 0.95, 0.99),
}
THRESHOLDS = (
    ("lambda_max_ge_1.02", "lambda_max", ">=", 1.02),
    ("lambda_max_ge_1.05", "lambda_max", ">=", 1.05),
    ("lambda_max_ge_1.10", "lambda_max", ">=", 1.10),
    ("lambda_max_ge_1.20", "lambda_max", ">=", 1.20),
    ("lambda_min_le_0.98", "lambda_min", "<=", 0.98),
    ("lambda_min_le_0.95", "lambda_min", "<=", 0.95),
    ("lambda_min_le_0.90", "lambda_min", "<=", 0.90),
    ("lambda_min_le_0.80", "lambda_min", "<=", 0.80),
)


def sha256_file(path, block_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(str(path), "rb") as stream:
        while True:
            block = stream.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def percentile_key(probability):
    return "p{:02d}".format(int(round(100.0 * probability)))


def inverse_ecdf_percentiles(values, probabilities, weights=None):
    """Left-continuous inverse empirical CDF with no interpolation."""
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("percentile values must be a nonempty finite vector")
    if weights is None:
        weights = np.ones(values.size, dtype=np.float64)
    else:
        weights = np.asarray(weights, dtype=np.float64)
    if weights.shape != values.shape or not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
        raise ValueError("percentile weights must be finite, positive, and aligned")
    order = np.argsort(values, kind="mergesort")
    ordered_values = values[order]
    cumulative = np.cumsum(weights[order], dtype=np.float64)
    total = float(cumulative[-1])
    result = {}
    for probability in probabilities:
        if not 0.0 < probability <= 1.0:
            raise ValueError("percentile probability outside (0,1]")
        index = int(np.searchsorted(cumulative, probability * total, side="left"))
        index = min(index, ordered_values.size - 1)
        result[percentile_key(probability)] = float(ordered_values[index])
    return result


def invalid_counts(reason_values):
    return {
        name: int(np.count_nonzero(reason_values & int(bit)))
        for bit, name in INVALID_REASON_NAMES.items()
    }


def add_counts(destination, source):
    for key, value in source.items():
        destination[key] = destination.get(key, 0) + int(value)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_json_no_overwrite_or_equal(path, value):
    path = Path(path)
    if path.exists():
        existing = load_json(path)
        if existing != value:
            raise RuntimeError("existing analysis differs; refusing overwrite: {}".format(path))
        print("Existing summary is identical; retained: {}".format(path))
        return
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(path))


def quantities_from_package(package, valid):
    lambda_max = package["lambda_max"][valid].astype(np.float64, copy=False)
    lambda_min = package["lambda_min"][valid].astype(np.float64, copy=False)
    log_strain = package["log_strain"][valid].astype(np.float64, copy=False)
    quantities = {
        "lambda_max": lambda_max,
        "lambda_min": lambda_min,
        "abs_log_stretch_max": np.abs(log_strain[:, 0]),
        "abs_log_stretch_min": np.abs(log_strain[:, 1]),
        "abs_log_area_change": np.abs(log_strain[:, 2]),
        "log_anisotropy": log_strain[:, 3],
    }
    quantities["max_abs_log_stretch"] = np.maximum(
        quantities["abs_log_stretch_max"], quantities["abs_log_stretch_min"]
    )
    for name, values in quantities.items():
        if not np.all(np.isfinite(values)):
            raise RuntimeError("nonfinite valid values in {}".format(name))
    return quantities


def summarize_complete_scene(input_root, scene_id, manifest):
    scene_dir = input_root / "scenes" / scene_id
    object_records = manifest["objects"]
    if manifest.get("objects_in_frozen_order") != [item["object_name"] for item in object_records]:
        raise RuntimeError("object order mismatch in {}".format(scene_id))

    references = {}
    finite_area_by_object = {}
    for record in object_records:
        reference_path = scene_dir / record["reference_file"]
        if sha256_file(reference_path) != record["reference_file_sha256"]:
            raise RuntimeError("reference hash mismatch: {}".format(reference_path))
        reference = np.load(str(reference_path), allow_pickle=False)
        references[record["object_id"]] = reference
        area = reference["area_reference"].astype(np.float64, copy=False)
        finite_area_by_object[record["object_id"]] = float(
            np.sum(area[np.isfinite(area) & (area >= 0.0)])
        )

    value_chunks = {name: [] for name in PRIMARY_PROBABILITIES}
    weight_chunks = []
    per_object_frame = []
    scene_invalid_counts = {name: 0 for name in INVALID_REASON_NAMES.values()}
    valid_observations = 0
    invalid_observations = 0
    expected_observations = sum(item["triangle_count"] for item in object_records) * len(FRAME_RANGE)
    valid_weight = 0.0
    finite_weight = sum(finite_area_by_object.values()) * len(FRAME_RANGE)
    roundoff_count = 0

    for frame in FRAME_RANGE:
        status_path = scene_dir / "frames" / "frame_{:06d}.json".format(frame)
        if not status_path.is_file():
            raise RuntimeError("missing scheduled frame status: {}".format(status_path))
        status = load_json(status_path)
        if status.get("status") != "complete" or status.get("frame") != frame:
            raise RuntimeError("incomplete frame status: {}".format(status_path))
        status_by_object = {item["object_id"]: item for item in status["objects"]}
        if set(status_by_object) != {item["object_id"] for item in object_records}:
            raise RuntimeError("frame object set mismatch: {}".format(status_path))
        for object_record in object_records:
            object_id = object_record["object_id"]
            frame_record = status_by_object[object_id]
            if frame_record.get("topology_status") != "pass":
                raise RuntimeError("non-pass topology in complete scene")
            package_path = scene_dir / frame_record["file"]
            if sha256_file(package_path) != frame_record["sha256"]:
                raise RuntimeError("frame package hash mismatch: {}".format(package_path))
            with np.load(str(package_path), allow_pickle=False) as package:
                valid = package["valid"].astype(np.bool_, copy=False)
                reasons = package["invalid_reason"].astype(np.uint32, copy=False)
                reference_area = references[object_id]["area_reference"].astype(np.float64, copy=False)
                if valid.shape != reference_area.shape or reasons.shape != valid.shape:
                    raise RuntimeError("face-row shape mismatch: {}".format(package_path))
                if not np.all(np.isnan(package["lambda_max"][~valid])):
                    raise RuntimeError("invalid lambda_max rows are not NaN: {}".format(package_path))
                if not np.all(np.isnan(package["lambda_min"][~valid])):
                    raise RuntimeError("invalid lambda_min rows are not NaN: {}".format(package_path))
                if not np.all(np.isnan(package["log_strain"][~valid])):
                    raise RuntimeError("invalid log_strain rows are not NaN: {}".format(package_path))
                quantities = quantities_from_package(package, valid)
                weights = reference_area[valid]
                if np.any(~np.isfinite(weights)) or np.any(weights <= 0.0):
                    raise RuntimeError("valid rows have invalid reference-area weights")
                for name, values in quantities.items():
                    value_chunks[name].append(values.copy())
                weight_chunks.append(weights.copy())
                counts = invalid_counts(reasons)
                add_counts(scene_invalid_counts, counts)
                valid_count = int(np.count_nonzero(valid))
                invalid_count = int(np.count_nonzero(~valid))
                object_valid_weight = float(np.sum(weights))
                object_finite_weight = finite_area_by_object[object_id]
                projections = int(package["roundoff_projection_count"])
                per_object_frame.append({
                    "frame": frame,
                    "object_id": object_id,
                    "object_name": object_record["object_name"],
                    "topology_status": "pass",
                    "total_canonical_face_count": int(valid.size),
                    "valid_face_count": valid_count,
                    "invalid_face_count": invalid_count,
                    "valid_reference_area_numerator": object_valid_weight,
                    "finite_reference_area_denominator": object_finite_weight,
                    "valid_reference_area_fraction": (
                        object_valid_weight / object_finite_weight if object_finite_weight > 0.0 else None
                    ),
                    "invalid_reason_counts": counts,
                    "roundoff_projection_count": projections,
                    "package": str(package_path.relative_to(input_root)),
                    "package_sha256": frame_record["sha256"],
                })
                valid_observations += valid_count
                invalid_observations += invalid_count
                valid_weight += object_valid_weight
                roundoff_count += projections

    if valid_observations + invalid_observations != expected_observations:
        raise RuntimeError("scene observation accounting mismatch: {}".format(scene_id))
    values = {name: np.concatenate(chunks) for name, chunks in value_chunks.items()}
    weights = np.concatenate(weight_chunks)
    if weights.size != valid_observations:
        raise RuntimeError("valid weight/sample mismatch")

    primary = {}
    secondary = {}
    for name in PRIMARY_PROBABILITIES:
        primary[name] = {
            "percentiles": inverse_ecdf_percentiles(values[name], PRIMARY_PROBABILITIES[name], weights),
            "valid_sample_count": valid_observations,
            "reference_area_weight_denominator": valid_weight,
        }
        secondary[name] = {
            "percentiles": inverse_ecdf_percentiles(values[name], SECONDARY_PROBABILITIES[name]),
            "valid_sample_count": valid_observations,
            "equal_weight_denominator": valid_observations,
        }

    area_fractions = {}
    for label, quantity, operator, threshold in THRESHOLDS:
        mask = values[quantity] >= threshold if operator == ">=" else values[quantity] <= threshold
        numerator = float(np.sum(weights[mask]))
        area_fractions[label] = {
            "quantity": quantity,
            "operator": operator,
            "threshold": threshold,
            "reference_area_numerator": numerator,
            "valid_reference_area_denominator": valid_weight,
            "fraction": numerator / valid_weight,
            "valid_sample_count": valid_observations,
            "satisfying_sample_count": int(np.count_nonzero(mask)),
            "descriptive_only": True,
        }

    return {
        "status": "characterized",
        "reference_frame": manifest["reference_frame"],
        "target_frames": [1, 150],
        "scheduled_frame_count": 150,
        "successfully_correspondence_checked_frame_count": 150,
        "failed_frames": [],
        "objects_in_frozen_order": manifest["objects_in_frozen_order"],
        "expected_face_frame_observation_count": expected_observations,
        "valid_observation_count": valid_observations,
        "invalid_observation_count": invalid_observations,
        "total_valid_reference_area_weight": valid_weight,
        "total_finite_reference_area_weight": finite_weight,
        "scene_valid_reference_area_fraction": valid_weight / finite_weight,
        "invalid_reason_counts": scene_invalid_counts,
        "roundoff_projection_count": roundoff_count,
        "per_object_per_frame_validity": per_object_frame,
        "primary_reference_area_weighted": primary,
        "secondary_unweighted": secondary,
        "descriptive_reference_area_fractions": area_fractions,
        "scientific_pass_fail": None,
    }


def analyze(input_root):
    input_root = input_root.resolve()
    run_manifest_path = input_root / "run_manifest.json"
    if not run_manifest_path.is_file():
        raise RuntimeError("missing run manifest: {}".format(run_manifest_path))
    run_manifest = load_json(run_manifest_path)
    scenes = {}
    for scene_id in SCENE_ORDER:
        scene_manifest_path = input_root / "scenes" / scene_id / "scene_manifest.json"
        if not scene_manifest_path.is_file():
            scenes[scene_id] = {"status": "missing", "primary_statistics_computed": False}
            continue
        manifest = load_json(scene_manifest_path)
        if manifest.get("contract") != run_manifest.get("contract"):
            raise RuntimeError("scene/run contract mismatch: {}".format(scene_id))
        if manifest.get("status") == "unusable":
            scenes[scene_id] = {
                "status": "unusable",
                "failure": manifest.get("failure"),
                "primary_statistics_computed": False,
            }
        elif manifest.get("status") == "complete":
            scenes[scene_id] = summarize_complete_scene(input_root, scene_id, manifest)
        else:
            scenes[scene_id] = {
                "status": manifest.get("status", "unknown"),
                "primary_statistics_computed": False,
            }
    return {
        "schema": "lumimotion.constitutive.deformation_regime_summary",
        "schema_version": 1,
        "preregistration": "docs/constitutive_deformation_regime_prereg.md",
        "run_manifest_sha256": sha256_file(run_manifest_path),
        "analysis_script_sha256": sha256_file(SCRIPT_PATH),
        "percentile_convention": "left-continuous inverse empirical CDF; no interpolation",
        "primary_probabilities": {
            name: [percentile_key(q) for q in probabilities]
            for name, probabilities in PRIMARY_PROBABILITIES.items()
        },
        "secondary_probabilities": {
            name: [percentile_key(q) for q in probabilities]
            for name, probabilities in SECONDARY_PROBABILITIES.items()
        },
        "scene_order": list(SCENE_ORDER),
        "pooled_four_scene_statistic": None,
        "scientific_threshold": None,
        "scenes": scenes,
    }


def self_test():
    values = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    weights = np.array([1.0, 1.0, 7.0, 1.0], dtype=np.float64)
    weighted = inverse_ecdf_percentiles(values, (0.01, 0.50, 0.90, 0.99), weights)
    unweighted = inverse_ecdf_percentiles(values, (0.01, 0.50, 0.90, 0.99))
    expected_weighted = {"p01": 1.0, "p50": 3.0, "p90": 3.0, "p99": 4.0}
    expected_unweighted = {"p01": 1.0, "p50": 2.0, "p90": 4.0, "p99": 4.0}
    if weighted != expected_weighted or unweighted != expected_unweighted:
        raise AssertionError("inverse-ECDF self-test failed")
    if PRIMARY_PROBABILITIES["lambda_min"] != (0.01, 0.05, 0.10, 0.25, 0.50):
        raise AssertionError("primary lambda_min tail convention changed")
    if SECONDARY_PROBABILITIES["lambda_min"] != (0.01, 0.05, 0.10, 0.50):
        raise AssertionError("secondary lambda_min tail convention changed")
    result = {
        "pass": True,
        "weighted": weighted,
        "unweighted": unweighted,
        "primary_lambda_min": [percentile_key(q) for q in PRIMARY_PROBABILITIES["lambda_min"]],
        "secondary_lambda_min": [percentile_key(q) for q in SECONDARY_PROBABILITIES["lambda_min"]],
        "numpy_version": np.__version__,
    }
    print(json.dumps(result, indent=2))
    return 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze completed private packages using the frozen asymmetric percentile contract."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, help="Default: <input-root>/deformation_regime_summary.json")
    parser.add_argument("--self-test", action="store_true", help="Test percentile conventions on synthetic data only.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.self_test:
        return self_test()
    output = args.output.resolve() if args.output else args.input_root.resolve() / DEFAULT_SUMMARY_NAME
    summary = analyze(args.input_root)
    atomic_json_no_overwrite_or_equal(output, summary)
    print("Wrote frozen descriptive summary: {}".format(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
