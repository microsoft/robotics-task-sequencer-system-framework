# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.interface.blackboard as blackboard
import tasqsym.core.interface.envg_interface as envg_interface

import tasqsym.core.classes.skill_base as skill_base
import tasqsym.core.classes.skill_decoder as skill_decoder


class PrepareDecoder(skill_decoder.Decoder):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:
        self.decoded = True
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def asConfig(self) -> dict:
        return {}  # no configs returned


class Prepare(skill_base.Skill):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:
        rs = envg.controller_env.getLatestRobotStates()
        self.robot_ids = rs.robot_states.keys()
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getAction(self, observation: dict) -> dict:
        return {
            "terminate": (observation["observable_timestep"] == 1)
        }

    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        init_statement = {}
        for unique_id in self.robot_ids:
            init_statement[unique_id] = [tss_structs.RobotAction(tss_constants.SolveByType.INIT_ROBOT, {})]
        return tss_structs.CombinedRobotAction("prepare", init_statement)
