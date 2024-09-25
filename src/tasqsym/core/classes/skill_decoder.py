# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

from abc import abstractmethod, ABC

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.interface.blackboard as blackboard
import tasqsym.core.interface.envg_interface as envg_interface


class DecoderAbstract(ABC):

    decoded: bool = False
    configs: dict = {}

    def __init__(self, configs: dict):
        self.configs = configs

    @abstractmethod
    def decode(self, encoded_params: dict, board: blackboard.Blackboard) -> tss_structs.Status:
        """
        Parameter decoding irrelevant to the current robot state or the current state of the environment.
        encoded_params: task parameters
        board:          the blackboard to read the values and/or flags from

        return: success status
        """
        pass

    @abstractmethod
    def fillRuntimeParameters(self, encoded_params: dict, board: blackboard.Blackboard, envg: envg_interface.EngineInterface) -> tss_structs.Status:
        """
        Parameter decoding relevant to the current robot state or the current state of the environment.
        encoded_params: task parameters
        board:          the blackboard to read the values and/or flags from
        envg:           access to the robot model and controller states from engines

        return: success status
        """
        print("skill decoder warning: fillRuntimeParameters not implemented, assuming no runtime parameters")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    @abstractmethod
    def asConfig(self) -> dict:
        """
        Return the parameters in a format that can be loaded by the skill module.

        return: parameters
        """
        pass

    def isReadyForExecution(self) -> bool:
        """
        Return whether the decoding procedure including filling runtime parameters has finished.

        return: finished state
        """
        return self.decoded


"""Use below class to use default implementations of abstract methods."""
class Decoder(DecoderAbstract):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def fillRuntimeParameters(self, encoded_params: dict, board: blackboard.Blackboard, envg: envg_interface.EngineInterface) -> tss_structs.Status:
        return super().fillRuntimeParameters(encoded_params, board, envg)