# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import asyncio

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
from tasqsym.core.classes.physical_robot import PhysicalRobot


class SimGripperController(PhysicalRobot):

    def __init__(self, model_info: dict):
        """self.role must be set before calling super().__init__()."""
        self.role = tss_constants.RobotRole.END_EFFECTOR
        super().__init__(model_info)

    def connect(self, model_info: dict, configs: dict) -> tss_structs.Status:
        """Get the name of the contact center link from the robot structure config."""
        self.contact_center_link = configs["contact_center_link"]

        """In this example, there will be no real hardware connections as a simulated gripper."""
        print("=============== connected to the sim gripper controller!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def disconnect(self) -> tss_structs.Status:
        """In this example, no real hardware connections are established as a simulated gripper."""
        print("=============== disconnected from the sim gripper controller!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def getLatestState(self) -> tss_structs.RobotState:
        """
        Grippers must return information about contact links.
        This is crucial as without this information skills cannot determine which link frame to solve the IK.
        At least one link with the "CONTACT_CENTER" link annotation must be returned in the end-effector state.
        """
        contact_link_names = [self.contact_center_link]
        contact_annotations = [tss_structs.EndEffectorState.ContactAnnotations.CONTACT_CENTER]

        """
        Write the logic to get the latest state of the above link from the controller.
        Since this example does not have real hardware connections, will just return some dummy state values.
        """
        print("=============== got the latest state from the sim gripper controller")
        self.base_transform = tss_structs.Pose()
        contact_link_states = [tss_structs.Pose()]
        return tss_structs.EndEffectorState(
            ["gripper_joint"], tss_structs.JointStates([0.0]),
            self.parent_link, self.base_transform,
            contact_link_names, contact_annotations, contact_link_states)

    async def emergencyStop(self) -> tss_structs.Status:
        """
        Write the logic to send the emergency stop to the controller, if the gripper has such capabilities.
        """
        print("=============== emergency stopped sim gripper!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def init(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Initiate the gripper if needed.
        """
        print("=============== initiating sim gripper controller ...")
        await asyncio.sleep(1.0)
        print("=============== initiated the sim gripper controller!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def sendJointAngles(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Send joint angles to the controller.
        For example, like the below:

            action: action_formats.FKAction = desired_actions[0]
            send_task = asyncio.create_task(self.controller.send(action.goal.joint_states.positions))
            res = await send_task

            return res

        """
        print("=============== sending joint angles to the sim gripper controller ...")
        await asyncio.sleep(1.0)
        print("=============== finished sending joint angles to the sim gripper controller!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def abortJointAngles(self) -> tss_structs.Status:
        """
        Write the logic to cancel the joint angle command here.
        """
        print("=============== aborted sim gripper joint angle movement!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)