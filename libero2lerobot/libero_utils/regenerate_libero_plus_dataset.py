"""Regenerate a LIBERO-Plus perturbed dataset (HDF5) across embodiments.

Standalone counterpart to `regenerate_libero_dataset.py` (kept untouched except for the
dynamic-camera change). The standard script iterates a task suite; this one iterates
*perturbation work items* (a perturbed scene paired with one original Panda demo) for a single
render dimension, replays the original demo's actions in a freshly-built env with the chosen
robot + cameras, success-filters, and writes one `<base>_demo.hdf5` per base task (each work
item becomes one demo group, with provenance in HDF5 attrs).

Reuses the standard script's pure replay/init helpers (imported, not duplicated) and the fork's
own perturbation code:
  - lighting / texture : instantiate the perturbed bddl file (needs the fork + assets.zip).
  - camera             : default cams -> synthesize the `_view_…_initstate_0` task name so the
                         fork moves `agentview` natively; additional cams -> apply the SAME
                         geometric transform (fork helpers) to frontview + sideview.
  - noise              : apply the fork's blur kernels (via sensor_noise) to the recorded
                         non-wrist views (no native `_noise_` so there is no double blur).

Must run inside the `libero_plus` conda env (fork replaces vanilla libero; robosuite==1.4.0).

Usage:
    python libero_utils/regenerate_libero_plus_dataset.py \
        --perturbation_dim lighting \
        --libero_task_suite libero_object \
        --robot IIWA \
        --cameras additional \
        --libero_raw_data_root <PATH TO libero_datasets> \
        --libero_target_dir <PATH TO OUTPUT DIR>
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import h5py
import numpy as np
import robosuite.utils.transform_utils as T
import tqdm
from libero.libero import get_libero_path
from libero.libero.envs import OffScreenRenderEnv
from libero.libero.envs.env_wrapper import ControlEnv

# Fork camera-geometry helpers (identical copies live in every problems/*.py; import one).
from libero.libero.envs.problems.libero_kitchen_tabletop_manipulation import (
    rotate_around_y,
    rotate_around_z,
    scale_distance_from_pivot,
)

from config import CAMERA_SETS
from libero_plus_tasks import enumerate_work_items
from regenerate_libero_dataset import (
    ROBOT_JOINT_DIMS,
    drive_to_start_and_splice,
    get_eef_goal_action,
    get_libero_dummy_action,
    is_noop,
    set_controller_absolute,
)
from sensor_noise import apply_noise, kernel_name

import custom_robots  # noqa: F401  (registers Mounted{robot} embodiments with robosuite)

ALL_SUITES = ["libero_object", "libero_spatial", "libero_goal", "libero_10"]
WRIST_CAM = "robot0_eye_in_hand"


def build_env(bddl_file_name, robot, resolution, cameras):
    """Build the target render env for an explicit bddl path (possibly a synthesized name)."""
    camera_names = [cam.render_cam for cam in CAMERA_SETS[cameras]]
    env = OffScreenRenderEnv(
        bddl_file_name=bddl_file_name,
        robots=[robot],
        camera_heights=resolution,
        camera_widths=resolution,
        camera_names=camera_names,
    )
    env.seed(0)
    return env


def build_source_env(base_bddl):
    """State-only Panda env (no rendering) on the UNPERTURBED base scene, for init + absolute replay."""
    env = ControlEnv(
        bddl_file_name=base_bddl,
        use_camera_obs=False,
        has_renderer=False,
        has_offscreen_renderer=False,
    )
    env.seed(0)
    return env


def synth_view_name(base_bddl, params):
    """Synthesize the fork's perturbed task name so ControlEnv moves agentview natively."""
    h, v, scale, endrot, endvert = params
    scale100 = int(round(scale * 100))
    stem = base_bddl[:-5] if base_bddl.endswith(".bddl") else base_bddl
    return f"{stem}_view_{int(h)}_{int(v)}_{scale100}_{int(endrot)}_{int(endvert)}_initstate_0.bddl"


