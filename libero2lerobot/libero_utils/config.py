ROBOT_JOINT_DIMS = {"franka": 7, "ur5e": 6, "kinova3": 7, "iiwa": 7, "sawyer": 7}


def get_libero_features(robot_type: str = "franka") -> dict:
    """LeRobot feature schema for regenerated LIBERO datasets.

    Only the arm joint dimension differs between embodiments (all use the Panda gripper
    and 7-dim OSC_POSE actions).
    """
    joint_dim = ROBOT_JOINT_DIMS[robot_type]
    return {
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
        # "observation.images.image": { # this is agentview
        #     "dtype": "video",
        #     "shape": (256, 256, 3),
        #     "names": ["height", "width", "rgb"],
        # },
        "observation.images.frontview_image": {
            "dtype": "video",
            "shape": (256, 256, 3),
            "names": ["height", "width", "rgb"],
        },
        # "observation.images.birdview_image": {
        #     "dtype": "video",
        #     "shape": (256, 256, 3),
        #     "names": ["height", "width", "rgb"],
        # },
        "observation.images.sideview_image": {
            "dtype": "video",
            "shape": (256, 256, 3),
            "names": ["height", "width", "rgb"],
        },
        # "observation.images.wrist_image": {
        #     "dtype": "video",
        #     "shape": (256, 256, 3),
        #     "names": ["height", "width", "rgb"],
        # },
        "action": {
            "dtype": "float32",
            "shape": (7,),
            "names": {"motors": ["x", "y", "z", "axis_angle1", "axis_angle2", "axis_angle3", "gripper"]},
        },
    }


LIBERO_FEATURES = get_libero_features("franka")
