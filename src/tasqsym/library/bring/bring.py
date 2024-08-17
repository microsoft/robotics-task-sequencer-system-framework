# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

from __future__ import annotations
import typing
import enum
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


class BringDecoder(skill_decoder.Decoder):

    class BringType(enum.Enum):
        COORDINATE_DESTINATION = 0
        FROM_CONTEXT = 1

    bring_type: BringType
    destination: typing.Any
    orientation: typing.Optional[list[float]] = None
    null_orientation_goal: bool = False

    context: str = ""

    def __init__(self, configs: dict):
        super().__init__(configs)

    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:
        if ("@destination" not in encoded_params):
            msg = "bring skill error: @destination parameter missing! please check bring.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if "@context" in encoded_params: self.context = encoded_params["@context"]

        if (encoded_params["@destination"] == None) and ("@context" in encoded_params):
            self.bring_type = BringDecoder.BringType.FROM_CONTEXT
            self.destination = None

        elif type(encoded_params["@destination"]) == list:
            if ("@frame" not in encoded_params) or (type(encoded_params["@frame"]) != str):
                msg = "bring skill error: @frame parameter missing! please check bring.md for details."
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            self.bring_type = BringDecoder.BringType.COORDINATE_DESTINATION

        else:
            msg = "bring skill error: @destination parameter in wrong format! please check bring.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def fillRuntimeParameters(self, encoded_params: dict, board: blackboard.Blackboard, envg: envg_interface.EngineInterface) -> tss_structs.Status:
        if self.bring_type != BringDecoder.BringType.COORDINATE_DESTINATION:
            self.decoded = True
            return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

        latest_state = envg.controller_env.getLatestRobotStates()
        base_id = envg.kinematics_env.getBaseRobotId()
        base_state = latest_state.robot_states[base_id]

        if ("@orientation" in encoded_params) and (type(encoded_params["@orientation"]) == str):
            if encoded_params["@orientation"] != "any":
                # only valid command of this type is any
                msg = "bring skill error: unexpected value in @orientation parameter! please check bring.md for details."
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            self.null_orientation_goal = True
        else: self.null_orientation_goal = False

        if encoded_params["@frame"] == "origin":
            # relative to base robot's origin frame
            self.destination = np.array(base_state.base_state.position) + np.array(tss_math.quat_mul_vec(base_state.base_state.orientation, encoded_params["@destination"]))
            if (not self.null_orientation_goal) and ("@orientation" in encoded_params) and (encoded_params["@orientation"] is not None):
                self.orientation = tss_math.quaternion_multiply(base_state.base_state.orientation, encoded_params["@orientation"])

        elif encoded_params["@frame"] == "current_state":
            # relative to current end effector robot's position
            envg.kinematics_env.setEndEffectorRobot("bring", {"context": self.context})
            _, eef_state = tss_utils.getEndEffectorPoseToMaintain(tss_utils.ContactAnnotations.CONTACT_CENTER, envg)
            self.destination = np.array(eef_state.position) + np.array(tss_math.quat_mul_vec(base_state.base_state.orientation, encoded_params["@destination"]))
            if (not self.null_orientation_goal) and ("@orientation" in encoded_params) and (encoded_params["@orientation"] is not None):
                self.orientation = tss_math.quaternion_multiply(base_state.base_state.orientation, encoded_params["@orientation"])

        elif encoded_params["@frame"][0] == "{":
            # from values in blackboard
            details = board.getBoardVariable(encoded_params["@frame"])
            # store position only, maintains current orientation unless @orientation is specified
            if ("position" not in details) or ("orientation" not in details):
                msg = "bring skill error: missing essential details from blackboard."
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            self.destination = np.array(details["position"]) + np.array(tss_math.quat_mul_vec(details["orientation"], encoded_params["@destination"]))
            if (not self.null_orientation_goal) and ("@orientation" in encoded_params) and (encoded_params["@orientation"] is not None):
                self.orientation = tss_math.quaternion_multiply(details["orientation"], encoded_params["@orientation"])

        else:
            msg = "bring skill error: unexpected value in @frame parameter! please check bring.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        self.decoded = True
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def asConfig(self) -> dict:
        """null explicitly indicates no orientation goal, whereas, orientation none just means no goal was set (=use default settings)"""
        return {
            "goal_type": self.bring_type,
            "destination": self.destination,  # in world coordinate defined by the base robot
            "orientation": self.orientation,  # in world coordinate defined by the base robot
            "null_orientation_goal": self.null_orientation_goal,
            "context": self.context
        }