def apply_view_to_cam(env, cam_name, params):
    """Re-apply the fork's camera transform (same helper order as `_setup_camera`) to a camera."""
    h, v, scale, endrot, endvert = params
    cam_id = env.sim.model.camera_name2id(cam_name)
    pos = list(env.sim.model.cam_pos[cam_id].copy())
    quat = list(env.sim.model.cam_quat[cam_id].copy())  # mujoco quat is [w, x, y, z]

    if int(v) != 0:
        r = rotate_around_y(original_quat=quat, original_pos=pos, degrees=int(v))
        pos, quat = r["new_pos"], r["new_quat"]
        r = rotate_around_z(original_quat=quat, original_pos=pos, degrees=int(h))
        pos, quat = r["new_pos"], r["new_quat"]
    else:
        r = rotate_around_z(original_quat=quat, original_pos=pos, degrees=int(h))
        pos, quat = r["new_pos"], r["new_quat"]

    if float(scale) != 1.0:
        r = scale_distance_from_pivot(original_quat=quat, original_pos=pos, scale_factor=float(scale))
        pos, quat = r["new_pos"], r["new_quat"]

    if int(endrot) != 0:
        quat = rotate_around_z(original_quat=quat, degrees=int(endrot))["new_quat"]
    if int(endvert) != 0:
        quat = rotate_around_y(original_quat=quat, degrees=int(endvert))["new_quat"]

    env.sim.model.cam_pos[cam_id] = np.array(pos)
    env.sim.model.cam_quat[cam_id] = np.array(quat)
    env.sim.forward()


def record_image(obs, cam, dim, params):
    """Pull one camera's image from obs, apply noise if needed, then the 180° flip."""
    img = obs[cam.obs_image_key]
    if dim == "noise" and cam.render_cam != WRIST_CAM:
        if img.dtype != np.uint8:
            img = (img * 255).astype(np.uint8)
        img = apply_noise(img, params)
    return np.ascontiguousarray(img[::-1, ::-1])


def replay_work_item(item, robot, replay_mode, resolution, cameras, cam_specs, source_demo):
    """Replay one perturbed demo. Returns (success: bool, demo_dict) or (None, None) on skip."""
    orig_actions = source_demo["actions"][()]
    orig_states = source_demo["states"][()]

    # Choose the env bddl: perturbed file (light/texture), synthesized name (camera+default),
    # or the base scene (camera+additional, noise).
    if item.dim in ("lighting", "texture"):
        env_bddl = item.bddl_path
    elif item.dim == "camera" and cameras == "default":
        env_bddl = synth_view_name(item.bddl_path, item.params)
    else:
        env_bddl = item.bddl_path

    env = build_env(env_bddl, robot, resolution, cameras)
    source_env = build_source_env(item.bddl_path) if (robot != "Panda" or replay_mode == "absolute") else None

    try:
        # Settle source Panda env at the demo's initial state (holds the initial EEF goal).
        if source_env is not None:
            source_env.reset()
            source_env.set_init_state(orig_states[0])
            for _ in range(10):
                source_env.step(get_libero_dummy_action("llava"))
        if robot == "Panda":
            env.reset()
            env.set_init_state(orig_states[0])
            init_state = orig_states[0]
        else:
            _, init_state = drive_to_start_and_splice(env, source_env, orig_states[0], ROBOT_JOINT_DIMS[robot])
        for _ in range(10):
            obs, reward, done, info = env.step(get_libero_dummy_action("llava"))
        if replay_mode == "absolute":
            set_controller_absolute(env, True)

        # Camera dim, additional cams: move frontview+sideview, then refresh the current obs.
        if item.dim == "camera" and cameras == "additional":
            for cam in cam_specs:
                apply_view_to_cam(env, cam.render_cam, item.params)
            obs = env.env._get_observations()

        states, actions, ee_states, gripper_states, joint_states, robot_states = [], [], [], [], [], []
        images = {cam.hdf5_rgb_key: [] for cam in cam_specs}

        for _, action in enumerate(orig_actions):
            prev_action = actions[-1] if len(actions) > 0 else None
            if is_noop(action, prev_action):
                continue

            if states == []:
                states.append(init_state)
                if robot == "Panda":
                    robot_states.append(source_demo["robot_states"][0])
                else:
                    robot_states.append(
                        np.concatenate([obs["robot0_gripper_qpos"], obs["robot0_eef_pos"], obs["robot0_eef_quat"]])
                    )
            else:
                states.append(env.sim.get_state().flatten())
                robot_states.append(
                    np.concatenate([obs["robot0_gripper_qpos"], obs["robot0_eef_pos"], obs["robot0_eef_quat"]])
                )

            if replay_mode == "absolute":
                source_env.step(action.tolist())
                exec_action = get_eef_goal_action(source_env, gripper_action=action[-1])
            else:
                exec_action = action
            actions.append(exec_action)

            if "robot0_gripper_qpos" in obs:
                gripper_states.append(obs["robot0_gripper_qpos"])
            joint_states.append(obs["robot0_joint_pos"])
            ee_states.append(np.hstack((obs["robot0_eef_pos"], T.quat2axisangle(obs["robot0_eef_quat"]))))
            for cam in cam_specs:
                images[cam.hdf5_rgb_key].append(record_image(obs, cam, item.dim, item.params))

            obs, reward, done, info = env.step(exec_action.tolist())

        if len(actions) == 0:
            return None, None

        dones = np.zeros(len(actions)).astype(np.uint8)
        dones[-1] = 1
        rewards = np.zeros(len(actions)).astype(np.uint8)
        if done:
            rewards[-1] = 1

        demo = {
            "gripper_states": np.stack(gripper_states, axis=0),
            "joint_states": np.stack(joint_states, axis=0),
            "ee_states": np.stack(ee_states, axis=0),
            "actions": np.array(actions),
            "states": np.stack(states),
            "robot_states": np.stack(robot_states, axis=0),
            "rewards": rewards,
            "dones": dones,
            "images": {k: np.stack(v, axis=0) for k, v in images.items()},
        }
        return bool(done), demo
    finally:
        env.close()
        if source_env is not None:
            source_env.close()


