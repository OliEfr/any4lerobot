#!/usr/bin/env python3
"""Merge four LIBERO dataset suites into a single 'libero' dataset.

Merges libero_10, libero_goal, libero_spatial, and libero_object
(all with additionalCams) into one unified dataset.

Usage:
    conda activate any4lerobot
    cd /home/admin_07/project_repos/any4lerobot/lerobot_datasets
    python merge_libero.py
"""

import logging
import shutil
from pathlib import Path

from lerobot.datasets.dataset_tools import merge_datasets
from lerobot.datasets.lerobot_dataset import LeRobotDataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATASETS_DIR = Path("/home/admin_07/project_repos/any4lerobot/lerobot_datasets")

DATASET_NAMES = [
    "libero_10_additionalCams_lerobot",
    "libero_goal_additionalCams_lerobot",
    "libero_spatial_additionalCams_lerobot",
    "libero_object_additionalCams_lerobot",
]

OUTPUT_REPO_ID = "libero"
OUTPUT_DIR = DATASETS_DIR / "libero"


def main():
    if OUTPUT_DIR.exists():
        logger.warning(f"Output directory {OUTPUT_DIR} already exists, removing it.")
        shutil.rmtree(OUTPUT_DIR)

    datasets = []
    for name in DATASET_NAMES:
        root = DATASETS_DIR / name
        logger.info(f"Loading dataset: {name}")
        ds = LeRobotDataset(repo_id=name, root=root)
        logger.info(f"  {ds.meta.total_episodes} episodes, {ds.meta.total_frames} frames")
        datasets.append(ds)

    logger.info(f"Merging {len(datasets)} datasets into '{OUTPUT_REPO_ID}' at {OUTPUT_DIR}")

    merged = merge_datasets(
        datasets=datasets,
        output_repo_id=OUTPUT_REPO_ID,
        output_dir=OUTPUT_DIR,
    )

    logger.info("Merge complete!")
    logger.info(f"  Total episodes: {merged.meta.total_episodes}")
    logger.info(f"  Total frames:   {merged.meta.total_frames}")
    logger.info(f"  Total tasks:    {merged.meta.total_tasks}")
    logger.info(f"  Output path:    {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
