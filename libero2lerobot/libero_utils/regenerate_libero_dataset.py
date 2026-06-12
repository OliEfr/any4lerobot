"""
Adapted from https://github.com/openvla/openvla/blob/main/experiments/robot/libero/regenerate_libero_dataset.py

Regenerates a LIBERO dataset (HDF5 files) by replaying demonstrations in the environments.

Notes:
    - We save image observations at 256x256px resolution (instead of 128x128).
    - We filter out transitions with "no-op" (zero) actions that do not change the robot's state.
    - We filter out unsuccessful demonstrations.
    - In the LIBERO HDF5 data -> RLDS data conversion (not shown here), we rotate the images by
    180 degrees because we observe that the environments return images that are upside down
    on our platform.

Usage:
    python experiments/robot/libero/regenerate_libero_dataset.py \
        --libero_task_suite [ libero_spatial | libero_object | libero_goal | libero_10 ] \
        --libero_raw_data_dir <PATH TO RAW HDF5 DATASET DIR> \
        --libero_target_dir <PATH TO TARGET DIR>

    Example (LIBERO-Spatial):
        python experiments/robot/libero/regenerate_libero_dataset.py \
            --libero_task_suite libero_spatial \
            --libero_raw_data_dir ./LIBERO/libero/datasets/libero_spatial \
            --libero_target_dir ./LIBERO/libero/datasets/libero_spatial_no_noops

"""

import argparse
import json
import os

import h5py
import numpy as np
import robosuite.utils.transform_utils as T
import tqdm
from libero.libero import benchmark, get_libero_path
from libero.libero.envs import OffScreenRenderEnv
from libero.libero.envs.env_wrapper import ControlEnv

import custom_robots  # noqa: F401  (registers non-Panda embodiments with robosuite)

ROBOT_JOINT_DIMS = {"Panda": 7, "UR5e": 6, "Kinova3": 7, "IIWA": 7, "Sawyer": 7}


def get_libero_dummy_action(model_family: str):
    """Get dummy/no-op action, used to roll out the simulation while the robot does nothing."""
    return [0, 0, 0, 0, 0, 0, -1]


def get_libero_env(task, robot, resolution=256):
    """Initializes and returns the LIBERO environment, along with the task description."""
    task_description = task.language
    task_bddl_file = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
    env_args = {"bddl_file_name": task_bddl_file, "robots": [robot], "camera_heights": resolution, "camera_widths": resolution, "camera_names": ["frontview", "sideview"]}
    # env_args = {"bddl_file_name": task_bddl_file, "camera_heights": resolution, "camera_widths": resolution, "camera_names": ["agentview", "robot0_eye_in_hand"]}
    env = OffScreenRenderEnv(**env_args)
    env.seed(0)  # IMPORTANT: seed seems to affect object positions even when using fixed initial state
    return env, task_description


def get_source_panda_env(task):
    """State-only Panda env (no rendering) that replays the original demo alongside the target env.

    Provides the Panda's settled initial EEF goal for initializing other embodiments, and the
    per-step absolute EEF goal actions for --replay_mode absolute.
    """
    task_bddl_file = os.path.join(get_libero_path("bddl_files"), task.problem_folder, task.bddl_file)
    env = ControlEnv(
        bddl_file_name=task_bddl_file,
        use_camera_obs=False,
        has_renderer=False,
        has_offscreen_renderer=False,
    )
    env.seed(0)
    return env


def set_controller_absolute(env, absolute):
    """Toggle the OSC controller between delta and absolute EEF targets.

    robosuite's OSC controller only reads `use_delta` inside `set_goal`, so flipping it at
    runtime is equivalent to loading a controller config with control_delta=False. Must be
    re-applied after env.reset() because hard resets re-create the controller.
    """
    env.env.robots[0].controller.use_delta = not absolute


def get_eef_goal_action(env, gripper_action):
    """Absolute OSC_POSE action (pos, axis-angle, gripper) for env's current controller EEF goal."""
    controller = env.env.robots[0].controller
    goal_ori = T.quat2axisangle(T.mat2quat(controller.goal_ori))
    return np.concatenate([controller.goal_pos, goal_ori, [gripper_action]])