def write_demo(grp, demo_idx, demo, item):
    """Write one replayed demo into an HDF5 'data' group, with provenance attrs."""
    ep = grp.create_group(f"demo_{demo_idx}")
    obs_grp = ep.create_group("obs")
    obs_grp.create_dataset("gripper_states", data=demo["gripper_states"])
    obs_grp.create_dataset("joint_states", data=demo["joint_states"])
    obs_grp.create_dataset("ee_states", data=demo["ee_states"])
    obs_grp.create_dataset("ee_pos", data=demo["ee_states"][:, :3])
    obs_grp.create_dataset("ee_ori", data=demo["ee_states"][:, 3:])
    for rgb_key, arr in demo["images"].items():
        obs_grp.create_dataset(rgb_key, data=arr)
    ep.create_dataset("actions", data=demo["actions"])
    ep.create_dataset("states", data=demo["states"])
    ep.create_dataset("robot_states", data=demo["robot_states"])
    ep.create_dataset("rewards", data=demo["rewards"])
    ep.create_dataset("dones", data=demo["dones"])

    ep.attrs["perturbation_dim"] = item.dim
    ep.attrs["source_task"] = item.base_task
    ep.attrs["source_suite"] = item.base_suite
    ep.attrs["source_demo_index"] = item.demo_index
    ep.attrs["instance_bddl"] = os.path.basename(item.bddl_path)
    if item.dim == "camera":
        ep.attrs["params"] = json.dumps({"view": list(item.params)})
    elif item.dim == "noise":
        ep.attrs["params"] = json.dumps({"severity": item.params, "kernel": kernel_name(item.params)})
    else:
        ep.attrs["params"] = "{}"


