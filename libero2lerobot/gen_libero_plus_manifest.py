"""Emit the LIBERO-Plus combo manifest: one line per (robot, dim, suite).

Each line is a self-contained regeneration unit consumed by run_libero_plus_parallel.sh. The
inner per-instance enumeration (how many trajectories a combo expands to) happens later inside
regenerate_libero_plus_dataset.py; this manifest only lists the combos to schedule.

Order matters: the eval-conformant core (Panda x default cams) is emitted first so a
front-to-back run generates the most directly useful data first.

Usage:
    python gen_libero_plus_manifest.py --robots Panda UR5e Kinova3 IIWA Sawyer \
        --dims camera lighting texture noise --suites libero_object libero_spatial \
        libero_goal libero_10 > manifest.txt
"""

import argparse

ALL_SUITES = ["libero_object", "libero_spatial", "libero_goal", "libero_10"]
ALL_DIMS = ["camera", "lighting", "texture", "noise"]
ALL_ROBOTS = ["Panda", "UR5e", "Kinova3", "IIWA", "Sawyer"]


def main(args):
    rows = []
    for robot in args.robots:
        for dim in args.dims:
            for suite in args.suites:
                rows.append((robot, dim, suite))

    # Eval-conformant core first: Panda generally, default cams handled by the runner's CAMERAS.
    rows.sort(key=lambda r: (r[0] != "Panda", args.robots.index(r[0]), args.dims.index(r[1]), args.suites.index(r[2])))

    for robot, dim, suite in rows:
        print(f"{robot}\t{dim}\t{suite}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--robots", nargs="+", default=ALL_ROBOTS, choices=ALL_ROBOTS)
    parser.add_argument("--dims", nargs="+", default=ALL_DIMS, choices=ALL_DIMS)
    parser.add_argument("--suites", nargs="+", default=ALL_SUITES, choices=ALL_SUITES)
    args = parser.parse_args()
    main(args)