def drive_to_start_and_splice(env, source_env, orig_state0, n_joints):
    """Initialize a non-Panda env to match a Panda demo's initial state (Adapt3R's procedure).

    Drives the robot's EEF to the settled Panda's initial EEF goal with absolute OSC actions,
    then splices a mujoco init state combining the new robot's joint configuration with the
    demo's gripper + object state. Returns (obs, spliced_init_state).
    """
    start_action = get_eef_goal_action(source_env, gripper_action=-1.0)
    env.reset()
    set_controller_absolute(env, True)
    for _ in range(20):
        env.step(start_action.tolist())
    set_controller_absolute(env, False)

    # Flattened mujoco state layout: [time(1), robot qpos(n), gripper+object qpos(n_scene),
    # robot qvel(n), gripper+object qvel(n_scene)]
    new_state = env.sim.get_state().flatten()
    n_scene = (len(new_state) - 1) // 2 - n_joints
    n_joints_orig = (len(orig_state0) - 1) // 2 - n_scene
    init_state = np.concatenate(
        [
            orig_state0[:1],
            new_state[1 : 1 + n_joints],
            orig_state0[1 + n_joints_orig : 1 + n_joints_orig + n_scene],
            np.zeros(n_joints),
            orig_state0[1 + 2 * n_joints_orig + n_scene :],
        ]
    )
    obs = env.set_init_state(init_state)
    return obs, init_state


def is_noop(action, prev_action=None, threshold=1e-4):
    """
    Returns whether an action is a no-op action.

    A no-op action satisfies two criteria:
        (1) All action dimensions, except for the last one (gripper action), are near zero.
        (2) The gripper action is equal to the previous timestep's gripper action.

    Explanation of (2):
        Naively filtering out actions with just criterion (1) is not good because you will
        remove actions where the robot is staying still but opening/closing its gripper.
        So you also need to consider the current state (by checking the previous timestep's
        gripper action as a proxy) to determine whether the action really is a no-op.
    """
    # Special case: Previous action is None if this is the first action in the episode
    # Then we only care about criterion (1)
    if prev_action is None:
        return np.linalg.norm(action[:-1]) < threshold

    # Normal case: Check both criteria (1) and (2)
    gripper_action = action[-1]
    prev_gripper_action = prev_action[-1]
    return np.linalg.norm(action[:-1]) < threshold and gripper_action == prev_gripper_action


