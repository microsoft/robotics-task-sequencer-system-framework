# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import typing
import copy
import numpy as np

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.math as tss_math
import tasqsym.core.interface.blackboard as blackboard
import tasqsym.core.interface.envg_interface as envg_interface

import tasqsym.core.classes.skill_base as skill_base
import tasqsym.core.classes.skill_decoder as skill_decoder
import tasqsym.core.common.action_formats as action_formats
import tasqsym.assets.include.tasqsym_utilities as tss_utils


class PickDecoder(skill_decoder.Decoder):

    detach_direction: list[float]
    context: str = ""

    def __init__(self, configs: dict):
        super().__init__(configs)

    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:
        if ("@detach_direction" not in encoded_params) or (type(encoded_params["@detach_direction"]) != list):
            msg = "pick skill error: @detach_direction parameter missing or in wrong format! please check pick.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        self.detach_direction = encoded_params["@detach_direction"]
        if "@context" in encoded_params: self.context = encoded_params["@context"]
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def fillRuntimeParameters(self, encoded_params: dict, board: blackboard.Blackboard, envg: envg_interface.EngineInterface) -> tss_structs.Status:
        # detach direction is a runtime parameter as detach direction is w.r.t. current body orientation
        base_robot_id = envg.kinematics_env.getBaseRobotId()
        robot_states = envg.controller_env.getLatestRobotStates()
        body_state = robot_states.robot_states[base_robot_id]
        root_orientation = body_state.base_state.orientation
        self.detach_direction = tss_math.quat_mul_vec(root_orientation, self.detach_direction)
        self.decoded = True
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def asConfig(self) -> dict:
        return {
            "detach_direction": self.detach_direction,
            "context": self.context
        }


class Pick(skill_base.Skill):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:
        envg.kinematics_env.setEndEffectorRobot("pick", skill_params)
        detach_direction = skill_params["detach_direction"]
        distance, _, _ = tss_math.xyz2dist_ang(detach_direction)

        self.robot_id = envg.kinematics_env.getFocusEndEffectorParentId()
        if self.robot_id == "":
            print("pick skill error: tried to trigger skill but no target end-effector set!")
            return tss_structs.Status(tss_constants.StatusFlags.FAILED)

        self.source_links, eef_state = tss_utils.getEndEffectorPoseToMaintain(tss_utils.ContactAnnotations.CONTACT_CENTER, envg)
        self.eef_rot = eef_state.orientation
        pos = eef_state.position

        _div = self.configs.get("num_segments", int(distance/0.05) + 1)
        ts = [np.array(pos), np.array(pos) + np.array(detach_direction)]
        self.translation_trajectory = []
        for i in range(_div):
            t = float(i+1)/_div
            tv = [(1-t)*ts[0][0]+t*ts[1][0], (1-t)*ts[0][1]+t*ts[1][1], (1-t)*ts[0][2]+t*ts[1][2]]
            self.translation_trajectory.append(copy.deepcopy(tv))

        self.context = skill_params["context"]  # for IK hints

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getAction(self, observation: dict) -> dict:
        return {
            "timestep": observation["observable_timestep"],
            "terminate": (observation["observable_timestep"] == len(self.translation_trajectory))
        }

    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        pt = action["timestep"]
        return tss_structs.CombinedRobotAction(
            "pick",
            {
                self.robot_id: [
                    action_formats.IKAction(
                        tss_structs.Pose(self.translation_trajectory[pt], self.eef_rot),
                        self.source_links, fixed_shape=None, context=self.context
                    )
                ]
            }
        )

    def onFinish(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> typing.Optional[tss_structs.CombinedRobotAction]:
        envg.kinematics_env.freeEndEffectorRobot()
        return None
