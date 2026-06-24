from collections import namedtuple

ROBOT_JOINT_DIMS = {"franka": 7, "ur5e": 6, "kinova3": 7, "iiwa": 7, "sawyer": 7}

# Single source of truth for camera selection, replacing the old comment-toggle across
# regenerate_libero_dataset.py / config.py / libero_utils.py (commit b7d34c8). A runtime
# `--cameras {default,additional}` flag picks one set; every consumer (both regen scripts +
# the converter) reads CAMERA_SETS so the env cameras, HDF5 keys, and LeRobot features stay
# in lockstep.
#   render_cam          - robosuite camera name passed to the env (`camera_names`)
#   obs_image_key       - key in the env's obs dict (`obs[...]`)
#   hdf5_rgb_key        - dataset name written under the HDF5 `obs/` group
#   lerobot_feature_key - LeRobot feature / frame key in the converted dataset
CameraSpec = namedtuple("CameraSpec", ["render_cam", "obs_image_key", "hdf5_rgb_key", "lerobot_feature_key"])

CAMERA_SETS = {
    "default": [
        CameraSpec("agentview", "agentview_image", "agentview_rgb", "observation.images.image"),
        CameraSpec("robot0_eye_in_hand", "robot0_eye_in_hand_image", "eye_in_hand_rgb", "observation.images.wrist_image"),
    ],
    "additional": [
        CameraSpec("frontview", "frontview_image", "frontview_rgb", "observation.images.frontview_image"),
        CameraSpec("sideview", "sideview_image", "sideview_rgb", "observation.images.sideview_image"),
    ],
}


def get_libero_features(robot_type: str = "franka", cameras: str = "default") -> dict:
    """LeRobot feature schema for regenerated LIBERO datasets.

    Only the arm joint dimension differs between embodiments (all use the Panda gripper
    and 7-dim OSC_POSE actions). The image features are built from the selected camera set
    so the converted dataset matches whatever cameras the regeneration used.
    """
    joint_dim = ROBOT_JOINT_DIMS[robot_type]
    features = {
        "observation.state": {
            "dtype": "float32",
            "shape": (8,),
            "names": {"motors": ["x", "y", "z", "axis_angle1", "axis_angle2", "axis_angle3", "gripper", "gripper"]},
        },
        "observation.states.ee_state": {
            "dtype": "float32",
            "shape": (6,),
            "names": {"motors": ["x", "y", "z", "axis_angle1", "axis_angle2", "axis_angle3"]},
        },
        "observation.states.joint_state": {
            "dtype": "float32",
            "shape": (joint_dim,),
            "names": {"motors": [f"joint_{i}" for i in range(joint_dim)]},
        },
        "observation.states.gripper_state": {
            "dtype": "float32",
            "shape": (2,),
            "names": {"motors": ["gripper", "gripper"]},
        },
    }
    for cam in CAMERA_SETS[cameras]:
        features[cam.lerobot_feature_key] = {
            "dtype": "video",
            "shape": (256, 256, 3),
            "names": ["height", "width", "rgb"],
        }
    features["action"] = {
        "dtype": "float32",
        "shape": (7,),
        "names": {"motors": ["x", "y", "z", "axis_angle1", "axis_angle2", "axis_angle3", "gripper"]},
    }
    return features


LIBERO_FEATURES = get_libero_features("franka")
