"""Read-only evaluated-mesh extraction wrapper for Path-A strain.

Run with Blender, for example:
  blender --background scene.blend --python blender_extract_path_a.py -- \
    --objects Cloth --reference-frame 1 --target-frame 2 --output-dir /tmp/path_a

The wrapper never saves the open blend.  It freezes reference triangulation,
requires identical evaluated polygon/vertex correspondence at the target, and
uses evaluated object-to-world transforms.  ``--self-test`` constructs an
in-memory controlled scene and does not open or save an asset.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mesh_strain import (  # noqa: E402
    INVALID_REASON_NAMES,
    LOG_STRAIN_ORDER,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    StrainTolerances,
    compute_face_strain,
)


def sha256_file(path, block_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def hash_array(array, dtype):
    canonical = np.ascontiguousarray(array, dtype=dtype)
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def set_configuration(frame, subframe):
    bpy.context.scene.frame_set(int(frame), subframe=float(subframe))
    bpy.context.view_layer.update()


def extract_evaluated_object(object_name):
    source = bpy.data.objects.get(object_name)
    if source is None:
        raise RuntimeError("explicit object not found: {}".format(object_name))
    if source.type != "MESH":
        raise RuntimeError("object is not a mesh: {} ({})".format(object_name, source.type))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = source.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    if mesh is None:
        raise RuntimeError("evaluated mesh unavailable: {}".format(object_name))
    try:
        matrix_world = np.asarray(evaluated.matrix_world, dtype=np.float64)
        local = np.array([vertex.co[:] for vertex in mesh.vertices], dtype=np.float64)
        homogeneous = np.column_stack((local, np.ones(local.shape[0], dtype=np.float64)))
        world = (homogeneous @ matrix_world.T)[:, :3]
        polygons = [tuple(int(index) for index in polygon.vertices) for polygon in mesh.polygons]
        loops = [int(loop.vertex_index) for loop in mesh.loops]
        # Topology-only deterministic fan triangulation.  Unlike evaluated
        # tessellation, this cannot choose a different diagonal as geometry moves.
        triangles = np.array(
            [
                (polygon[0], polygon[corner], polygon[corner + 1])
                for polygon in polygons
                for corner in range(1, len(polygon) - 1)
            ],
            dtype=np.int64,
        ).reshape((-1, 3))
        shape_keys = source.data.shape_keys
        return {
            "positions": world,
            "triangles": triangles,
            "polygons": polygons,
            "loops": loops,
            "matrix_world": matrix_world,
            "vertex_count": len(mesh.vertices),
            "polygon_count": len(mesh.polygons),
            "loop_count": len(mesh.loops),
            "triangle_count": len(triangles),
            "evaluation_provenance": {
                "source_object_name": source.name_full,
                "source_mesh_name": source.data.name_full,
                "evaluated_object_name": evaluated.name_full,
                "modifiers": [
                    {
                        "name": modifier.name,
                        "type": modifier.type,
                        "show_viewport": bool(modifier.show_viewport),
                        "show_render": bool(modifier.show_render),
                    }
                    for modifier in source.modifiers
                ],
                "object_action": (
                    source.animation_data.action.name
                    if source.animation_data and source.animation_data.action
                    else None
                ),
                "shape_key_action": (
                    shape_keys.animation_data.action.name
                    if shape_keys and shape_keys.animation_data and shape_keys.animation_data.action
                    else None
                ),
                "shape_key_values": (
                    {block.name: float(block.value) for block in shape_keys.key_blocks}
                    if shape_keys
                    else {}
                ),
            },
        }
    finally:
        evaluated.to_mesh_clear()


def encode_ragged(rows):
    flat = np.array([value for row in rows for value in row], dtype=np.int64)
    offsets = np.zeros(len(rows) + 1, dtype=np.int64)
    offsets[1:] = np.cumsum([len(row) for row in rows], dtype=np.int64)
    return flat, offsets


def topology_signature(extracted):
    polygon_flat, polygon_offsets = encode_ragged(extracted["polygons"])
    digest = hashlib.sha256()
    for array, dtype in (
        (np.array([extracted["vertex_count"]], dtype=np.int64), "<i8"),
        (polygon_flat, "<i8"),
        (polygon_offsets, "<i8"),
        (np.asarray(extracted["loops"]), "<i8"),
        (extracted["triangles"], "<i8"),
    ):
        digest.update(np.ascontiguousarray(array, dtype=dtype).tobytes())
    return digest.hexdigest(), polygon_flat, polygon_offsets


def require_correspondence(reference, target, object_name):
    scalar_fields = ("vertex_count", "polygon_count", "loop_count", "triangle_count")
    for field in scalar_fields:
        if reference[field] != target[field]:
            raise RuntimeError(
                "topology changed for {}: {} reference={} target={}".format(
                    object_name, field, reference[field], target[field]
                )
            )
    if reference["polygons"] != target["polygons"]:
        raise RuntimeError("polygon correspondence/order changed for {}".format(object_name))
    if reference["loops"] != target["loops"]:
        raise RuntimeError("loop correspondence/order changed for {}".format(object_name))
    # Deterministic topology-only triangulation must match, but the frozen
    # reference triangle array remains the sole topology passed to strain.
    if not np.array_equal(reference["triangles"], target["triangles"]):
        raise RuntimeError("evaluated triangle correspondence/order changed for {}".format(object_name))


def save_object_package(output_dir, object_name, reference, target, strain, target_filename):
    object_dir = output_dir / object_name
    object_dir.mkdir(parents=True, exist_ok=False)
    topology_hash, polygon_flat, polygon_offsets = topology_signature(reference)
    np.savez_compressed(
        str(object_dir / "reference.npz"),
        reference_positions=reference["positions"],
        triangles=reference["triangles"],
        polygon_vertices=polygon_flat,
        polygon_offsets=polygon_offsets,
        reference_matrix_world=reference["matrix_world"],
        reference_tangent_basis=strain["reference_tangent_basis"],
        area_reference=strain["area_reference"],
        q_area_reference=strain["q_area_reference"],
        condition_number_reference=strain["condition_number_reference"],
    )
    np.savez_compressed(
        str(object_dir / target_filename),
        target_positions=target["positions"],
        target_matrix_world=target["matrix_world"],
        F_surface=strain["F_surface"],
        C_surface=strain["C_surface"],
        lambda_max=strain["lambda_max"],
        lambda_min=strain["lambda_min"],
        log_strain=strain["log_strain"],
        area_deformed=strain["area_deformed"],
        area_ratio=strain["area_ratio"],
        stretch_area=strain["stretch_area"],
        area_identity_residual=strain["area_identity_residual"],
        q_area_target=strain["q_area_target"],
        valid=strain["valid"],
        invalid_reason=strain["invalid_reason"],
    )
    return {
        "object_name": object_name,
        "storage_directory": object_name,
        "target_file": target_filename,
        "vertex_count": reference["vertex_count"],
        "triangle_count": reference["triangle_count"],
        "topology_sha256": topology_hash,
        "reference_positions_sha256_float64_le": hash_array(reference["positions"], "<f8"),
        "target_positions_sha256_float64_le": hash_array(target["positions"], "<f8"),
        "triangles_sha256_int64_le": hash_array(reference["triangles"], "<i8"),
        "valid_faces": int(np.count_nonzero(strain["valid"])),
        "invalid_faces": int(np.count_nonzero(~strain["valid"])),
        "roundoff_projection_count": int(strain["roundoff_projection_count"]),
        "reference_evaluation": reference["evaluation_provenance"],
        "target_evaluation": target["evaluation_provenance"],
    }


def make_self_test_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("PathAControlledPatchMesh")
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        [],
        [(0, 1, 2), (0, 2, 3)],
    )
    mesh.update()
    obj = bpy.data.objects.new("PathAControlledPatch", mesh)
    bpy.context.collection.objects.link(obj)
    basis = obj.shape_key_add(name="Basis")
    stretched = obj.shape_key_add(name="Stretch110")
    for vertex in stretched.data:
        vertex.co.x *= 1.10
    stretched.value = 0.0
    stretched.keyframe_insert(data_path="value", frame=1)
    stretched.value = 1.0
    stretched.keyframe_insert(data_path="value", frame=2)
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.location = (0.0, 0.0, 0.0)
    obj.keyframe_insert(data_path="rotation_euler", frame=1)
    obj.keyframe_insert(data_path="location", frame=1)
    obj.rotation_euler = tuple(np.deg2rad([19.0, -23.0, 37.0]))
    obj.location = (0.37, -1.20, 2.50)
    obj.keyframe_insert(data_path="rotation_euler", frame=2)
    obj.keyframe_insert(data_path="location", frame=2)
    # Freeze interpolation at the explicit endpoint values.
    if obj.animation_data and obj.animation_data.action:
        for curve in obj.animation_data.action.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "CONSTANT"
    if basis is None:  # keeps static analyzers from treating the creation as unused
        raise AssertionError("shape-key basis creation failed")
    return obj.name


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects", nargs="+")
    parser.add_argument("--reference-frame", type=int, required=False)
    parser.add_argument("--reference-subframe", type=float, default=0.0)
    parser.add_argument("--target-frame", type=int, required=False)
    parser.add_argument("--target-subframe", type=float, default=0.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError("output directory already exists; refusing to overwrite: {}".format(args.output_dir))
    if args.self_test:
        object_names = [make_self_test_scene()]
        reference_frame, target_frame = 1, 2
        reference_subframe = target_subframe = 0.0
        source_info = {"kind": "in_memory_controlled_fixture", "path": None, "size": None, "sha256": None}
    else:
        if not args.objects or args.reference_frame is None or args.target_frame is None:
            raise RuntimeError("explicit --objects, --reference-frame, and --target-frame are required")
        object_names = args.objects
        reference_frame, target_frame = args.reference_frame, args.target_frame
        reference_subframe, target_subframe = args.reference_subframe, args.target_subframe
        source_path = Path(bpy.data.filepath)
        if not source_path.is_file():
            raise RuntimeError("open Blender source has no readable file path")
        source_info = {
            "kind": "blend_file",
            "path": str(source_path.resolve()),
            "size": source_path.stat().st_size,
            "sha256": sha256_file(str(source_path)),
        }

    set_configuration(reference_frame, reference_subframe)
    references = {name: extract_evaluated_object(name) for name in object_names}
    set_configuration(target_frame, target_subframe)
    targets = {name: extract_evaluated_object(name) for name in object_names}

    computed = []
    for name in object_names:
        require_correspondence(references[name], targets[name], name)
        strain = compute_face_strain(
            references[name]["positions"], targets[name]["positions"], references[name]["triangles"]
        )
        computed.append((name, strain))

    target_filename = "frame_{:06d}_subframe_{:.6f}.npz".format(target_frame, target_subframe)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    objects_manifest = [
        save_object_package(
            args.output_dir, name, references[name], targets[name], strain, target_filename
        )
        for name, strain in computed
    ]

    repo_root = SCRIPT_DIR.parents[2]
    try:
        git_revision = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        git_revision = None
    validation_path = SCRIPT_DIR / "validation_results.json"
    validation_summary = None
    if validation_path.is_file():
        validation_data = json.loads(validation_path.read_text(encoding="utf-8"))
        validation_summary = {
            "schema_version": validation_data.get("schema_version"),
            "core_verdict": validation_data.get("core_verdict"),
            "results_sha256": sha256_file(str(validation_path)),
        }

    manifest = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "authoritative_level": "face",
        "extractor": {
            "git_revision": git_revision,
            "wrapper_sha256": sha256_file(str(Path(__file__).resolve())),
            "core_sha256": sha256_file(str(SCRIPT_DIR / "mesh_strain.py")),
        },
        "source": source_info,
        "blender": {
            "executable": str(Path(bpy.app.binary_path).resolve()),
            "version": bpy.app.version_string,
            "version_tuple": list(bpy.app.version),
            "build_hash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
            "platform": platform.platform(),
            "dependency_graph": "evaluated_get + to_mesh",
        },
        "command_line": sys.argv,
        "objects_in_frozen_order": object_names,
        "scene": bpy.context.scene.name,
        "view_layer": bpy.context.view_layer.name,
        "reference_configuration": {"frame": reference_frame, "subframe": reference_subframe},
        "target_configuration": {"frame": target_frame, "subframe": target_subframe},
        "coordinate_convention": {
            "space": "evaluated object-to-world",
            "matrix_application": "column-vector matrix; archived arrays use row vectors times transpose",
            "scene_units": {
                "system": bpy.context.scene.unit_settings.system,
                "scale_length": bpy.context.scene.unit_settings.scale_length,
            },
            "handedness": "Blender right-handed world coordinates",
            "per_frame_alignment": False,
        },
        "triangulation_policy": "deterministic polygon-index fan triangulation frozen at reference; target topology must reproduce it; strain uses reference rows",
        "numeric": {
            "dtype": "float64",
            "numpy_version": np.__version__,
            "tolerances": StrainTolerances().__dict__,
            "log_strain_order": list(LOG_STRAIN_ORDER),
            "invalid_reason_bits": {str(bit): name for bit, name in INVALID_REASON_NAMES.items()},
        },
        "objects": objects_manifest,
        "validation_suite": validation_summary,
        "source_blend_saved_or_modified": False,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
