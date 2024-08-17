# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import typing
import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.action_formats as action_formats
import tasqsym.core.interface.blackboard as blackboard
import tasqsym.core.interface.envg_interface as envg_interface

import tasqsym.core.classes.skill_base as skill_base
import tasqsym.core.classes.skill_decoder as skill_decoder


class FindDecoder(skill_decoder.Decoder):

    method: str
    target_description: str

    context: str = ""

    def __init__(self, configs: dict):
        super().__init__(configs)

    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:
        if "@target_description" not in encoded_params:
            msg = "find skill error: missing @target_description! please check find.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        
        if type(encoded_params["@target_description"]) != str:
            msg = "find skill error: @target_description parameter in wrong format! please check find.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        self.target_description = encoded_params["@target_description"]

        if "@context" in encoded_params: self.context = encoded_params["@context"]

        self.decoded = True
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def asConfig(self) -> dict:
        return {
            "target_description": self.target_description,
            "context": self.context
        }


class Find(skill_base.Skill):

    method: str
    target_description: str

    def __init__(self, configs: dict):
        super().__init__(configs)

    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:
        self.method = envg.kinematics_env.getRecognitionMethod("find", skill_params)
        self.target_description = skill_params["target_description"]

        envg.kinematics_env.setSensor(tss_constants.SensorRole.CAMERA_3D, "find", skill_params)
        self.robot_id = envg.kinematics_env.getFocusSensorParentId(tss_constants.SensorRole.CAMERA_3D)
        latest_state = envg.controller_env.getLatestRobotStates()
        self.pose_for_recognition: tss_structs.RobotState = envg.kinematics_env.getConfigurationForTask(
            self.robot_id, "find", skill_params, latest_state.robot_states[self.robot_id])

        if self.pose_for_recognition.status.status != tss_constants.StatusFlags.SUCCESS:
            return self.pose_for_recognition.status.status

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getAction(self, observation: dict) -> dict:
        """
        The find skill runs a ready-for-recognition pose, and then the actual recognition at onFinish().
        If there does not exist a ready-for-recognition pose, or if the pose is a base movement, please consider alt skill implementations.
        """
        return {"terminate": (observation["observable_timestep"] == 1)}

    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        return tss_structs.CombinedRobotAction(
            "find",
            {
                self.robot_id: [
                    action_formats.FKAction(self.pose_for_recognition)
                ]
            }
        )

    def onFinish(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> typing.Optional[tss_structs.CombinedRobotAction]:
        camera_id = envg.kinematics_env.getFocusSensorId(tss_constants.SensorRole.CAMERA_3D)
        status, camera_transform = envg.controller_env.getSensorTransform(camera_id)

        if status.status == tss_constants.StatusFlags.SUCCESS:
            base_id = envg.kinematics_env.getBaseRobotId()
            latest_state = envg.controller_env.getLatestRobotStates()
            base_state = tss_structs.Pose(latest_state.robot_states[base_id].base_state.position, latest_state.robot_states[base_id].base_state.orientation)
            status, sensor_data = envg.controller_env.getSceneryState(
                camera_id, self.method,
                tss_structs.Data({"target_description": self.target_description, "camera_transform": camera_transform, "base_transform": base_state}))

        board.setBoardVariable("{find_true}", (status.status == tss_constants.StatusFlags.SUCCESS))

        if status.status == tss_constants.StatusFlags.SUCCESS:
            board.setBoardVariable(
                "{find_result}",
                {
                    "description": self.target_description,
                    "position": sensor_data.detected_pose.position,
                    "orientation": sensor_data.detected_pose.orientation,
                    "scale": sensor_data.detected_scale,
                    "accuracy": sensor_data.detection_accuracy
                }
            )

        envg.kinematics_env.freeSensors(tss_constants.SensorRole.CAMERA_3D)

        return None