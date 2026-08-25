#!/usr/bin/env python3
"""Extract frozen Blender-4.4 packages for the version-fidelity comparison.

This is a thin contract wrapper around ``run_deformation_regime``.  It reuses
that driver's evaluated-mesh extraction, correspondence, Path-A, packaging, and
resume implementation while binding the preregistered 4.4 binary and immutable
3.6 baseline identities.  It never saves or renders the open blend file.
"""

import argparse
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BASELINE_ROOT = REPO_ROOT / "outputs_constitutive" / "deformation_regime_v1"
DEFAULT_OUTPUT = REPO_ROOT / "outputs_constitutive" / "blender_version_fidelity_v2"
OUTPUTS_LINK = REPO_ROOT / "outputs_constitutive"
EXPECTED_OUTPUTS_PHYSICAL = Path("/data/fmb/LumiMotion/outputs_constitutive")
PREREG = REPO_ROOT / "docs" / "constitutive_blender_version_fidelity_prereg.md"
BLENDER = Path("/home/fmb/blender-4.4.0-linux-x64/blender")
EXPECTED_BLENDER_VERSION = "4.4.0"
EXPECTED_BLENDER_BUILD_HASH = "05377985c527"

EXPECTED_BASELINE_HASHES = {
    "run_manifest.json": "a7106e81a9febcc02454436b429d2f2c3d69e5e5b77be1eb41783d4e26de0afd",
    "deformation_regime_summary.json": "d75faca42ec839ea84f08ffff3b32a7e7dc5c42429cbe3377382e24395399793",
    "scenes/hook/scene_manifest.json": "039d906692d4268cf22ca74fc706e8bbb0f53df30839f97f4f380ba9adb21df9",
    "scenes/jumpingjacks/scene_manifest.json": "bf8aecd2c6c43c49f4f2999823e551fd489fcc0e1ccb075e7549417bd74bd1cb",
    "scenes/mouse/scene_manifest.json": "7a797c99f2c57c724f37258e620952fb6df713c9d59c1010ffeabcba1d6c2de0",
    "scenes/standup/scene_manifest.json": "4c28bbcbf77e805dfb5dc510f4799002d958c111474414fdf9aa3c3e40df232f",
}
EXPECTED_SOURCE_HASHES = {
    "hook": "bb3949b4849661fa3df64eb149896978fe124f109b921e94850207788881e084",
    "jumpingjacks": "d9b58009bf55594edd204b7ee2627f342b89c43891b6f453fd50e1227f97cf82",
    "mouse": "db554ac925521769312b659397614c1e0920ac7ce1d8467f97caa652126bee78",
    "standup": "ff7a7d6f78255ee6f4996fa717ea6a54ca19788b80e5254d65be4ffb667985b5",
}


def _load_regime_driver():
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    import run_deformation_regime as regime

    return regime


def verify_baseline(regime):
    """Verify immutable top-level evidence before any 4.4 extraction."""
    baseline = BASELINE_ROOT.resolve()
    if baseline == DEFAULT_OUTPUT.resolve():
        raise RuntimeError("4.4 output and immutable baseline resolve to the same path")
    verified = {}
    for relative, expected_hash in EXPECTED_BASELINE_HASHES.items():
        path = baseline / relative
        if not path.is_file():
            raise RuntimeError("missing immutable baseline evidence: {}".format(path))
        actual_hash = regime.sha256_file(path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                "immutable baseline hash mismatch: {} expected={} actual={}".format(
                    path, expected_hash, actual_hash
                )
            )
        verified[relative] = actual_hash

    run_manifest = json.loads((baseline / "run_manifest.json").read_text(encoding="utf-8"))
    if run_manifest.get("scene_order") != list(regime.SCENES):
        raise RuntimeError("immutable baseline scene order differs from frozen order")
    for scene_id in regime.SCENES:
        manifest_path = baseline / "scenes" / scene_id / "scene_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "complete" or manifest.get("completed_frame_count") != 150:
            raise RuntimeError("immutable baseline scene is not complete: {}".format(scene_id))
        if manifest.get("target_frames") != [1, 150] or manifest.get("subframe") != 0.0:
            raise RuntimeError("immutable baseline frame schedule mismatch: {}".format(scene_id))
        if manifest.get("reference_frame") != regime.SCENES[scene_id]["reference_frame"]:
            raise RuntimeError("immutable baseline reference frame mismatch: {}".format(scene_id))
        if manifest.get("source", {}).get("sha256") != EXPECTED_SOURCE_HASHES[scene_id]:
            raise RuntimeError("immutable baseline source hash mismatch: {}".format(scene_id))
    return verified


