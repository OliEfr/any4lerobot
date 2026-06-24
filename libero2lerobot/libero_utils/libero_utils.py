from pathlib import Path

import numpy as np
from h5py import File

from libero_utils.config import CAMERA_SETS


def load_local_episodes(input_h5: Path, cameras: str = "default"):
    cam_specs = CAMERA_SETS[cameras]
    with File(input_h5, "r") as f:
        for demo in f["data"].values():
            demo_len = len(demo["obs/ee_states"])
            action = np.array(demo["actions"])
            # NOTE the below transforms the action to [0,1] as originally used by OpenVLA, however we do not require this.
            # (-1: open, 1: close) -> (0: close, 1: open)
            # action = np.concatenate(
            #     [
            #         action[:, :6],
            #         (1 - np.clip(action[:, -1], 0, 1))[:, None],
            #     ],
            #     axis=1,
            # )
            state = np.concatenate(
                [
                    np.array(demo["obs/ee_states"]),
                    np.array(demo["obs/gripper_states"]),
                ],
                axis=1,
            )
            episode = {
                "observation.state": np.array(state, dtype=np.float32),
                "observation.states.ee_state": np.array(demo["obs/ee_states"], dtype=np.float32),
                "observation.states.joint_state": np.array(demo["obs/joint_states"], dtype=np.float32),
                "observation.states.gripper_state": np.array(demo["obs/gripper_states"], dtype=np.float32),
                "action": np.array(action, dtype=np.float32),
            }
            for cam in cam_specs:
                episode[cam.lerobot_feature_key] = np.array(demo[f"obs/{cam.hdf5_rgb_key}"])
            yield [{**{k: v[i] for k, v in episode.items()}} for i in range(demo_len)]
