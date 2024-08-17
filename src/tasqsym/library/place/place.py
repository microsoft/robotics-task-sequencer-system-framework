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


class PlaceDecoder(skill_decoder.Decoder):

    attach_direction: list[float]
    context: str = ""

    def __init__(self, configs: dict):
        super().__init__(configs)

    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:
        if ("@attach_direction" not in encoded_params) or (type(encoded_params["@attach_direction"]) != list):
            msg = "place skill error: @attach_direction parameter missing or in wrong format! please check place.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        self.attach_direction = encoded_params["@attach_direction"]
        if "@context" in encoded_params: self.context = encoded_params["@context"]
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def fillRuntimeParameters(self, encoded_params: dict, board: blackboard.Blackboard, envg: envg_interface.EngineInterface) -> tss_structs.Status:
        # attach direction is a runtime parameter as detach direction is w.r.t. current body orientation
        base_robot_id = envg.kinematics_env.getBaseRobotId()
        robot_states = envg.controller_env.getLatestRobotStates()
        body_state = robot_states.robot_states[base_robot_id]
        root_orientation = body_state.base_state.orientation
        self.attach_direction = tss_math.quat_mul_vec(root_orientation, self.attach_direction)
        self.decoded = True
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def asConfig(self) -> dict:
        return {
            "attach_direction": self.attach_direction,
            "context": self.context
        }


class Place(skill_base.Skill):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:
        envg.kinematics_env.setEndEffectorRobot("place", skill_params)

        self.velocity_direction = skill_params["attach_direction"]
        distance, _, _ = tss_math.xyz2dist_ang(self.velocity_direction)
        self.velocity_direction /= distance

        v_approach = max(distance - 0.02, 0.0) * self.velocity_direction
        div = int(max(distance - 0.02, 0) / 0.05) + 1  # number of iterations at approach
        self.iterations_until_preplace_finish = div + 1

        self.robot_id = envg.kinematics_env.getFocusEndEffectorParentId()
        if self.robot_id == "":
            print("place skill error: tried to trigger skill but no target end-effector set!")
            return tss_structs.Status(tss_constants.StatusFlags.FAILED)

        envg.kinematics_env.setSensor(tss_constants.SensorRole.FORCE_6D, "place", skill_params)
        self.sensor_id = envg.kinematics_env.getFocusSensorId(tss_constants.SensorRole.FORCE_6D)
        envg.controller_env.getPhysicsState(self.sensor_id, "reset", None)

        self.source_links, eef_state = tss_utils.getEndEffectorPoseToMaintain(tss_utils.ContactAnnotations.CONTACT_CENTER, envg)
        self.eef_rot = eef_state.orientation
        pos = eef_state.position

        p_preplace = np.array(pos) + v_approach
        ts = [np.array(pos), p_preplace, p_preplace]
        # interpolate between preplace and place
        self.raw_translation = []
        for i in range(div):
            t = float(i+1)/div
            if np.linalg.norm(v_approach) < 0.02:
                tv = [ts[0][0], ts[0][1], ts[0][2]]
            elif i < div-1:
                tv = [(1-t)*ts[0][0]+t*ts[1][0], (1-t)*ts[0][1]+t*ts[1][1], (1-t)*ts[0][2]+t*ts[1][2]]
            else:
                tv = [ts[1][0], ts[1][1], ts[1][2]]
            self.raw_translation.append(tv)

        # place
        post_iters = 100  # number of max iterations to try to detect a "placed" feedback
        for i in range(post_iters+1):
            tv = copy.deepcopy(self.raw_translation[-1])
            self.raw_translation.append(tv)

        self.context = skill_params["context"]  # for IK hints

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def anyInitiationAction(self, envg: envg_interface.EngineInterface) -> typing.Optional[tss_structs.CombinedRobotAction]:
        return None

    def anyPostInitation(self, envg: envg_interface.EngineInterface) -> tss_structs.Status:
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def appendTaskSpecificStates(self, observation: dict, envg: envg_interface.EngineInterface, training: bool=False) -> dict:
        sensor_definitions = tss_structs.Data({})  # no parameters as highly-dependent on each sensor
        status, force_feedback = envg.controller_env.getPhysicsState(self.sensor_id, "SurfaceContact", sensor_definitions)
        # if needed, use status
        if force_feedback.contact_environment: observation["ptg13_plane_contact"] = -1
        else: observation["ptg13_plane_contact"] = 10
        return observation

    def getAction(self, observation: dict) -> dict:
        dist = 0.005
        if observation["observable_timestep"] < self.iterations_until_preplace_finish:
            action_dict = {"velocity_direction_deviation": 0.0, "terminate": (observation["ptg13_plane_contact"] <= 0)}
        else:  ## moving 5 mm each iteration till collision
            n_add = observation["observable_timestep"] - self.iterations_until_preplace_finish + 1
            action_dict = {"velocity_direction_deviation": n_add*dist, "terminate": (observation["ptg13_plane_contact"] <= 0)}
        action_dict["timestep"] = observation["observable_timestep"]  # required for trajectory revising skills
        return action_dict

    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        pt = action["timestep"]
        tv = self.raw_translation[pt]
        if abs(action["velocity_direction_deviation"]) >= 0.00001: # preplace ~ place
            """
            Below action adds some value (proportional to the number of elapsed iteration) to the preplace position.
            Since movement in each iteration is relatively small, an "absolute goal position ensuring distance decrementation to the target plane"
            should be used instead of a "relative goal position calculated from the current robot arm position."
            If used relative goals, there is a chance that the arm position oscillates at a position (due to poor control on small movement),
            thus, never getting close to the target plane.
            """
            tv = np.array(tv) + action["velocity_direction_deviation"]*self.velocity_direction  # move closer toward plane
        print(tv)
        return tss_structs.CombinedRobotAction(
            "place",
            {
                self.robot_id: [
                    action_formats.IKAction(
                        tss_structs.Pose(tv, self.eef_rot),
                        self.source_links, context=self.context
                    )
                ]
            }
        )

    def onFinish(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> typing.Optional[tss_structs.CombinedRobotAction]:
        envg.kinematics_env.freeEndEffectorRobot()
        return None