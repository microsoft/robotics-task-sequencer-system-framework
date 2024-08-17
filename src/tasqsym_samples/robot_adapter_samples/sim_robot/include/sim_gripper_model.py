# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import typing
import numpy as np

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.math as tss_math
from tasqsym.core.classes.model_robot import ModelRobot


class SimGripperModel(ModelRobot):

    def __init__(self, model_info: dict):
        """self.role must be set before calling super().__init__()."""
        self.role = tss_constants.RobotRole.END_EFFECTOR
        super().__init__(model_info)

    def create(self, model_info: dict, configs: dict) -> tss_structs.Status:
        """Return a SUCCESS flag if no specific creation process."""
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def destroy(self) -> tss_structs.Status:
        """Return a SUCCESS flag if no specific destroy process."""
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getConfigurationForTask(self, task: str, params: dict, latest_state: tss_structs.RobotState) -> tss_structs.RobotState:
        """Robots with an END_EFFECTOR role require the following predefined configurations."""
        latest_state: tss_structs.EndEffectorState = latest_state
        if task == "grasp":
            """
            The default grasp skill implementation requires a predefined configuration to indicate the shape of the fingers when performing a grasp.
            In this example, it is assumed that the gripper uses an I/O signal which closes the grippers with 1.0 and opens with 0.0.
            The example also assumes that the gripper has a low-level controller which automatically controls the strength of the grasp.
            If the gripper does not have such capabilities, please consider using a custom grasp skill implementation.
            """
            print("=============== setting the sim gripper to close the grippers")
            return tss_structs.EndEffectorState(
                ["gripper_joint"], tss_structs.JointStates([1.0])
            )
        elif task == "release":
            """
            The default grasp skill implementation requires a predefined configuration to indicate the shape of the fingers when the gripper is open.
            In this example, it is assumed that the gripper uses an I/O signal which closes the grippers with 1.0 and opens with 0.0.
            """
            print("=============== setting the sim gripper to open the grippers")
            return tss_structs.EndEffectorState(
                ["gripper_joint"], tss_structs.JointStates([0.0])
            )
        else:
            msg = "sim gripper model error: unknown task %s in getConfigurationForTask()" % task
            return tss_structs.EndEffectorState(
                ["gripper_joint"], latest_state.joint_states,
                status=tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            )

    def getOrientationTransform(self, control_link: tss_structs.EndEffectorState.ContactAnnotations, desired_transform: tss_structs.Quaternion,
                                known_transforms: typing.Optional[tss_structs.TransformPair], robot_transform: tss_structs.Quaternion) -> tss_structs.Quaternion:
        """In this example, the gripper's palm direction differs by 45 degrees around the Z-axis compared to the standard description."""
        if known_transforms is None:
            return tss_math.quaternion_multiply(desired_transform, [0, 0, np.sin(np.deg2rad(-45)*.5), np.cos(np.deg2rad(-45)*.5)])
        else:
            return tss_math.quaternion_multiply(
                desired_transform,
                tss_math.quaternion_multiply(
                    tss_math.quaternion_conjugate(known_transforms.base),
                    known_transforms.transform)
            )

    def generateOrientationTransformPair(self, params: dict) -> dict[tss_structs.EndEffectorState.ContactAnnotations, tss_structs.TransformPair]:
        """In this example, the gripper's palm direction differs by 45 degrees around the Z-axis compared to the standard description."""
        q_standard = [0, 0, 0, 1]  # the identity matrix in the "standard description" (pose s.t. gripper's palm direction faces [1, 0, 0] and is laid flat Z-up)
        q_robot = [0, 0, np.sin(np.deg2rad(-45)*.5), np.cos(np.deg2rad(-45)*.5)]  # gripper's orientation command to achieve pose q_standard
        return {
            tss_structs.EndEffectorState.ContactAnnotations.CONTACT_CENTER: tss_structs.TransformPair(q_standard, q_robot)
        }
