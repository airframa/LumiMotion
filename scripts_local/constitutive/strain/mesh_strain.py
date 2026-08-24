"""Reference-relative, face-level surface strain (Path A).

This module is intentionally Blender-independent.  It implements the formulation
frozen in docs/constitutive_strain_interface_spec.md and the numerical validity
rules frozen in docs/constitutive_strain_validation_prereg.md.
"""

from dataclasses import dataclass
from enum import IntFlag
from typing import Dict

import numpy as np


SCHEMA_NAME = "lumimotion.constitutive.path_a_face_strain"
SCHEMA_VERSION = 1
LOG_STRAIN_ORDER = (
    "log_stretch_max",
    "log_stretch_min",
    "log_area_change",
    "log_anisotropy",
)


class InvalidReason(IntFlag):
    NONE = 0
    NONFINITE_REFERENCE = 1 << 0
    NONFINITE_TARGET = 1 << 1
    REFERENCE_ZERO_SCALE = 1 << 2
    REFERENCE_DEGENERATE = 1 << 3
    REFERENCE_ILL_CONDITIONED = 1 << 4
    TARGET_COLLAPSED = 1 << 5
    EIGENDECOMPOSITION_FAILURE = 1 << 6
    MATERIALLY_NEGATIVE_EIGENVALUE = 1 << 7
    NONPOSITIVE_PRINCIPAL_STRETCH = 1 << 8
    ROUNDOFF_EIGENVALUE_PROJECTED = 1 << 9


INVALID_REASON_NAMES: Dict[int, str] = {
    int(reason): reason.name.lower() for reason in InvalidReason if reason != InvalidReason.NONE
}


@dataclass(frozen=True)
class StrainTolerances:
    area_quality_min: float = 1.0e-12
    condition_number_max: float = 1.0e8
    negative_eigenvalue_relative: float = 1.0e-12


def _validated_inputs(reference_positions, target_positions, triangles):
    reference = np.asarray(reference_positions, dtype=np.float64)
    target = np.asarray(target_positions, dtype=np.float64)
    faces = np.asarray(triangles)
    if reference.ndim != 2 or reference.shape[1] != 3:
        raise ValueError("reference_positions must have shape [V,3]")
    if target.shape != reference.shape:
        raise ValueError("target_positions must have the same [V,3] shape as reference_positions")
    if faces.ndim != 2 or faces.shape[1] != 3 or not np.issubdtype(faces.dtype, np.integer):
        raise ValueError("triangles must be an integer array with shape [F,3]")
    faces = faces.astype(np.int64, copy=False)
    if faces.size and (np.min(faces) < 0 or np.max(faces) >= reference.shape[0]):
        raise ValueError("triangles contain an out-of-range vertex index")
    return reference, target, faces


