# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
from tasqsym.core.classes.model_robot import ModelRobot


class SimRobotModel(ModelRobot):

    """Names of joints in the simulated robot."""
    joint_names: list[str] = [
        "arm_joint_0", "arm_joint_1", "arm_joint_2", "arm_joint_3", "arm_joint_4", "arm_joint_5",
        "neck_joint_r", "neck_joint_p", "neck_joint_y"
    ]

    def __init__(self, model_info: dict):
        """self.role must be set before calling super().__init__()."""
        self.role = tss_constants.RobotRole.MOBILE_MANIPULATOR
        super().__init__(model_info)

    def create(self, model_info: dict, configs: dict) -> tss_structs.Status:
        """Return a SUCCESS flag if no specific creation process."""
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def destroy(self) -> tss_structs.Status:
        """Return a SUCCESS flag if no specific destroy process."""
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getConfigurationForTask(self, task: str, params: dict, latest_state: tss_structs.RobotState) -> tss_structs.RobotState:
        """Robots with a MANIPULATOR/MOBILE_MANIPULATOR role require the following predefined configurations."""
        latest_state: tss_structs.ManipulatorState = latest_state
        if task == "find":
            """
            The default find skill requires a predefined configuration which sets the robot to get a good view of the environment.
            In this example, the neck joints are set to some defined angles based on the "context" parameter.
            If the "context" parameter indicates "left" or "right," the neck is set to face those directions.
            Otherwise, the neck will face forward.
            """
            if "right" in "context":
                print("=============== setting the sim robot to face right")
                neck_angles = [0.0, 0.0, -0.3]
            elif "left" in "context":
                print("=============== setting the sim robot to face left")
                neck_angles = [0.0, 0.0, 0.3]
            else:
                print("=============== setting the sim robot to face forward")
                neck_angles = [0.0, 0.0, 0.0]
            return tss_structs.ManipulatorState(
                self.joint_names,
                tss_structs.JointStates(latest_state.joint_states.positions[0:5] + neck_angles),
                latest_state.base_state
            )
        elif task == "bring":
            """
            The default bring skill requires a predefined configuration which sets the arm to some home position.
            Such home position is used to secure an object close to the robot's body after picking up the object.
            In this example, "to self" in the "context" parameter indicates going to the home position.
            Any other "context" is considered invalid and will return an error.
            """
            if "to self" not in params["context"]:
                return tss_structs.ManipulatorState(
                    self.joint_names,
                    latest_state.joint_states,
                    latest_state.base_state,
                    tss_structs.Status(
                        tss_constants.StatusFlags.FAILED,
                        message="sim robot model error: failed to get configuration for an unknown context: " + params["context"])
                )

            print("=============== setting the sim robot to secure object into a home position")
            return tss_structs.ManipulatorState(
                self.joint_names,
                tss_structs.JointStates([0.0, 0.0, -0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
                latest_state.base_state
            )
        else:
            msg = "sim robot model error: unknown task %s in getConfigurationForTask()" % task
            return tss_structs.ManipulatorState(
                self.joint_names,
                latest_state.joint_states,
                latest_state.base_state,
                tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            )
