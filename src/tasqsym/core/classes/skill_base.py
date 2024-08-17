# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import typing
from abc import abstractmethod, ABC

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.interface.blackboard as blackboard
import tasqsym.core.interface.envg_interface as envg_interface


class SkillAbstract(ABC):
    """
    A template class for designing an arbitrary skill in the system. 
    """
    
    configs: dict = {}

    interruptible_skill: bool  # set to True in config if interruptible
    learned_actions: bool  # set to True in config if skill is learned using ML, used for implementation checks

    def __init__(self, configs: dict):
        """
        Please use init() to do any initiation.
        """
        self.configs = configs
        self.interruptible_skill = self.configs.get("interruptible", False)
        self.learned_actions = self.configs.get("learned_actions", False)

    @abstractmethod
    def init(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:
        """
        Init the skill.
        envg:         access to the robot model and controller states from engines
        skill_params: skill parameters
        """
        pass

    @abstractmethod
    def anyInitiationAction(self, envg: envg_interface.EngineInterface) -> typing.Optional[tss_structs.CombinedRobotAction]:
        """
        Add actions before executing the skill if any (e.g., sending the pre-grasp fingers at start of grasp).
        envg: access to the robot model and controller states from engines
        ---
        return: action
        """
        return None

    @abstractmethod
    def anyPostInitation(self, envg: envg_interface.EngineInterface) -> tss_structs.Status:
        """
        Any initation process after running anyInitiationAction() such as generating a feed-forward trajectory from the current state.
        envg:         access to the robot model and controller states from engines
        skill_params: skill parameters

        Only use this method if anyInitiationAction() is not null AND some initiation calculation is required after the action. Otherwise use init().
        """
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    @abstractmethod
    def appendTaskSpecificStates(self, observation: dict, envg: envg_interface.EngineInterface, training: bool=False) -> dict:
        """
        Add task-specific observations. Observations will be used by getAction() and getTerminal().
        observation: current observation to append to (may also remove default observations if needed)
        envg:        access to the robot model and controller states from engines
        training:    used to return some states only during training
        ---
        return: updated observation
        """
        return observation

    @abstractmethod
    def getAction(self, observation: dict) -> dict:
        """
        Return actions in machine-learning compatible format.
        These actions will be converted using formatAction() to be processed within the system.

        observation: current states
        ---
        return: action in dictionary format
        """
        pass

    @abstractmethod
    def formatAction(self, action: dict) -> tss_structs.CombinedRobotAction:
        """
        Return actions in a valid format that can be processed within the system.
        Note, this is split from getAction for compatibility with some training environments.

        action: action in dictionary form
        ---
        return: formatted action        
        """
        pass
    
    @abstractmethod
    def getTerminal(self, observation: dict, action: dict) -> bool:
        """
        Use only if the skill is learned but uses a manual termination function.
        If both the actions and termination are completely programmed, define everything in getAction().

        observation: terminated or not
        """
        if "terminate" in action: return action["terminate"]
        elif not self.learned_actions:
            raise Exception("skill.getTerminal: Only implement getTerminal() if \
                            actions are learned but skill terminations are manually defined. \
                            Otherwise add a 'terminate' field in getAction().")
        else: raise NotImplementedError("please define")  # please return dict

    @abstractmethod
    def onFinish(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> typing.Optional[tss_structs.CombinedRobotAction]:
        """
        Any finishing process of the skill, especially saving values and/or flags to the blackboard (e.g., run recognition and save results).
        envg:  access to the robot model and controller states from engines
        board: the blackboard to save the values and/or flags to
        ---
        return: action (optional)
        """
        return None


"""
Use below class to use default implementations of abstract methods.
"""

class Skill(SkillAbstract):

    def __init__(self, configs: dict):
        super().__init__(configs)

    def anyInitiationAction(self, envg: envg_interface.EngineInterface) -> typing.Optional[tss_structs.CombinedRobotAction]:
        return super().anyInitiationAction(envg)

    def anyPostInitation(self, envg: envg_interface.EngineInterface) -> tss_structs.Status:
        return super().anyPostInitation(envg)

    def appendTaskSpecificStates(self, observation: dict, envg: envg_interface.EngineInterface, training: bool=False) -> dict:
        return super().appendTaskSpecificStates(observation, envg, training)

    def getTerminal(self, observation: dict, action: dict) -> bool:
        return super().getTerminal(observation, action)

    def onFinish(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> typing.Optional[tss_structs.CombinedRobotAction]:
        return super().onFinish(envg, board)