"""Non-Panda robot embodiments for LIBERO, ported from Adapt3R.

Importing this package registers the robots with robosuite:
- the ManipulatorModel subclasses auto-register in robosuite's REGISTERED_ROBOTS
  via the RobotModelMeta metaclass,
- ROBOT_CLASS_MAPPING tells robosuite to wrap them with SingleArm (same as
  LIBERO does for MountedPanda/OnTheGroundPanda).

LIBERO's problem classes prepend "Mounted"/"OnTheGround" to the robot name
passed via `robots=[...]`, so envs are created with e.g. robots=["UR5e"].

Adding another embodiment = port its two model files from Adapt3R and extend
the mapping below.
"""

from pathlib import Path

import robosuite
from robosuite.robots import ROBOT_CLASS_MAPPING
from robosuite.robots.single_arm import SingleArm

# The vendored Sawyer XML (head meshes marked inertia="shell" because mujoco>=3 rejects
# their near-zero volume) references the original robosuite meshes through this symlink,
# created here so it points at the local robosuite install.
_sawyer_meshes = Path(__file__).parent / "assets" / "sawyer" / "obj_meshes"
if not _sawyer_meshes.is_symlink():
    _sawyer_meshes.symlink_to(
        Path(robosuite.__file__).parent / "models" / "assets" / "robots" / "sawyer" / "obj_meshes"
    )

from .mounted_iiwa import MountedIIWA
from .mounted_kinova3 import MountedKinova3
from .mounted_sawyer import MountedSawyer
from .mounted_ur5e import MountedUR5e
from .on_the_ground_iiwa import OnTheGroundIIWA
from .on_the_ground_kinova3 import OnTheGroundKinova3
from .on_the_ground_sawyer import OnTheGroundSawyer
from .on_the_ground_ur5e import OnTheGroundUR5e

ROBOT_CLASS_MAPPING.update(
    {
        "MountedUR5e": SingleArm,
        "OnTheGroundUR5e": SingleArm,
        "MountedKinova3": SingleArm,
        "OnTheGroundKinova3": SingleArm,
        "MountedIIWA": SingleArm,
        "OnTheGroundIIWA": SingleArm,
        "MountedSawyer": SingleArm,
        "OnTheGroundSawyer": SingleArm,
    }
)
