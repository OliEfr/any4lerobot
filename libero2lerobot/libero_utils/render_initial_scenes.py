"""Render initial-scene previews for LIBERO tasks across all suites and embodiments.

For each embodiment and suite, takes the first N tasks, initializes the env to the first
recorded demo's initial scene, settles, and renders from three cameras: the standard
`agentview` plus our `frontview` + `sideview`. One PNG is saved per (suite, robot, view, task):

    <suite>_robot_<robot>_view_<view>_task_<task_name>.png
    e.g. libero_10_robot_franka_view_sideview_task_LIVING_ROOM_SCENE2_put_both...png

Non-Panda embodiments are initialized exactly like the regeneration pipeline (drive the
target arm's EEF to the Panda demo's settled start, then splice the mujoco state) so the
arm is placed correctly relative to the scene.

Run from libero2lerobot/ (so `import config`/`custom_robots` resolve), e.g.:
    python libero_utils/render_initial_scenes.py \
        --libero_raw_data_root ../libero_datasets \
        --out_dir ./initial_scene_previews \
        --tasks_per_suite 10
"""

import argparse
import os

import h5py
from PIL import Image, ImageDraw

from libero.libero import benchmark, get_libero_path
from libero.libero.envs import OffScreenRenderEnv

import custom_robots  # noqa: F401  (registers non-Panda embodiments with robosuite)
from regenerate_libero_dataset import (
    ROBOT_JOINT_DIMS,
    drive_to_start_and_splice,
    get_libero_dummy_action,
    get_source_panda_env,
)

# The standard agentview + our two additional views, rendered together in one env.
CAMERAS = ["agentview", "frontview", "sideview"]
SUITES = ["libero_object", "libero_spatial", "libero_goal", "libero_10", "libero_90"]
# filename key -> robosuite robot arg (LIBERO prepends Mounted/OnTheGround per scene).
ROBOTS = {"franka": "Panda", "ur5e": "UR5e", "kinova3": "Kinova3", "iiwa": "IIWA", "sawyer": "Sawyer"}
# Per-suite task_id override. Suites not listed default to the first --tasks_per_suite tasks.
# libero_10: 2 = KITCHEN_SCENE3 (stove + moka pot).  libero_90: 84 = STUDY_SCENE3 (caddy + mugs).
SUITE_TASK_IDS = {"libero_10": [2], "libero_90": [84]}


def label(img_array, text):
    """Return a PIL image of the (camera) frame, upright, with a small text label burned in."""
    img = Image.fromarray(img_array[::-1])  # robosuite renders upside-down
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, len(text) * 7 + 6, 16], fill=(0, 0, 0))
    draw.text((3, 3), text, fill=(255, 255, 255))
    return img


def make_env(task, robot, resolution):
    task_bddl_file = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
    env = OffScreenRenderEnv(
        bddl_file_name=task_bddl_file,
        robots=[robot],
        camera_heights=resolution,
        camera_widths=resolution,
        camera_names=CAMERAS,
    )
    env.seed(0)
    return env


def render_task(task, robot, raw_data_path, resolution):
    """Init to the first demo's initial scene and return {camera: rgb_array}."""
    with h5py.File(raw_data_path, "r") as f:
        orig_state0 = f["data"]["demo_0"]["states"][()][0]

    env = make_env(task, robot, resolution)
    source_env = get_source_panda_env(task) if robot != "Panda" else None
    try:
        if robot == "Panda":
            env.reset()
            env.set_init_state(orig_state0)
        else:
            # Settle the Panda source env at the demo start so it holds the initial EEF goal,
            # then drive the target arm there and splice the scene state (regen procedure).
            source_env.reset()
            source_env.set_init_state(orig_state0)
            for _ in range(10):
                source_env.step(get_libero_dummy_action("llava"))
            drive_to_start_and_splice(env, source_env, orig_state0, ROBOT_JOINT_DIMS[robot])

        obs = None
        for _ in range(10):  # settle physics
            obs, _, _, _ = env.step(get_libero_dummy_action("llava"))
        return {cam: obs[f"{cam}_image"] for cam in CAMERAS}
    finally:
        env.close()
        if source_env is not None:
            source_env.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--libero_raw_data_root", default="../libero_datasets",
                        help="Dir containing one subfolder of *_demo.hdf5 per suite.")
    parser.add_argument("--out_dir", default="./initial_scene_previews")
    parser.add_argument("--tasks_per_suite", type=int, default=10)
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument("--robots", nargs="+", default=list(ROBOTS.keys()),
                        help=f"Subset of embodiments to render. Choices: {list(ROBOTS.keys())}")
    args = parser.parse_args()

    benchmark_dict = benchmark.get_benchmark_dict()

    for robot_key in args.robots:
        robot = ROBOTS[robot_key]
        for suite in SUITES:
            task_suite = benchmark_dict[suite]()
            task_ids = SUITE_TASK_IDS.get(suite, list(range(min(args.tasks_per_suite, task_suite.n_tasks))))
            suite_out = os.path.join(args.out_dir, suite)
            os.makedirs(suite_out, exist_ok=True)
            print(f"\n=== {robot_key} / {suite}: tasks {task_ids} ===")

            for task_id in task_ids:
                task = task_suite.get_task(task_id)
                raw_data_path = os.path.join(args.libero_raw_data_root, suite, f"{task.name}_demo.hdf5")
                if not os.path.exists(raw_data_path):
                    print(f"  [skip] {task.name}: no raw demo at {raw_data_path}")
                    continue

                frames = render_task(task, robot, raw_data_path, args.resolution)
                for view in CAMERAS:
                    fname = f"{suite}_{robot_key}_{view}_{task.name}.png"
                    label(frames[view], view).save(os.path.join(suite_out, fname))
                print(f"  [{task_id:02d}] {task.name}")

    print(f"\nDone. Previews in {os.path.abspath(args.out_dir)}")


if __name__ == "__main__":
    main()