def verify_output_root(output_root):
    """Require the new tree to resolve through the existing /data symlink."""
    if not OUTPUTS_LINK.is_symlink():
        raise RuntimeError("expected outputs_constitutive symlink is absent")
    if OUTPUTS_LINK.resolve() != EXPECTED_OUTPUTS_PHYSICAL:
        raise RuntimeError(
            "outputs_constitutive resolves unexpectedly: {}".format(OUTPUTS_LINK.resolve())
        )
    resolved = output_root.resolve()
    try:
        resolved.relative_to(EXPECTED_OUTPUTS_PHYSICAL)
    except ValueError:
        raise RuntimeError("4.4 output must physically resolve under {}".format(EXPECTED_OUTPUTS_PHYSICAL))
    baseline = BASELINE_ROOT.resolve()
    if resolved == baseline or baseline in resolved.parents:
        raise RuntimeError("refusing to write in immutable 3.6 baseline: {}".format(resolved))
    return resolved


def verify_current_source_assets(regime):
    """Refuse to launch Blender unless the local files match baseline identity."""
    verified = {}
    for scene_id, scene in regime.SCENES.items():
        path = scene["asset"]
        if not path.is_file():
            raise RuntimeError("missing frozen source asset: {}".format(path))
        actual = regime.sha256_file(path)
        expected = EXPECTED_SOURCE_HASHES[scene_id]
        if actual != expected:
            raise RuntimeError(
                "source asset hash mismatch for {}: expected={} actual={}".format(
                    scene_id, expected, actual
                )
            )
        verified[scene_id] = actual
    return verified


def configure_regime(regime, baseline_hashes):
    """Bind the reused worker to the frozen fidelity contract."""
    regime.SCRIPT_PATH = SCRIPT_PATH
    regime.BLENDER = BLENDER
    regime.EXPECTED_BLENDER_VERSION = EXPECTED_BLENDER_VERSION
    regime.EXPECTED_BLENDER_BUILD_HASH = EXPECTED_BLENDER_BUILD_HASH
    regime.DEFAULT_OUTPUT = DEFAULT_OUTPUT
    regime.PREREG = PREREG
    base_identity = regime.contract_identity

    def fidelity_identity():
        identity = base_identity()
        identity.update({
            "comparison_schema": "lumimotion.constitutive.blender_version_fidelity_extraction",
            "comparison_schema_version": 1,
            "immutable_baseline_root": str(BASELINE_ROOT.resolve()),
            "immutable_baseline_hashes": dict(baseline_hashes),
            "expected_source_sha256": dict(EXPECTED_SOURCE_HASHES),
        })
        return identity

    regime.contract_identity = fidelity_identity


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run or dry-run the frozen Blender-4.4 fidelity extraction."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify baseline, paths, and Blender version and print commands; open no assets.",
    )
    parser.add_argument("--blender-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker-dispatch-self-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--scene-id", choices=("hook", "jumpingjacks", "mouse", "standup"), help=argparse.SUPPRESS
    )
    return parser.parse_args(argv)


def main(argv=None):
    blender_argv = (
        sys.argv[sys.argv.index("--") + 1 :]
        if "bpy" in sys.modules and "--" in sys.argv
        else argv
    )
    args = parse_args(blender_argv)
    if args.blender_worker and args.worker_dispatch_self_test:
        print(json.dumps({
            "worker_dispatch_self_test": "PASS",
            "blender_host_arguments_ignored": True,
            "worker_arguments": blender_argv,
            "scene_id": args.scene_id,
            "output_root": str(args.output_root),
            "joanna_asset_accessed": False,
            "strain_extracted": False,
        }, indent=2, sort_keys=True))
        return 0
    regime = _load_regime_driver()
    verified = verify_baseline(regime)
    verify_current_source_assets(regime)
    args.output_root = verify_output_root(args.output_root)
    configure_regime(regime, verified)
    if args.blender_worker:
        if args.scene_id is None:
            raise RuntimeError("--scene-id is required in Blender-worker mode")
        return regime.blender_worker(args)
    return regime.host_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