class Bring(skill_base.Skill):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:
        envg.kinematics_env.setEndEffectorRobot("bring", skill_params)
        self.robot_id = envg.kinematics_env.getFocusEndEffectorParentId()

        if skill_params["goal_type"] == BringDecoder.BringType.FROM_CONTEXT:
            latest_state = envg.controller_env.getLatestRobotStates()
            skill_params["target_eefs"] = [envg.kinematics_env.getFocusEndEffectorRobotId()]
            self.pose_for_bring = envg.kinematics_env.getConfigurationForTask(self.robot_id, "bring", skill_params, latest_state.robot_states[self.robot_id])
            if self.pose_for_bring.status.status != tss_constants.StatusFlags.SUCCESS: return self.pose_for_bring.status

        elif skill_params["goal_type"] == BringDecoder.BringType.COORDINATE_DESTINATION:
            self.pose_for_bring = None
            p_goal = skill_params["destination"]

            # # waypoint handling and orienting not supported
            # p_subgoal = None
            # q_subgoal = None

            # get current end-effector position
            self.source_links, eef_state = tss_utils.getEndEffectorPoseToMaintain(tss_utils.ContactAnnotations.CONTACT_CENTER, envg)
            pos = np.array(eef_state.position)

            self.null_orientation_goal = skill_params["null_orientation_goal"]

            """below orientation goal is ignored at send if null_orientation_goal is true"""
            if skill_params["orientation"] is not None:
                rot = skill_params["orientation"]  # orientation in standard description
                # convert to robot specific description
                base_id = envg.kinematics_env.getBaseRobotId()
                latest_state = envg.controller_env.getLatestRobotStates()
                rot = envg.kinematics_env.getOrientationTransform(
                    envg.kinematics_env.getFocusEndEffectorRobotId(), tss_utils.ContactAnnotations.CONTACT_CENTER,
                    rot, latest_state.robot_states[base_id].base_state.orientation)
            else: rot = list(eef_state.orientation)

            # if (p_subgoal is not None) and (q_subgoal is not None):
            #     tt = [pos, p_subgoal, p_goal]
            #     rt = [rot, q_subgoal, q_subgoal]
            #     div = [
            #         self.configs.get("num_segments", int(np.linalg.norm(p_subgoal - pos) / 0.05) + 1),
            #         self.configs.get("num_segments", int(np.linalg.norm(p_goal - p_subgoal) / 0.05) + 1)
            #     ]
            # else:

            tt = [pos, p_goal]
            rt = [rot, rot]
            div = [self.configs.get("num_segments", int(np.linalg.norm(p_goal - pos) / 0.05) + 1)]

            self.translation_trajectory = []
            self.rotation_trajectory = []
            for k in range(len(tt) - 1):
                for i in range(div[k]):
                    t = float(i+1)/div[k]
                    tv = [(1-t)*tt[k][0]+t*tt[k+1][0], (1-t)*tt[k][1]+t*tt[k+1][1], (1-t)*tt[k][2]+t*tt[k+1][2]]
                    self.translation_trajectory.append(copy.deepcopy(tv))
                    if np.linalg.norm(np.array(rt[k]) - np.array(rt[k+1])) > 0.00001:
                        rv = tss_math.quaternion_slerp(rt[k], rt[k+1], t)
                    else:
                        rv = copy.deepcopy(rt[k+1])
                    self.rotation_trajectory.append(copy.deepcopy(rv))

        self.context = skill_params["context"]  # for IK hints

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getAction(self, observation: dict) -> dict:
        if self.pose_for_bring is not None:
            return {"terminate": (observation["observable_timestep"] == 1)}
        else:
            return {
                "timestep": observation["observable_timestep"],
                "terminate": (observation["observable_timestep"] == len(self.translation_trajectory))
            }

    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        if self.pose_for_bring is not None:
            return tss_structs.CombinedRobotAction(
                "bring",
                {
                    self.robot_id: [
                        action_formats.FKAction(self.pose_for_bring)
                    ]
                }
            )
        else:
            pt = action["timestep"]
            if self.null_orientation_goal: rot = None
            else: rot = self.rotation_trajectory[pt]
            return tss_structs.CombinedRobotAction(
                "bring",
                {
                    self.robot_id: [
                        action_formats.IKAction(
                            tss_structs.Pose(self.translation_trajectory[pt], rot),
                            self.source_links, fixed_shape=None,
                            context=self.context
                        )
                    ]
                }
            )

    def onFinish(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> typing.Optional[tss_structs.CombinedRobotAction]:
        envg.kinematics_env.freeEndEffectorRobot()
        return None
