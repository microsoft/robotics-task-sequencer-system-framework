# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import typing

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.interface.blackboard as blackboard
import tasqsym.core.interface.envg_interface as envg_interface

import tasqsym.core.classes.skill_base as skill_base
import tasqsym.core.classes.skill_decoder as skill_decoder
import tasqsym.core.common.action_formats as action_formats


class NodeDecoder(skill_decoder.Decoder):

    set_variable: str=""
    set_value: typing.Any=None

    def __init__(self, configs: dict):
        super().__init__(configs)

    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:
        if ("@print_text" not in encoded_params):
            msg = "node decoder error: @print_text parameter missing!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        
        if ("@set_variable" in encoded_params):
            self.set_variable = encoded_params["@set_variable"]
            if ("@set_value" not in encoded_params):
                msg = "node decoder error: @set_value parameter missing!"
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            self.set_value = encoded_params["@set_value"]

        self.print_text = encoded_params["@print_text"]

        self.decoded = True
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def asConfig(self) -> dict:
        return {
            "print_text": self.print_text,
            "set_variable": self.set_variable,
            "set_value": self.set_value
        }


class Node(skill_base.Skill):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:
        self.print_text = skill_params["print_text"]
        self.set_variable = skill_params["set_variable"]
        self.set_value = skill_params["set_value"]

        """Below works with sim robot as only one end-effector and will return default."""
        envg.kinematics_env.setEndEffectorRobot("node", skill_params)
        self.robot_id = envg.kinematics_env.getFocusEndEffectorParentId()

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getAction(self, observation: dict) -> dict:
        return {"terminate": (observation["observable_timestep"] == 1)}

    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        """Assumes using with sim robot. Calling action to ensure sleep at each node."""
        print("::::::::::::::::::::::::::: %s" % self.print_text)
        return tss_structs.CombinedRobotAction(
            "node",
            {
                self.robot_id: [action_formats.FKAction(tss_structs.RobotState(tss_structs.Pose()))]  # does not matter with sim robot
            }
        )

    def onFinish(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> typing.Optional[tss_structs.CombinedRobotAction]:
        envg.kinematics_env.freeEndEffectorRobot()

        if self.set_variable != "": board.setBoardVariable(self.set_variable, self.set_value)

        return None
