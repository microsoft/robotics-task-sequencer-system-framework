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

ContactAnnotations = tss_structs.EndEffectorState.ContactAnnotations


class GraspDecoder(skill_decoder.Decoder):

    expected_start_position: np.ndarray
    goal_position: np.ndarray
    goal_orientation: np.ndarray

    grasp_type: str
    hand_laterality: str

    context: str = ""

    def __init__(self, configs: dict):
        super().__init__(configs)

    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:

        """
        @grasp_type could be used to change the skill implementation depending on the type,
        run custom recognition modules based on the type,
        or to set the target end effector for robots with multiple manipulators.
        """
        if ("@grasp_type" not in encoded_params) or (type(encoded_params["@grasp_type"]) != str):
            msg = "grasp skill error: @grasp_type parameter missing or in wrong format! please check grasp.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        """@hand_laterality could be used to decide the target end effector for robots with multiple manipulators."""
        if ("@hand_laterality" not in encoded_params) or (type(encoded_params["@hand_laterality"]) != str):
            msg = "grasp skill error: @hand_laterality parameter missing or in wrong format! please check grasp.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if ("@target" not in encoded_params) or (type(encoded_params["@target"]) != str):
            msg = "grasp skill error: @target parameter missing or in wrong format! please check grasp.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if ("@approach_direction" not in encoded_params) or (type(encoded_params["@approach_direction"]) != list):
            msg = "grasp skill error: @approach_direction parameter missing or in wrong format! please check grasp.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        self.grasp_type = encoded_params["@grasp_type"]
        self.hand_laterality = encoded_params["@hand_laterality"]

        """@context could be used as a hint for solving IK, if running recognition method, etc."""
        if "@context" in encoded_params: self.context = encoded_params["@context"]

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def fillRuntimeParameters(self, encoded_params: dict, board: blackboard.Blackboard, envg: envg_interface.EngineInterface) -> tss_structs.Status:

        approach_direction_body = np.array(encoded_params["@approach_direction"])

        base_robot_id = envg.kinematics_env.getBaseRobotId()
        current_robot_states = envg.controller_env.getLatestRobotStates()
        current_base_orientation = current_robot_states.robot_states[base_robot_id].base_state.orientation
        approach_direction = tss_math.quat_mul_vec(current_base_orientation, approach_direction_body)
        length, _, _ = tss_math.xyz2dist_ang(approach_direction)
        approach_direction /= length


        if encoded_params["@target"][0] == "{":
            """If @target is in the form "{find_result}", obtain position and orientation from the blackboard."""

            target_details = board.getBoardVariable(encoded_params["@target"])

            if target_details is None:
                msg = "grasp skill error: could not find result for %s in blackboard" % encoded_params["@target"]
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        else:
            """If @target is a usual string, obtain position and orientation by running detailed recognition."""

            envg.kinematics_env.setSensor(tss_constants.SensorRole.CAMERA_3D, "grasp", encoded_params)  # could be hand camera etc.
            camera_id = envg.kinematics_env.getFocusSensorId(tss_constants.SensorRole.CAMERA_3D)
            _, camera_transform = envg.controller_env.getSensorTransform(camera_id)
            base_state = tss_structs.Pose(current_robot_states.robot_states[base_robot_id].base_state.position, current_base_orientation)

            status, sensor_data = envg.controller_env.getSceneryState(
                camera_id, envg.kinematics_env.getRecognitionMethod("grasp", encoded_params),
                tss_structs.Data({
                    "target_description": encoded_params["@target"], "skill_parameters": tss_structs.Data(encoded_params),
                    "camera_transform": camera_transform, "base_transform": base_state}))
            if status.status != tss_constants.StatusFlags.SUCCESS: return status

            target_details = {
                "description": encoded_params["@target"],
                "position": sensor_data.detected_pose.position,
                "orientation": sensor_data.detected_pose.orientation,
                "scale": sensor_data.detected_scale,
                "accuracy": sensor_data.detection_accuracy
            }
            envg.kinematics_env.freeSensors(tss_constants.SensorRole.CAMERA_3D)


        if ("position" not in target_details) or ("orientation" not in target_details):
            msg = "grasp skill error: missing essential details for %s" % encoded_params["@target"]
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        self.goal_position = target_details["position"]
        self.goal_orientation = target_details["orientation"]

        self.expected_start_position = np.array(self.goal_position) - 0.15*np.array(approach_direction)

        self.decoded = True
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def asConfig(self) -> dict:
        return {
            "target_pose": tss_structs.Pose(self.goal_position, self.goal_orientation),
            "expected_start_position": self.expected_start_position,
            "grasp_type": self.grasp_type,
            "hand_laterality": self.hand_laterality,
            "context": self.context
        }


class Grasp(skill_base.Skill):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:

        # set the robot end-effector to use for the skill
        envg.kinematics_env.setEndEffectorRobot("grasp", skill_params)
        self.eef_id = envg.kinematics_env.getFocusEndEffectorRobotId()
        self.manip_id = envg.kinematics_env.getFocusEndEffectorParentId()
        base_id = envg.kinematics_env.getBaseRobotId()

        latest_state = envg.controller_env.getLatestRobotStates()
        eef_state: tss_structs.EndEffectorState = latest_state.robot_states[self.eef_id]
        self.joint_preshape: tss_structs.EndEffectorState = envg.kinematics_env.getConfigurationForTask(self.eef_id, "release", skill_params, eef_state)
        if (self.joint_preshape is None):
            print("grasp skill error: could not find end-effector robot of name %s" % self.eef_id)
            return tss_structs.Status(tss_constants.StatusFlags.FAILED)
        self.joint_shape: tss_structs.EndEffectorState = envg.kinematics_env.getConfigurationForTask(self.eef_id, "grasp", skill_params, eef_state)

        # specify name of grasp origin
        self.source_links = [eef_state.contact_link_names[ContactAnnotations.CONTACT_CENTER]]
        goal_pose: tss_structs.Pose = skill_params["target_pose"]
        self.p_robot2goal = np.array(goal_pose.position)
        # get orientation in robot-specific description
        envg.kinematics_env.generateOrientationTransformPair(self.eef_id, skill_params)  # values may depend on grasp type
        self.q_robot2goal = envg.kinematics_env.getOrientationTransform(
            self.eef_id, ContactAnnotations.CONTACT_CENTER, goal_pose.orientation, latest_state.robot_states[base_id].base_state.orientation)

        self.expected_start_position: np.ndarray = skill_params["expected_start_position"]

        self.context = skill_params["context"]  # for IK hints

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def anyInitiationAction(self, envg: envg_interface.EngineInterface) -> typing.Optional[tss_structs.CombinedRobotAction]:
        robot_state = envg.controller_env.getLatestRobotStates()
        return tss_structs.CombinedRobotAction(
            "grasp",
            {
                self.eef_id: [
                    action_formats.FKAction(self.joint_preshape)
                ],
                self.manip_id: [
                    action_formats.IKAction(
                        tss_structs.Pose(self.expected_start_position, self.q_robot2goal),
                        self.source_links, self.joint_preshape, self.context
                    )
                ]
            }
        )

    def anyPostInitation(self, envg: envg_interface.EngineInterface) -> tss_structs.Status:
        robot_state = envg.controller_env.getLatestRobotStates()
        eef_state: tss_structs.EndEffectorState = robot_state.robot_states[self.eef_id]

        pos = eef_state.contact_link_states[ContactAnnotations.CONTACT_CENTER].position
        rot = eef_state.contact_link_states[ContactAnnotations.CONTACT_CENTER].orientation

        # values used for creating the reference motion
        js = [self.joint_preshape.joint_states.positions, self.joint_shape.joint_states.positions]  # preshape and grasp finger configuration
        # hand translation
        ts = [pos, self.p_robot2goal]

        # interpolate between pregrasp and grasp
        _div = self.configs.get("num_approach_segments", 5)
        _post_iters = self.configs.get("num_grasp_segments", 10)
        joint_vector_size = len(self.joint_preshape.joint_states.positions)
        self.joint_trajectory = []
        self.translation_trajectory = []
        self.rotation_trajectory = []
        for i in range(_div):
            t = float(i+1)/_div
            jv = [None for x in range(joint_vector_size)]
            if _div == 1:  # do not close during approach if a single-step approach
                jv = copy.deepcopy(js[0])
            else:
                for j in range(joint_vector_size):
                    jv[j] = (1-t)*js[0][j] + t*js[1][j]
            self.joint_trajectory.append(copy.deepcopy(jv))
            tv = [(1-t)*ts[0][0]+t*ts[1][0], (1-t)*ts[0][1]+t*ts[1][1], (1-t)*ts[0][2]+t*ts[1][2]]
            self.translation_trajectory.append(copy.deepcopy(tv))
            rv = copy.deepcopy(rot)
            self.rotation_trajectory.append(copy.deepcopy(rv))
        # continue grasp for a while
        for i in range(_post_iters):
            t = float(i+1)/_post_iters
            if _div == 1:  # begin grasp here if a single-step approach
                for j in range(joint_vector_size):
                    jv[j] = (1-t)*js[0][j] + t*js[1][j]
            else:
                jv = self.joint_trajectory[-1]
            tv = copy.deepcopy(self.translation_trajectory[-1])
            rv = copy.deepcopy(self.rotation_trajectory[-1])
            self.joint_trajectory.append(copy.deepcopy(jv))
            self.translation_trajectory.append(copy.deepcopy(tv))
            self.rotation_trajectory.append(copy.deepcopy(rv))

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getAction(self, observation: dict) -> dict:
        return {
            "timestep": observation["observable_timestep"],
            "terminate": (observation["observable_timestep"] == len(self.joint_trajectory))
        }

    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        pt = action["timestep"]
        shape = tss_structs.EndEffectorState(
            self.joint_preshape.joint_names,
            tss_structs.JointStates(self.joint_trajectory[pt])
        )
        return tss_structs.CombinedRobotAction(
            "grasp",
            {
                self.eef_id: [
                    action_formats.FKAction(shape)
                ],
                self.manip_id: [
                    action_formats.IKAction(
                        tss_structs.Pose(self.translation_trajectory[pt], self.rotation_trajectory[pt]),
                        self.source_links, shape, self.context
                    )
                ]
            }
        )

    def onFinish(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> typing.Optional[tss_structs.CombinedRobotAction]:
        envg.kinematics_env.freeEndEffectorRobot()
        return None
