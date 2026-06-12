"""Ported from Adapt3R (adapt3r/envs/libero/robots/on_the_ground_sawyer.py)."""

from pathlib import Path

import numpy as np

from robosuite.models.robots.manipulators.manipulator_model import ManipulatorModel


class OnTheGroundSawyer(ManipulatorModel):
    """
    Sawyer is a witty single-arm robot designed by Rethink Robotics.

    Args:
        idn (int or str): Number or some other unique identification string for this robot instance
    """

    def __init__(self, idn=0):
        # Vendored copy with inertia="shell" on the head meshes (mujoco>=3 rejects their
        # near-zero volume); meshes are symlinked from the robosuite install.
        super().__init__(str(Path(__file__).parent / "assets/sawyer/robot.xml"), idn=idn)

    @property
    def default_mount(self):
        return None

    @property
    def default_gripper(self):
        return "PandaGripper"

    @property
    def default_controller_config(self):
        return "default_sawyer"

    @property
    def init_qpos(self):
        return np.array([0, -1.18, 0.00, 2.18, 0.00, 0.57, -1.57])

    @property
    def base_xpos_offset(self):
        return {
            "bins": (-0.5, -0.1, 0),
            "empty": (-0.6, 0, 0),
            "table": lambda table_length: (-0.16 - table_length / 2, 0, 0),
            "coffee_table": lambda table_length: (-0.16 - table_length / 2, 0, 0.41),
            "living_room_table": lambda table_length: (
                -0.16 - table_length / 2,
                0,
                0.42,
            ),
        }

    @property
    def top_offset(self):
        return np.array((0, 0, 1.0))

    @property
    def _horizontal_radius(self):
        return 0.5

    @property
    def arm_type(self):
        return "single"
