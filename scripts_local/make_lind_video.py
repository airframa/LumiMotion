#
# Probe B (Test 1): assemble the per-frame PNGs written by
# scripts_local/dump_lind.py into two videos:
#   lind.mp4             -- L_ind alone
#   beauty_lind_sxs.mp4  -- beauty | L_ind side by side
#
# Run from the repo root:
#   python -m scripts_local.make_lind_video --frames_dir <output_dir>/frames
#
import argparse
import glob
import os

import cv2
import imageio
import numpy as np


def load_sorted(pattern):
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No frames matched {pattern}")
    return paths


def read_rgb(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def make_videos(frames_dir, output_dir, fps):
    os.makedirs(output_dir, exist_ok=True)

    lind_paths = load_sorted(os.path.join(frames_dir, "lind_*.png"))
    beauty_paths = load_sorted(os.path.join(frames_dir, "beauty_*.png"))
    assert len(lind_paths) == len(beauty_paths), (
        f"{len(lind_paths)} L_ind frames vs {len(beauty_paths)} beauty frames -- "
        "did dump_lind.py finish the full run?")

    lind_path = os.path.join(output_dir, "lind.mp4")
    sxs_path = os.path.join(output_dir, "beauty_lind_sxs.mp4")
    lind_writer = imageio.get_writer(lind_path, fps=fps)
    sxs_writer = imageio.get_writer(sxs_path, fps=fps)

    for lp, bp in zip(lind_paths, beauty_paths):
        lind_img = read_rgb(lp)
        beauty_img = read_rgb(bp)
        lind_writer.append_data(lind_img)
        sxs_writer.append_data(np.concatenate([beauty_img, lind_img], axis=1))

    lind_writer.close()
    sxs_writer.close()
    print(f"Wrote {lind_path}")
    print(f"Wrote {sxs_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble L_ind frame dumps into videos (Probe B, Test 1)")
    parser.add_argument("--frames_dir", type=str, required=True,
                        help="Directory with lind_*.png / beauty_*.png from dump_lind.py")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Defaults to the parent directory of --frames_dir")
    parser.add_argument("--fps", type=int, default=15)
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.dirname(os.path.normpath(args.frames_dir))
    make_videos(args.frames_dir, output_dir, args.fps)
