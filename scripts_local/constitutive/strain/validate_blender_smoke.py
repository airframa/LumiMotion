#!/usr/bin/env python3
"""Validate the controlled Blender wrapper package against the frozen gate."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


THRESHOLD = 1.0e-5


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.package / "manifest.json").read_text())
    if manifest["source"]["kind"] != "in_memory_controlled_fixture":
        raise RuntimeError("smoke validator accepts only the controlled in-memory fixture")
    object_name = manifest["objects_in_frozen_order"][0]
    object_record = manifest["objects"][0]
    target = np.load(str(args.package / object_name / object_record["target_file"]))
    max_error_max = float(np.max(np.abs(target["lambda_max"] - 1.10)))
    max_error_min = float(np.max(np.abs(target["lambda_min"] - 1.00)))
    max_area_residual = float(np.max(np.abs(target["area_identity_residual"])))
    invalid_fraction = float(1.0 - np.mean(target["valid"]))
    dtype_pass = target["lambda_max"].dtype == np.float64 and target["log_strain"].dtype == np.float64
    version_pass = manifest["blender"]["version_tuple"] == [3, 6, 13]
    passed = (
        max_error_max <= THRESHOLD
        and max_error_min <= THRESHOLD
        and max_area_residual <= THRESHOLD
        and invalid_fraction == 0.0
        and dtype_pass
        and version_pass
    )
    report = {
        "schema": "lumimotion.constitutive.path_a_blender_smoke_validation",
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "package": str(args.package.resolve()),
        "fixture": "in_memory_uniaxial_1.10_plus_rigid",
        "blender_executable": manifest["blender"]["executable"],
        "blender_version": manifest["blender"]["version"],
        "blender_build_hash": manifest["blender"]["build_hash"],
        "max_abs_lambda_max_error": max_error_max,
        "max_abs_lambda_min_error": max_error_min,
        "max_abs_area_identity_residual": max_area_residual,
        "invalid_fraction": invalid_fraction,
        "float64_gate_pass": bool(dtype_pass),
        "blender_3_6_13_gate_pass": bool(version_pass),
        "pass": bool(passed),
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
