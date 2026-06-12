"""Export MP4 videos from regenerated LIBERO HDF5 files for visual inspection.

Writes one video per demo with frontview and sideview side by side.

Usage:
    python libero_utils/export_h5_videos.py \
        --src ../libero_datasets_regenerated/libero_object_ur5e_smoketest \
        --out ../libero_datasets_regenerated/libero_object_ur5e_smoketest_videos
"""

import argparse
from pathlib import Path

import h5py
import imageio.v2 as imageio
import numpy as np


def export_file(h5_path: Path, out_dir: Path, fps: int, max_demos: int | None):
    with h5py.File(h5_path, "r") as f:
        demos = sorted(f["data"].keys(), key=lambda k: int(k.split("_")[-1]))
        if max_demos is not None:
            demos = demos[:max_demos]
        for demo in demos:
            obs = f["data"][demo]["obs"]
            frames = np.concatenate([obs["frontview_rgb"][()], obs["sideview_rgb"][()]], axis=2)
            out_path = out_dir / f"{h5_path.stem.removesuffix('_demo')}_{demo}.mp4"
            imageio.mimwrite(out_path, frames, fps=fps, macro_block_size=1)
            print(f"wrote {out_path} ({len(frames)} frames)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, required=True, help="regenerated HDF5 file or directory of *_demo.hdf5")
    parser.add_argument("--out", type=Path, required=True, help="output directory for MP4s")
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--max-demos-per-task", type=int, default=None)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    files = sorted(args.src.glob("*.hdf5")) if args.src.is_dir() else [args.src]
    for h5_path in files:
        export_file(h5_path, args.out, args.fps, args.max_demos_per_task)
