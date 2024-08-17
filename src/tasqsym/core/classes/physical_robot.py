# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

from abc import abstractmethod, ABC
import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs


class PhysicalRobot(ABC):

    unique_id: str  # loaded on __init__()
    role: tss_constants.RobotRole = None  # set before calling super().__init__()

    parent_id: str    # loaded on __init__()
    parent_link: str  # loaded on __init__()

    def __init__(self, model_info: dict):
        if self.role is None:
            print("\
                PhysicalRobot.role is None, a value is required: Please set one value from tasqsym.common.constants.RobotRole \
                before calling super().__init__(). \
            ")
        self.unique_id = model_info["unique_id"]
        self.parent_id = model_info["parent_id"]
        self.parent_link = model_info["parent_link"]

    @abstractmethod
    def connect(self, model_info: dict, configs: dict) -> tss_structs.Status:
        """
        Connect to the robot controller.
        model_info: controller information from the robot structure file
        configs:    controller-specific configurations specified in the robot structure file
        ---
        return: success status
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> tss_structs.Status:
        """
        Disconnect from the robot controller.
        model_info: controller information from the robot structure file
        configs:    controller-specific configurations specified in the robot structure file
        ---
        return: success status
        """
        pass

    @abstractmethod
    async def getLatestState(self) -> tss_structs.RobotState:
        """
        Get the latest state of the robot from the controller.
        ---
        return: robot status
        """
        pass

    @abstractmethod
    async def emergencyStop(self) -> tss_structs.Status:
        """
        Emergency stop the controller.
        ---
        return: success status
        """
        pass

    def getLinkTransform(self, link_name: str) -> tuple[tss_structs.Status, tss_structs.Pose]:
        """
        Get the link transform from the controller. Robots with an end-effector role may not have such capability and implementation left blank.
        link_name: the link of interest
        ---
        return: the transformation from the world coordinate to the specified link
        """
        raise NotImplementedError()

    async def init(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Controller initiation process (triggered when a preparation skill is at the beginning of a sequence).
        desired_actions: not used
        ref_state:       the current state of the robot
        ---
        return: success status
        """
        print("\
            PhysicalRobot.init implementation required for preparation skill! \
        ")
        raise NotImplementedError()

    async def sendJointAngles(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Send joint angles to the controller. Required for most type of robots.
        desired_actions: a list of desired actions (usually a list of one action about the target joint angles)
        ref_state:       the current state of the robot
        ---
        return: success status
        """
        raise NotImplementedError()

    async def abortJointAngles(self) -> tss_structs.Status:
        """
        Cancel the send joint angle command.
        ---
        return: success status
        """
        raise NotImplementedError()

    async def sendBasePose(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Send base movment to the controller. Required for MOBILE_BASE or MOBILE_MANIPULATOR type robots.
        desired_actions: a list of desired actions (usually a list of one action about the base movement)
        ref_state:       the current state of the robot
        ---
        return: success status
        """
        raise NotImplementedError()

    async def abortBasePose(self) -> tss_structs.Status:
        """
        Cancel the base movement command.
        ---
        return: success status
        """
        raise NotImplementedError()

    async def sendTargetMotion(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Send target poses in cartesian space to the controller.
        desired_actions: a list of desired actions (there could be more than one target pose (e.g., dual arm manipulation))
        ref_state:       the current state of the robot
        ---
        return: success status
        """
        raise NotImplementedError()

    async def abortTargetMotion(self) -> tss_structs.Status:
        """
        Cancel the target pose command.
        ---
        return: success status
        """
        raise NotImplementedError()

    async def sendPointToMotion(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Send point-to targets in cartesian space to the controller.
        desired_actions: a list of desired actions (usually a list of one action about the point-to target)
        ref_state:       the current state of the robot
        ---
        return: success status
        """
        raise NotImplementedError()

    async def abortPointToMotion(self) -> tss_structs.Status:
        """
        Cancel the point to command.
        ---
        return: success status
        """
        raise NotImplementedError()
    
    async def sendControlCommand(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Send a control command to the controller. Not used by the skills in the default skill library but could be used for a custom skill.
        desired_actions: a list of desired actions (usually a list of one action about the command)
        ref_state:       the current state of the robot
        ---
        return: success status
        """
        raise NotImplementedError()

    async def abortControlCommand(self) -> tss_structs.Status:
        """
        Cancel the control command.
        ---
        return: success status
        """
        raise NotImplementedError()
