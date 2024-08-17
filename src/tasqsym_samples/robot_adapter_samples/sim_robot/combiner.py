# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import numpy as np

import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.math as tss_math


class SimRobotCombiner:

    def __init__(self):
        pass
    
    # setEndEffectorRobot() not needed as only one end-effector

    # setSensor() not needed as only one camera

    # setMultipleEndEffectorRobots() not needed as no multi-arm manipulation in the default skill library

    def getTaskTransform(self, task: str, params: dict, current_robot_states: tss_structs.CombinedRobotState) -> dict[str, dict[str, tss_structs.Pose]]:
        """If the robot uses the navigation skill combined with object detection, must have the below implementation"""
        if (task == "navigation"):
            base_robot_name = "mobile_base_with_arm"  # make sure to change this to the robot ID in the combined robot structure tree
            target_pose = tss_structs.Pose(params["target_details"]["position"], params["target_details"]["orientation"])
            des_pos_rel_to_target = params["destination"]
            des_orn_rel_to_target = params["orientation"]
            pos = np.array(target_pose.position) + np.array(tss_math.quat_mul_vec(target_pose.orientation, des_pos_rel_to_target))
            current_state = current_robot_states.robot_states[base_robot_name].base_state
            if des_orn_rel_to_target is None: rot = current_state.orientation  # maintain the current orientation
            else: rot = tss_math.quaternion_multiply(target_pose.orientation, des_orn_rel_to_target)  # a desired orientation was provided

            rel_pos = tss_math.quat_mul_vec(
                tss_math.quaternion_conjugate(current_state.orientation), pos - np.array(current_state.position))
            rel_rot = tss_math.quaternion_multiply(tss_math.quaternion_conjugate(current_state.orientation), rot)
            return {
                base_robot_name: {
                    "map->base": tss_structs.Pose(pos, rot),
                    "base_old->base_new": tss_structs.Pose(rel_pos, rel_rot)
                }
            }

    def getRecognitionMethod(self, task: str, params: dict) -> str:
        """The sim_camera example only has one valid recognition method, thus no need to return a value for method."""
        return ""
