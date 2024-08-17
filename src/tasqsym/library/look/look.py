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


class LookDecoder(skill_decoder.Decoder):

    method: str
    target_point: list[float]

    context: str = ""

    def __init__(self, configs: dict):
        super().__init__(configs)

    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:
        if "@target" not in encoded_params:
            msg = "look skill error: missing @target! please check look.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if encoded_params["@target"] is None:
            self.target_point = None
        elif type(encoded_params["@target"]) == str:
            if encoded_params["@target"][0] != "{":
                msg = "look skill error: @target parameter must be blackboard variable! please use the @context parameter for language models."
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

            target_details = board.getBoardVariable(encoded_params["@target"])

            if target_details is None:
                msg = "look skill error: could not find result for %s in blackboard" % encoded_params["@target"]
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            if ("position" not in target_details):
                msg = "look skill error: missing essential details for %s" % encoded_params["@target"]
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

            self.target_point = target_details["position"]
        else:
            msg = "look skill error: @target parameter in wrong format! please check look.md for details."
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if "@context" in encoded_params: self.context = encoded_params["@context"]

        self.decoded = True
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def asConfig(self) -> dict:
        return {
            "target_point": self.target_point,
            "context": self.context
        }


class Look(skill_base.Skill):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:
        envg.kinematics_env.setSensor(tss_constants.SensorRole.CAMERA_3D, "look", skill_params)

        self.target_point = skill_params["target_point"]
        self.context = skill_params["context"]
        sensor_id = envg.kinematics_env.getFocusSensorId(tss_constants.SensorRole.CAMERA_3D)
        self.source_link = envg.controller_env.sensors[sensor_id].parent_link  # TODO: is this way of accessing ok?

        self.robot_id = envg.kinematics_env.getFocusSensorParentId(tss_constants.SensorRole.CAMERA_3D)

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getAction(self, observation: dict) -> dict:
        return {"terminate": (observation["observable_timestep"] == 1)}

    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        return tss_structs.CombinedRobotAction(
            "look",
            {
                self.robot_id: [
                    action_formats.PointToAction(self.target_point, self.source_link, self.context)
                ]
            }
        )

    def onFinish(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> typing.Optional[tss_structs.CombinedRobotAction]:
        envg.kinematics_env.freeSensors(tss_constants.SensorRole.CAMERA_3D)
        return None