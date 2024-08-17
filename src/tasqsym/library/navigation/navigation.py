# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

from __future__ import annotations
from enum import Enum
import numpy as np

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.math as tss_math

import tasqsym.core.interface.blackboard as blackboard
import tasqsym.core.interface.envg_interface as envg_interface

import tasqsym.core.classes.skill_base as skill_base
import tasqsym.core.classes.skill_decoder as skill_decoder
from tasqsym.core.common.action_formats import Nav3DAction


class NavigationDecoder(skill_decoder.Decoder):

    class GoalType(Enum):
        POINT_ON_MAP = 0
        RELATIVE_MOVEMENT = 1
        ABSOLUTE_MOVEMENT = 2
        POINT_FROM_VISION = 3

    nav_goal_type: GoalType
    destination: list[float]
    orientation: list[float]
    target_details: dict = {}
    context: str = ""

    def __init__(self, configs: dict):
        super().__init__(configs)

    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:

        if ("@destination" not in encoded_params):
            msg = "navigation skill error: @destination parameter missing! please check navigation.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if encoded_params["@destination"] is None:
            # parameter is a direct location string handled by the controller
            self.nav_goal_type = NavigationDecoder.GoalType.POINT_ON_MAP
            self.destination = None
            self.orientation = None

        elif type(encoded_params["@destination"]) == list:
            """
            The navigation skill does not have a "fixed frame" to define the destination coordinates.
            Therefore, POINT_FROM_VISION will be relative to the target with target details from the blackboard,
            RELATIVE_MOVEMENT will be relative to the current base position,
            ABSOLUTE_MOVEMENT will be some absolute position on a map.
            """

            if ("@frame" not in encoded_params) or (type(encoded_params["@frame"]) != str):
                msg = "navigation skill error: @frame parameter missing! please check navigation.md for details."
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

            if encoded_params["@frame"][0] == "{":
                self.nav_goal_type = NavigationDecoder.GoalType.POINT_FROM_VISION
                target_details = board.getBoardVariable(encoded_params["@frame"])
                if ("position" not in target_details) or ("orientation" not in target_details) or ("scale" not in target_details):
                    msg = "navigation skill error: missing essential details for %s from blackboard" % encoded_params["@frame"]
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                self.target_details = target_details
                if "@orientation" in encoded_params:
                    print("navigation skill warning: providing an orientation goal w.r.t. vision could lead to an unexpected behavior")
                    self.orientation = encoded_params["@orientation"]
                else: self.orientation = None  # maintain current

            elif encoded_params["@frame"] == "current_state":
                self.nav_goal_type = NavigationDecoder.GoalType.RELATIVE_MOVEMENT
                if "@orientation" in encoded_params: self.orientation = encoded_params["@orientation"]
                else: self.orientation = [0, 0, 0, 1]  # maintain current

            elif encoded_params["@frame"] == "map":
                self.nav_goal_type = NavigationDecoder.GoalType.ABSOLUTE_MOVEMENT
                if "@orientation" in encoded_params: self.orientation = encoded_params["@orientation"]
                else: self.orientation = None  # maintain current

            else:
                msg = "navigation skill error: unexpected value in @frame parameter! please check navigation.md for details."
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            self.destination = encoded_params["@destination"]

        else:
            msg = "navigation skill error: unexpected value in @destination parameter! please check navigation.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if "@context" in encoded_params: self.context = encoded_params["@context"]

        self.decoded = True

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def asConfig(self) -> dict:
        return {
            "goal_type": self.nav_goal_type,
            "destination":  self.destination,
            "orientation": self.orientation,
            "target_details": self.target_details,
            "context": self.context
        }


