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


class ReleaseDecoder(skill_decoder.Decoder):

    context: str = ""

    def __init__(self, configs: dict):
        super().__init__(configs)

    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:
        if ("@depart_direction" not in encoded_params) or (type(encoded_params["@depart_direction"]) != list):
            msg = "release skill error: @depart_direction parameter missing or in wrong format! please check release.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        self.depart_direction = encoded_params["@depart_direction"]
        depart_distance = np.linalg.norm(self.depart_direction)
        if abs(depart_distance) < 0.001:
            msg = "release skill error: @depart_direction parameter cannot be of size 0 or smaller than 1[mm]!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        if "@context" in encoded_params: self.context = encoded_params["@context"]
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def fillRuntimeParameters(self, encoded_params: dict, board: blackboard.Blackboard, envg: envg_interface.EngineInterface) -> tss_structs.Status:
        base_robot_id = envg.kinematics_env.getBaseRobotId()
        robot_states = envg.controller_env.getLatestRobotStates()
        body_state = robot_states.robot_states[base_robot_id]
        root_orientation = body_state.base_state.orientation
        self.depart_direction = tss_math.quat_mul_vec(root_orientation, self.depart_direction)
        self.decoded = True
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def asConfig(self) -> dict:
        return {
            "depart_direction": self.depart_direction,
            "context": self.context
        }


class Release(skill_base.Skill):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:
        envg.kinematics_env.setEndEffectorRobot("release", skill_params)
        depart_direction = skill_params["depart_direction"]

        d = 0.15  # constant distance to avoid finger-object collision
        depart_direction = d/np.linalg.norm(depart_direction) * np.array(depart_direction)

        self.eef_id = envg.kinematics_env.getFocusEndEffectorRobotId()
        if self.eef_id == "":
            msg = "release skill error: tried to trigger skill but no target end-effector set!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        self.manip_id = envg.kinematics_env.getFocusEndEffectorParentId()

        self.source_links, eef_state = tss_utils.getEndEffectorPoseToMaintain(tss_utils.ContactAnnotations.CONTACT_CENTER, envg)
        self.eef_rot = eef_state.orientation
        pos = eef_state.position

        joint_postshape: tss_structs.EndEffectorState = envg.kinematics_env.getConfigurationForTask(self.eef_id, "release", skill_params, eef_state)
        if (joint_postshape is None):
            print("release skill error: could not find end-effector robot of name %s" % self.eef_id)
            return tss_structs.Status(tss_constants.StatusFlags.FAILED)
        latest_state = envg.controller_env.getLatestRobotStates()
        current_eef_state: tss_structs.EndEffectorState = latest_state.robot_states[self.eef_id]
        self.joint_shape = current_eef_state

        # note, joint_shape will usually loosen the gripper a bit as looser than commanded joints
        js = [self.joint_shape.joint_states.positions, joint_postshape.joint_states.positions]
        ts = [np.array(pos), np.array(pos) + depart_direction]

        _div1 = self.configs.get("num_release_segments", 3)
        _div2 = self.configs.get("num_depart_segments", 3)
        joint_vector_size = len(self.joint_shape.joint_states.positions)
        self.joint_trajectory = []
        self.translation_trajectory = []
        for i in range(_div1):
            t = float(i+1)/_div1
            jv = [None for x in range(joint_vector_size)]
            for j in range(joint_vector_size):
                jv[j] = (1-t)*js[0][j] + t*js[1][j]
            self.joint_trajectory.append(copy.deepcopy(jv))
            tv = copy.deepcopy(ts[0])
            self.translation_trajectory.append(copy.deepcopy(tv))
        for i in range(_div2):
            self.joint_trajectory.append(copy.deepcopy(self.joint_trajectory[-1]))
            t = float(i+1)/_div2
            tv = [(1-t)*ts[0][0]+t*ts[1][0], (1-t)*ts[0][1]+t*ts[1][1], (1-t)*ts[0][2]+t*ts[1][2]]
            self.translation_trajectory.append(copy.deepcopy(tv))

        self.context = skill_params["context"]  # for IK hints
        
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getAction(self, observation: dict) -> dict:
        return {
            "timestep": observation["observable_timestep"],
            "terminate": (observation["observable_timestep"] == len(self.joint_trajectory))
        }

    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        pt = action["timestep"]
        shape = tss_structs.EndEffectorState(
            self.joint_shape.joint_names,
            tss_structs.JointStates(self.joint_trajectory[pt])
        )
        return tss_structs.CombinedRobotAction(
            "release",
            {
                self.eef_id: [
                    action_formats.FKAction(shape)
                ],
                self.manip_id: [
                    action_formats.IKAction(
                        tss_structs.Pose(self.translation_trajectory[pt], self.eef_rot),
                        self.source_links, shape, self.context
                    )
                ]
            }
        )

    def onFinish(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> typing.Optional[tss_structs.CombinedRobotAction]:
        envg.kinematics_env.freeEndEffectorRobot()
        return None