def main(args):
    print(
        f"Regenerating LIBERO-Plus [{args.perturbation_dim}] {args.libero_task_suite} "
        f"with robot {args.robot}, cameras={args.cameras} ({args.replay_mode} replay)"
    )

    os.makedirs(args.libero_target_dir, exist_ok=True)
    failures_dir = args.libero_target_dir.rstrip("/") + "_failures"
    os.makedirs(failures_dir, exist_ok=True)

    bddl_root = get_libero_path("bddl_files")
    cam_specs = CAMERA_SETS[args.cameras]

    items = enumerate_work_items(
        dim=args.perturbation_dim,
        suite=args.libero_task_suite,
        bddl_root=bddl_root,
        libero_raw_data_root=args.libero_raw_data_root,
        suites=ALL_SUITES,
        include_mix=args.include_mix,
        cap_per_dim=args.cap_per_dim,
        max_demos=args.max_demos_per_task,
        seed=args.seed,
    )
    print(f"Enumerated {len(items)} work items for {args.perturbation_dim}/{args.libero_task_suite}")

    # Group by base task so each base task -> one <base>_demo.hdf5 (successes) + _failures file.
    by_task = defaultdict(list)
    for item in items:
        by_task[item.base_task].append(item)

    num_replays = num_success = 0
    raw_root = Path(args.libero_raw_data_root)

    for base_task, task_items in by_task.items():
        out_path = os.path.join(args.libero_target_dir, f"{base_task}_demo.hdf5")
        fail_path = os.path.join(failures_dir, f"{base_task}_demo.hdf5")
        if os.path.exists(out_path):
            print(f"Skipping '{base_task}' — output exists: {out_path}")
            continue

        out_file = h5py.File(out_path, "w")
        out_grp = out_file.create_group("data")
        fail_file = h5py.File(fail_path, "w")
        fail_grp = fail_file.create_group("data")
        succ_idx = fail_idx = 0

        for item in tqdm.tqdm(task_items, desc=base_task):
            demo_path = raw_root / item.base_suite / f"{base_task}_demo.hdf5"
            with h5py.File(demo_path, "r") as f:
                source_demo = f["data"][f"demo_{item.demo_index}"]
                try:
                    success, demo = replay_work_item(
                        item, args.robot, args.replay_mode, args.resolution, args.cameras, cam_specs, source_demo
                    )
                except Exception as e:  # one bad scene must not kill the whole combo
                    print(f"  ERROR on {item.base_task}/{os.path.basename(item.bddl_path)} demo_{item.demo_index}: {e}")
                    continue
            if demo is None:
                continue

            if success:
                write_demo(out_grp, succ_idx, demo, item)
                succ_idx += 1
                num_success += 1
            else:
                write_demo(fail_grp, fail_idx, demo, item)
                fail_idx += 1
            num_replays += 1
            if num_replays % 10 == 0:
                print(f"  replayed {num_replays}, successes {num_success} ({num_success / num_replays * 100:.1f}%)")

        for data_file, data_path in [(out_file, out_path), (fail_file, fail_path)]:
            is_empty = len(data_file["data"]) == 0
            data_file.close()
            if is_empty:
                os.remove(data_path)

    print(f"Done. {num_success}/{num_replays} successful. Output: {args.libero_target_dir}")
    print(f"Failures: {failures_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument(
        "--perturbation_dim", type=str, required=True, choices=["camera", "lighting", "texture", "noise"]
    )
    parser.add_argument(
        "--robot", type=str, default="Panda", choices=list(ROBOT_JOINT_DIMS.keys())
    )
    parser.add_argument("--replay_mode", type=str, default="delta", choices=["delta", "absolute"])
    parser.add_argument(
        "--cameras", type=str, default="default", choices=list(CAMERA_SETS.keys()),
        help="default: agentview + wrist; additional: frontview + sideview.",
    )
    parser.add_argument(
        "--libero_task_suite", type=str, required=True, choices=ALL_SUITES,
        help="Base suite to perturb (libero_90 is dropped, matching LIBERO-Plus).",
    )
    parser.add_argument(
        "--libero_raw_data_root", type=str, required=True,
        help="Root holding the original per-suite demos, e.g. .../libero_datasets",
    )
    parser.add_argument("--libero_target_dir", type=str, required=True)
    parser.add_argument(
        "--include-mix", dest="include_mix", action="store_true", default=True,
        help="Match the original ~4,000/dim (light/texture: include libero_mix bddls; camera/noise: 2 samples/demo).",
    )
    parser.add_argument("--no-include-mix", dest="include_mix", action="store_false")
    parser.add_argument("--cap-per-dim", dest="cap_per_dim", type=int, default=None, help="Subsample work items (pilots).")
    parser.add_argument(
        "--max_demos_per_task", type=int, default=None, help="Cap demos/task for camera/noise (quick estimates)."
    )
    parser.add_argument("--seed", type=int, default=0, help="Seed for camera/noise param sampling + cap subsampling.")
    args = parser.parse_args()

    main(args)