def main(args):
    print(f"Regenerating {args.libero_task_suite} dataset with robot {args.robot} ({args.replay_mode} replay)!")

    # Create target directory
    if os.path.isdir(args.libero_target_dir):
        user_input = input(
            f"Target directory already exists at path: {args.libero_target_dir}\nEnter 'y' to overwrite the directory, or anything else to exit: "
        )
        if user_input != "y":
            exit()
    os.makedirs(args.libero_target_dir, exist_ok=True)

    # Failed replays go to a sibling directory with identical file layout, so the same
    # conversion tooling works on either directory
    failures_dir = args.libero_target_dir.rstrip("/") + "_failures"
    os.makedirs(failures_dir, exist_ok=True)

    # Prepare JSON file to record success/false and initial states per episode
    metainfo_json_dict = {}
    variant = "" if (args.robot == "Panda" and args.replay_mode == "delta") else f"_{args.robot.lower()}_{args.replay_mode}"
    metainfo_json_out_path = f"./experiments/robot/libero/{args.libero_task_suite}{variant}_metainfo.json"
    metainfo_dir = os.path.dirname(metainfo_json_out_path)
    os.makedirs(metainfo_dir, exist_ok=True)

    # Create file first if it does not exist
    if not os.path.exists(metainfo_json_out_path):
        with open(metainfo_json_out_path, "x") as f:
            json.dump({}, f)

    with open(metainfo_json_out_path, "w") as f:
        # Just test that we can write to this file (we overwrite it later)
        json.dump(metainfo_json_dict, f)

    # Get task suite
    benchmark_dict = benchmark.get_benchmark_dict()
    task_suite = benchmark_dict[args.libero_task_suite]()
    num_tasks_in_suite = task_suite.n_tasks

    # Setup
    num_replays = 0
    num_success = 0
    num_noops = 0

    for task_id in tqdm.tqdm(range(num_tasks_in_suite)):
        # Get task in suite
        task = task_suite.get_task(task_id)
        env, task_description = get_libero_env(task, args.robot, resolution=args.resolution)
        source_env = get_source_panda_env(task) if (args.robot != "Panda" or args.replay_mode == "absolute") else None

        # Get dataset for task
        orig_data_path = os.path.join(args.libero_raw_data_dir, f"{task.name}_demo.hdf5")
        assert os.path.exists(orig_data_path), f"Cannot find raw data file {orig_data_path}."
        orig_data_file = h5py.File(orig_data_path, "r")
        orig_data = orig_data_file["data"]

        # Skip task if output file already exists
        new_data_path = os.path.join(args.libero_target_dir, f"{task.name}_demo.hdf5")
        if os.path.exists(new_data_path):
            print(f"Skipping task '{task.name}' — output file already exists: {new_data_path}")
            continue

        # Create new HDF5 files for regenerated demos (successes and failures separately)
        new_data_file = h5py.File(new_data_path, "w")
        grp = new_data_file.create_group("data")
        failures_data_path = os.path.join(failures_dir, f"{task.name}_demo.hdf5")
        failures_data_file = h5py.File(failures_data_path, "w")
        failures_grp = failures_data_file.create_group("data")

        num_demos = len(orig_data.keys())
        if args.max_demos_per_task is not None:
            num_demos = min(num_demos, args.max_demos_per_task)
        for i in range(num_demos):
            # Get demo data
            demo_data = orig_data[f"demo_{i}"]
            orig_actions = demo_data["actions"][()]
            orig_states = demo_data["states"][()]

            # Reset environment, set initial state, and wait a few steps for environment to settle
            if source_env is not None:
                # Settle the Panda source env at the demo's initial state (its controller then
                # holds the Panda's initial EEF goal)
                source_env.reset()
                source_env.set_init_state(orig_states[0])
                for _ in range(10):
                    source_env.step(get_libero_dummy_action("llava"))
            if args.robot == "Panda":
                env.reset()
                env.set_init_state(orig_states[0])
                init_state = orig_states[0]
            else:
                _, init_state = drive_to_start_and_splice(env, source_env, orig_states[0], ROBOT_JOINT_DIMS[args.robot])
            for _ in range(10):
                obs, reward, done, info = env.step(get_libero_dummy_action("llava"))
            if args.replay_mode == "absolute":
                set_controller_absolute(env, True)

            # Set up new data lists
            states = []
            actions = []
            ee_states = []
            gripper_states = []
            joint_states = []
            robot_states = []
            agentview_images = []
            eye_in_hand_images = []
            frontview_images = []
            birdview_images = []
            sideview_images = []

            # Replay original demo actions in environment and record observations
            for _, action in enumerate(orig_actions):
                # Skip transitions with no-op actions
                prev_action = actions[-1] if len(actions) > 0 else None
                if is_noop(action, prev_action):
                    print(f"\tSkipping no-op action: {action}")
                    num_noops += 1
                    continue

                if states == []:
                    # In the first timestep, record the state the environment was initialized with
                    # (for Panda this is the original demo's first state, copied over as before)
                    states.append(init_state)
                    if args.robot == "Panda":
                        robot_states.append(demo_data["robot_states"][0])
                    else:
                        robot_states.append(
                            np.concatenate([obs["robot0_gripper_qpos"], obs["robot0_eef_pos"], obs["robot0_eef_quat"]])
                        )
                else:
                    # For all other timesteps, get state from environment and record it
                    states.append(env.sim.get_state().flatten())
                    robot_states.append(
                        np.concatenate([obs["robot0_gripper_qpos"], obs["robot0_eef_pos"], obs["robot0_eef_quat"]])
                    )

                if args.replay_mode == "absolute":
                    # Mirror the original demo on the Panda source env and command the target
                    # robot with the Panda controller's absolute EEF goal
                    source_env.step(action.tolist())
                    exec_action = get_eef_goal_action(source_env, gripper_action=action[-1])
                else:
                    exec_action = action

                # Record executed action (original delta action, or absolute EEF goal action)
                actions.append(exec_action)

                # Record data returned by environment
                if "robot0_gripper_qpos" in obs:
                    gripper_states.append(obs["robot0_gripper_qpos"])
                joint_states.append(obs["robot0_joint_pos"])
                ee_states.append(
                    np.hstack(
                        (
                            obs["robot0_eef_pos"],
                            T.quat2axisangle(obs["robot0_eef_quat"]),
                        )
                    )
                )
                # agentview_images.append(np.ascontiguousarray(obs["agentview_image"][::-1, ::-1]))
                # eye_in_hand_images.append(np.ascontiguousarray(obs["robot0_eye_in_hand_image"][::-1, ::-1]))
                frontview_images.append(np.ascontiguousarray(obs["frontview_image"][::-1, ::-1]))
                # birdview_images.append(np.ascontiguousarray(obs["birdview_image"][::-1, ::-1]))
                sideview_images.append(np.ascontiguousarray(obs["sideview_image"][::-1, ::-1]))

                # Execute action in environment
                obs, reward, done, info = env.step(exec_action.tolist())

            # At end of episode, save the replayed trajectory: successes to the main file,
            # failures to the parallel failures file (reward stays 0 there)
            dones = np.zeros(len(actions)).astype(np.uint8)
            dones[-1] = 1
            rewards = np.zeros(len(actions)).astype(np.uint8)
            if done:
                rewards[-1] = 1
            assert len(actions) == len(ee_states)

            ep_data_grp = (grp if done else failures_grp).create_group(f"demo_{i}")
            obs_grp = ep_data_grp.create_group("obs")
            obs_grp.create_dataset("gripper_states", data=np.stack(gripper_states, axis=0))
            obs_grp.create_dataset("joint_states", data=np.stack(joint_states, axis=0))
            obs_grp.create_dataset("ee_states", data=np.stack(ee_states, axis=0))
            obs_grp.create_dataset("ee_pos", data=np.stack(ee_states, axis=0)[:, :3])
            obs_grp.create_dataset("ee_ori", data=np.stack(ee_states, axis=0)[:, 3:])
            # obs_grp.create_dataset("agentview_rgb", data=np.stack(agentview_images, axis=0))
            # obs_grp.create_dataset("eye_in_hand_rgb", data=np.stack(eye_in_hand_images, axis=0))
            obs_grp.create_dataset("frontview_rgb", data=np.stack(frontview_images, axis=0))
            # obs_grp.create_dataset("birdview_rgb", data=np.stack(birdview_images, axis=0))
            obs_grp.create_dataset("sideview_rgb", data=np.stack(sideview_images, axis=0))
            ep_data_grp.create_dataset("actions", data=actions)
            ep_data_grp.create_dataset("states", data=np.stack(states))
            ep_data_grp.create_dataset("robot_states", data=np.stack(robot_states, axis=0))
            ep_data_grp.create_dataset("rewards", data=rewards)
            ep_data_grp.create_dataset("dones", data=dones)

            if done:
                num_success += 1

            num_replays += 1

            # Record success/false and initial environment state in metainfo dict
            task_key = task_description.replace(" ", "_")
            episode_key = f"demo_{i}"
            if task_key not in metainfo_json_dict:
                metainfo_json_dict[task_key] = {}
            if episode_key not in metainfo_json_dict[task_key]:
                metainfo_json_dict[task_key][episode_key] = {}
            metainfo_json_dict[task_key][episode_key]["success"] = bool(done)
            metainfo_json_dict[task_key][episode_key]["initial_state"] = init_state.tolist()

            # Write metainfo dict to JSON file
            # (We repeatedly overwrite, rather than doing this once at the end, just in case the script crashes midway)
            with open(metainfo_json_out_path, "w") as f:
                json.dump(metainfo_json_dict, f, indent=2)

            # Count total number of successful replays so far
            print(
                f"Total # episodes replayed: {num_replays}, Total # successes: {num_success} ({num_success / num_replays * 100:.1f} %)"
            )

            # Report total number of no-op actions filtered out so far
            print(f"  Total # no-op actions filtered out: {num_noops}")

        # Close HDF5 files, dropping any that stayed empty
        orig_data_file.close()
        for data_file, data_path in [(new_data_file, new_data_path), (failures_data_file, failures_data_path)]:
            is_empty = len(data_file["data"]) == 0
            data_file.close()
            if is_empty:
                os.remove(data_path)
        env.close()
        if source_env is not None:
            source_env.close()
        print(f"Saved regenerated demos for task '{task_description}' at: {new_data_path}")

    print(f"Dataset regeneration complete! Saved new dataset at: {args.libero_target_dir}")
    print(f"Saved failed replays at: {failures_dir}")
    print(f"Saved metainfo JSON at: {metainfo_json_out_path}")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", type=int, default=256, help="Resolution of the images. Example: 256")
    parser.add_argument(
        "--robot",
        type=str,
        default="Panda",
        choices=list(ROBOT_JOINT_DIMS.keys()),
        help="Robot embodiment to replay the demos with. Example: UR5e",
    )
    parser.add_argument(
        "--replay_mode",
        type=str,
        default="delta",
        choices=["delta", "absolute"],
        help="delta: replay the original EEF delta actions. absolute: track the Panda's EEF goal "
        "trajectory with absolute OSC_POSE targets (recorded actions are then absolute EEF goals).",
    )
    parser.add_argument(
        "--max_demos_per_task",
        type=int,
        default=None,
        help="Optionally limit the number of demos replayed per task (for quick success-rate estimates).",
    )
    parser.add_argument(
        "--libero_task_suite",
        type=str,
        choices=["libero_spatial", "libero_object", "libero_goal", "libero_10", "libero_90"],
        help="LIBERO task suite. Example: libero_spatial",
        required=True,
    )
    parser.add_argument(
        "--libero_raw_data_dir",
        type=str,
        help="Path to directory containing raw HDF5 dataset. Example: ./LIBERO/libero/datasets/libero_spatial",
        required=True,
    )
    parser.add_argument(
        "--libero_target_dir",
        type=str,
        help="Path to regenerated dataset directory. Example: ./LIBERO/libero/datasets/libero_spatial_no_noops",
        required=True,
    )
    args = parser.parse_args()

    # Start data regeneration
    main(args)
