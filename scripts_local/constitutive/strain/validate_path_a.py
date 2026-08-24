#!/usr/bin/env python3
"""Run the frozen Path-A numerical validation suite and write JSON results."""

import argparse
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from mesh_strain import InvalidReason, compute_face_strain, invalid_reason_labels


THRESHOLD = 1.0e-5


def rotations():
    ax, ay, az = np.deg2rad([19.0, -23.0, 37.0])
    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def jsonable(value):
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def positive_result(name, reference, target, triangles, expected_max, expected_min):
    strain = compute_face_strain(reference, target, triangles)
    valid = strain["valid"]
    invalid_fraction = float(1.0 - np.mean(valid))
    if np.any(valid):
        max_error_max = float(np.max(np.abs(strain["lambda_max"][valid] - expected_max)))
        max_error_min = float(np.max(np.abs(strain["lambda_min"][valid] - expected_min)))
        area_residual = float(np.max(np.abs(strain["area_identity_residual"][valid])))
    else:
        max_error_max = max_error_min = area_residual = math.inf
    stretch_pass = max_error_max <= THRESHOLD and max_error_min <= THRESHOLD and invalid_fraction == 0.0
    area_pass = area_residual <= THRESHOLD and invalid_fraction == 0.0
    return {
        "name": name,
        "expected_lambda_max": expected_max,
        "expected_lambda_min": expected_min,
        "lambda_max": strain["lambda_max"],
        "lambda_min": strain["lambda_min"],
        "log_strain": strain["log_strain"],
        "invalid_fraction": invalid_fraction,
        "invalid_reason": strain["invalid_reason"],
        "max_abs_lambda_max_error": max_error_max,
        "max_abs_lambda_min_error": max_error_min,
        "max_abs_area_identity_residual": area_residual,
        "roundoff_projection_count": strain["roundoff_projection_count"],
        "stretch_gate_pass": stretch_pass,
        "area_gate_pass": area_pass,
        "pass": stretch_pass and area_pass,
    }


def negative_result(name, reference, target, triangles, required_reason):
    strain = compute_face_strain(reference, target, triangles)
    invalid_fraction = float(1.0 - np.mean(strain["valid"]))
    descriptors_nan = bool(
        np.all(np.isnan(strain["lambda_max"]))
        and np.all(np.isnan(strain["lambda_min"]))
        and np.all(np.isnan(strain["log_strain"]))
    )
    reasons_match = bool(np.all((strain["invalid_reason"] & int(required_reason)) != 0))
    passed = invalid_fraction == 1.0 and descriptors_nan and reasons_match
    return {
        "name": name,
        "invalid_fraction": invalid_fraction,
        "invalid_reason": strain["invalid_reason"],
        "invalid_reason_labels": [invalid_reason_labels(v) for v in strain["invalid_reason"]],
        "required_reason": required_reason.name.lower(),
        "all_strain_descriptors_nan": descriptors_nan,
        "reason_gate_pass": reasons_match,
        "pass": passed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    reference = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=np.float64)
    triangles = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    R = rotations()
    translation = np.array([0.37, -1.20, 2.50], dtype=np.float64)
    rigid = reference @ R.T + translation
    stretch_matrix = np.diag([1.10, 1.00, 1.00])
    stretched = reference @ stretch_matrix.T
    stretched_rigid = stretched @ R.T + translation

    positive = [
        positive_result("identity", reference, reference.copy(), triangles, 1.0, 1.0),
        positive_result("rigid_motion", reference, rigid, triangles, 1.0, 1.0),
        positive_result("uniaxial_1.10", reference, stretched, triangles, 1.10, 1.0),
        positive_result("uniaxial_1.10_plus_rigid", reference, stretched_rigid, triangles, 1.10, 1.0),
    ]

    deg_ref = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]], dtype=np.float64)
    valid_ref = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64)
    one_face = np.array([[0, 1, 2]], dtype=np.int64)
    collapsed = valid_ref.copy()
    collapsed[2] = collapsed[1]
    nonfinite = valid_ref.copy()
    nonfinite[2, 1] = np.nan
    negative = [
        negative_result(
            "degenerate_reference", deg_ref, deg_ref.copy(), one_face, InvalidReason.REFERENCE_DEGENERATE
        ),
        negative_result("collapsed_target", valid_ref, collapsed, one_face, InvalidReason.TARGET_COLLAPSED),
        negative_result("nonfinite_target", valid_ref, nonfinite, one_face, InvalidReason.NONFINITE_TARGET),
    ]

    dtype_probe = compute_face_strain(reference, reference, triangles)
    float_arrays = [
        "F_surface", "C_surface", "lambda_max", "lambda_min", "log_strain",
        "area_reference", "area_deformed", "area_ratio", "stretch_area",
        "area_identity_residual", "condition_number_reference",
    ]
    dtype_pass = all(dtype_probe[name].dtype == np.float64 for name in float_arrays)
    all_gates_pass = all(item["pass"] for item in positive + negative) and dtype_pass
    report = {
        "schema": "lumimotion.constitutive.path_a_validation",
        "schema_version": 1,
        "contract": "docs/constitutive_strain_validation_prereg.md",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "authoritative_dtype": "float64",
        },
        "frozen_thresholds": {
            "positive_absolute": THRESHOLD,
            "area_quality_min": 1.0e-12,
            "condition_number_max": 1.0e8,
            "negative_eigenvalue_relative": 1.0e-12,
        },
        "positive_fixtures": positive,
        "negative_fixtures": negative,
        "dtype_gate": {"checked_arrays": float_arrays, "pass": dtype_pass},
        "roundoff_projection_count_total": int(sum(item["roundoff_projection_count"] for item in positive)),
        "core_verdict": "PASS" if all_gates_pass else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=jsonable, allow_nan=True) + "\n")
    print(json.dumps(report, indent=2, default=jsonable, allow_nan=True))
    return 0 if all_gates_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