class Navigation(skill_base.Skill):

    base_robot_id: str
    desired_world_pose: tss_structs.Pose
    desired_local_movement: tss_structs.Pose
    desired_location_name: str = ""
    timeout: float
    stay_position_tolerance: float
    stay: bool = False  # will not send actions if flag is True (e.g., already at location)
    navigation_2d: bool  # if True, will ignore Z-difference during stay calculation

    def __init__(self, configs: dict):
        super().__init__(configs)
        self.timeout = configs.get("timeout", 30.0)
        self.stay_position_tolerance = configs.get("stay_position_tolerance", 0.08)
        self.stay_orientation_tolerance = configs.get("stay_orientation_tolerance", 0.2)
        self.navigation_2d = configs.get("navigation_2d", True)

    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:

        self.context = skill_params["context"]
        goal_type = skill_params["goal_type"]
        self.base_robot_id = envg.kinematics_env.getBaseRobotId()
        current_robot_states = envg.controller_env.getLatestRobotStates()
        current_base_state = current_robot_states.robot_states[self.base_robot_id]

        if goal_type == NavigationDecoder.GoalType.POINT_FROM_VISION:
            # calculate standpoint from target information and context
            link_transforms = envg.kinematics_env.getTaskTransform("navigation", skill_params, current_robot_states)
            self.desired_world_pose = link_transforms[self.base_robot_id]["map->base"]
            self.desired_local_movement = link_transforms[self.base_robot_id]["base_old->base_new"]

        elif goal_type == NavigationDecoder.GoalType.RELATIVE_MOVEMENT:
            self.desired_local_movement = tss_structs.Pose(skill_params["destination"], skill_params["orientation"])
            """Calculate the absolute movement command representation in case the controller does not support relative movements."""
            world_position = np.array(current_base_state.base_state.position) \
                + tss_math.quat_mul_vec(current_base_state.base_state.orientation, np.array(skill_params["destination"]))
            world_orientation = tss_math.quaternion_multiply(current_base_state.base_state.orientation, skill_params["orientation"])
            self.desired_world_pose = tss_structs.Pose(world_position, world_orientation)
            return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)  # always move, no stay check

        elif goal_type == NavigationDecoder.GoalType.ABSOLUTE_MOVEMENT:
            if skill_params["orientation"] is None: skill_params["orientation"] = current_base_state.base_state.orientation
            self.desired_world_pose = tss_structs.Pose(skill_params["destination"], skill_params["orientation"])
            """Calculate the relative movement command representation in case the controller does not support absolute movements."""
            relative_position = tss_math.quat_mul_vec(
                tss_math.quaternion_conjugate(current_base_state.base_state.orientation),
                np.array(skill_params["destination"]) - np.array(current_base_state.base_state.position))
            relative_orientation = tss_math.quaternion_multiply(
                tss_math.quaternion_conjugate(current_base_state.base_state.orientation), skill_params["orientation"])
            self.desired_local_movement = tss_structs.Pose(relative_position, relative_orientation)

        elif goal_type == NavigationDecoder.GoalType.POINT_ON_MAP:
            self.desired_location_name = skill_params["context"]  # assumes desired location name can be obtained through context
            self.desired_world_pose = None  # not used
            self.desired_local_movement = None  # not used
            return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

        # determine whether stay flag should be True
        p_diff = np.array(self.desired_world_pose.position) - np.array(current_robot_states.robot_states[self.base_robot_id].base_state.position)
        if self.navigation_2d: p_diff[2] = 0.0
        p_diff = np.linalg.norm(p_diff)
        q_diff = tss_math.quaternion_multiply(
            self.desired_world_pose.orientation,
            tss_math.quaternion_conjugate(current_robot_states.robot_states[self.base_robot_id].base_state.orientation))
        q_diff = 2*np.arccos(max(min(q_diff[3], 1.0), -1.0))  # avoid float error
        self.stay = (p_diff < self.stay_position_tolerance) and (q_diff < self.stay_orientation_tolerance)

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getAction(self, observation: dict) -> dict:
        return {
            "terminate": (observation["observable_timestep"] == 1)
        }

    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        if self.stay:
            print("navigation skill warning: not sending navigation command as already at desired location")
            return tss_structs.CombinedRobotAction(
                "navigation",
                {
                    self.base_robot_id: [tss_structs.RobotAction(tss_constants.SolveByType.NULL_ACTION, {})]
                }
            )
        return tss_structs.CombinedRobotAction(
            "navigation",
            {
                self.base_robot_id: [Nav3DAction(self.desired_world_pose, self.desired_local_movement, self.desired_location_name, self.context, self.timeout)]
            }
        )
    