def compute_face_strain(
    reference_positions,
    target_positions,
    triangles,
    tolerances: StrainTolerances = StrainTolerances(),
):
    """Compute Path-A strain while retaining every canonical face row.

    Returned arrays are float64 unless intrinsically integer/Boolean.  Invalid
    rows retain diagnostics and reason bits, while F, C, lambdas, and log strain
    remain NaN.
    """
    reference, target, faces = _validated_inputs(reference_positions, target_positions, triangles)
    face_count = faces.shape[0]
    nan = np.full
    result = {
        "schema_name": SCHEMA_NAME,
        "schema_version": np.int64(SCHEMA_VERSION),
        "triangles": faces.copy(),
        "F_surface": nan((face_count, 3, 2), np.nan, dtype=np.float64),
        "C_surface": nan((face_count, 2, 2), np.nan, dtype=np.float64),
        "lambda_max": nan(face_count, np.nan, dtype=np.float64),
        "lambda_min": nan(face_count, np.nan, dtype=np.float64),
        "log_strain": nan((face_count, 4), np.nan, dtype=np.float64),
        "area_reference": nan(face_count, np.nan, dtype=np.float64),
        "area_deformed": nan(face_count, np.nan, dtype=np.float64),
        "area_ratio": nan(face_count, np.nan, dtype=np.float64),
        "stretch_area": nan(face_count, np.nan, dtype=np.float64),
        "area_identity_residual": nan(face_count, np.nan, dtype=np.float64),
        "reference_edge_scale": nan(face_count, np.nan, dtype=np.float64),
        "q_area_reference": nan(face_count, np.nan, dtype=np.float64),
        "q_area_target": nan(face_count, np.nan, dtype=np.float64),
        "condition_number_reference": nan(face_count, np.nan, dtype=np.float64),
        "reference_tangent_basis": nan((face_count, 3, 2), np.nan, dtype=np.float64),
        "valid": np.zeros(face_count, dtype=np.bool_),
        "invalid_reason": np.zeros(face_count, dtype=np.uint32),
        "roundoff_projection_count": np.int64(0),
    }

    for face_id, (a, b, c) in enumerate(faces):
        X = reference[[a, b, c]]
        x = target[[a, b, c]]
        reason = InvalidReason.NONE
        if not np.all(np.isfinite(X)):
            reason |= InvalidReason.NONFINITE_REFERENCE
        if not np.all(np.isfinite(x)):
            reason |= InvalidReason.NONFINITE_TARGET
        if reason:
            result["invalid_reason"][face_id] = int(reason)
            continue

        e1, e2 = X[1] - X[0], X[2] - X[0]
        d1, d2 = x[1] - x[0], x[2] - x[0]
        L = max(float(np.linalg.norm(e1)), float(np.linalg.norm(e2)))
        result["reference_edge_scale"][face_id] = L
        if L == 0.0:
            result["invalid_reason"][face_id] = int(InvalidReason.REFERENCE_ZERO_SCALE)
            continue

        cross_ref = np.cross(e1, e2)
        cross_target = np.cross(d1, d2)
        cross_ref_norm = float(np.linalg.norm(cross_ref))
        cross_target_norm = float(np.linalg.norm(cross_target))
        q_ref = cross_ref_norm / (L * L)
        q_target = cross_target_norm / (L * L)
        result["q_area_reference"][face_id] = q_ref
        result["q_area_target"][face_id] = q_target
        result["area_reference"][face_id] = 0.5 * cross_ref_norm
        result["area_deformed"][face_id] = 0.5 * cross_target_norm
        if q_ref <= tolerances.area_quality_min:
            reason |= InvalidReason.REFERENCE_DEGENERATE
        if q_target <= tolerances.area_quality_min:
            reason |= InvalidReason.TARGET_COLLAPSED
        if reason:
            result["invalid_reason"][face_id] = int(reason)
            continue

        first_edge = e1 if np.linalg.norm(e1) > 0.0 else e2
        t1 = first_edge / np.linalg.norm(first_edge)
        normal = cross_ref / cross_ref_norm
        t2 = np.cross(normal, t1)
        tangent = np.column_stack((t1, t2))
        Dm = np.column_stack((e1, e2))
        Ds = np.column_stack((d1, d2))
        B_ref = tangent.T @ Dm
        condition = float(np.linalg.cond(B_ref))
        result["condition_number_reference"][face_id] = condition
        result["reference_tangent_basis"][face_id] = tangent
        if not np.isfinite(condition) or condition > tolerances.condition_number_max:
            result["invalid_reason"][face_id] = int(InvalidReason.REFERENCE_ILL_CONDITIONED)
            continue

        try:
            # F B_ref = Ds; solve the transposed system without explicitly inverting B_ref.
            F_surface = np.linalg.solve(B_ref.T, Ds.T).T
            C_surface = F_surface.T @ F_surface
            C_surface = 0.5 * (C_surface + C_surface.T)
            eigenvalues = np.linalg.eigvalsh(C_surface)[::-1]
        except np.linalg.LinAlgError:
            result["invalid_reason"][face_id] = int(InvalidReason.EIGENDECOMPOSITION_FAILURE)
            continue
        if not (np.all(np.isfinite(F_surface)) and np.all(np.isfinite(eigenvalues))):
            result["invalid_reason"][face_id] = int(InvalidReason.EIGENDECOMPOSITION_FAILURE)
            continue

        mu_max = float(eigenvalues[0])
        negative_tolerance = tolerances.negative_eigenvalue_relative * max(1.0, mu_max)
        materially_negative = eigenvalues < -negative_tolerance
        if np.any(materially_negative):
            result["invalid_reason"][face_id] = int(InvalidReason.MATERIALLY_NEGATIVE_EIGENVALUE)
            continue
        projected = (eigenvalues < 0.0) & ~materially_negative
        if np.any(projected):
            eigenvalues[projected] = 0.0
            reason |= InvalidReason.ROUNDOFF_EIGENVALUE_PROJECTED
            result["roundoff_projection_count"] += 1
        stretches = np.sqrt(eigenvalues)
        if np.any(stretches <= 0.0):
            reason |= InvalidReason.NONPOSITIVE_PRINCIPAL_STRETCH
            result["invalid_reason"][face_id] = int(reason)
            continue

        lambda_max, lambda_min = map(float, stretches)
        logs = np.log(stretches)
        log_strain = np.array(
            [logs[0], logs[1], logs[0] + logs[1], logs[0] - logs[1]], dtype=np.float64
        )
        area_ratio = result["area_deformed"][face_id] / result["area_reference"][face_id]
        stretch_area = lambda_max * lambda_min
        result["F_surface"][face_id] = F_surface
        result["C_surface"][face_id] = C_surface
        result["lambda_max"][face_id] = lambda_max
        result["lambda_min"][face_id] = lambda_min
        result["log_strain"][face_id] = log_strain
        result["area_ratio"][face_id] = area_ratio
        result["stretch_area"][face_id] = stretch_area
        result["area_identity_residual"][face_id] = area_ratio - stretch_area
        result["valid"][face_id] = True
        result["invalid_reason"][face_id] = int(reason)

    return result


def invalid_reason_labels(value: int):
    """Return stable symbolic labels for a uint32 invalid-reason bitmask."""
    return [name for bit, name in INVALID_REASON_NAMES.items() if int(value) & bit]

