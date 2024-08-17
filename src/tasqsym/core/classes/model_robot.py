# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

from abc import abstractmethod, ABC
import typing
import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs


class ModelRobot(ABC):

    unique_id: str  # loaded on __init__()
    role: tss_constants.RobotRole = None  # set before calling super().__init__()

    parent_id: str    # loaded on __init__()
    parent_link: str  # loaded on __init__()

    # state and memory (some skills may copy actions from a previous desired action)

    desired_actions_log: dict[tss_constants.SolveByType, list[tss_structs.RobotAction]] = {}  # preserve most latest actions from skills
    most_latest_action_types: list[tss_constants.SolveByType] = []  # preserve the most latest executed action type

    def __init__(self, model_info: dict):
        if self.role is None:
            print("\
                ModelRobot.role is None, a value is required: Please set one value from tasqsym.common.constants.RobotRole \
                before calling super().__init__(). \
            ")

        self.unique_id = model_info["unique_id"]
        self.parent_id = model_info["parent_id"]
        self.parent_link = model_info["parent_link"]

    @abstractmethod
    def create(self, model_info: dict, configs: dict) -> tss_structs.Status:
        """
        Model creation process if any.
        model_info: model information from the robot structure file
        configs:    model-specific configurations specified in the robot structure file
        ---
        return: success status
        """
        pass

    @abstractmethod
    def destroy(self) -> tss_structs.Status:
        """
        Model destroy process if any.
        ---
        return: success status
        """
        pass

    @abstractmethod
    def getConfigurationForTask(self, task: str, params: dict, latest_state: tss_structs.RobotState) -> tss_structs.RobotState:
        """
        Get a predefined configuration from the robot model.
        task:         the name of the current task requesting the configuration
        params:       information which could be used for determining the configuration
        latest_state: the latest robot state of the target robot
        ---
        return: the predefined configuration
        """
        pass

    def getOrientationTransform(self, control_link: tss_structs.EndEffectorState.ContactAnnotations, desired_transform: tss_structs.Quaternion,
                                known_transforms: typing.Optional[tss_structs.TransformPair], robot_transform: tss_structs.Quaternion) -> tss_structs.Quaternion:
        """
        Skills returning with IK action type will return the desired orientation in some "standard description."
        In the standard description, the identity matrix refers to a pose where the gripper's palm direction faces [1, 0, 0] and the gripper is laid flat Z-up.
        However, each gripper may have a different coordinate description (e.g., palm facing Z-up).
        This function should convert the desired orientation represented in the "standard description" to an orientation represented specific to the gripper.
        When the conversion is unknown (e.g., before grasp), a static matrix transformation should be used to convert between the descriptions.

        control_link:      the link of interest
        desired_transform: the desired orientation of the control link in the "standard description"
        known_transforms:  the transformation between the "gripper-specific description" and the "standard description" (if known)
        robot_transform:   the current orientation of the root (base) robot in the world coordinate
        ---
        return: the orientation of the control link in the robot-specific coordinate
        """
        raise NotImplementedError()

    def generateOrientationTransformPair(self, params: dict) -> dict[tss_structs.EndEffectorState.ContactAnnotations, tss_structs.TransformPair]:
        """
        Generate the transform between the "standard description" and the "gripper-specific description."
        This transform could vary depending on the grasp (i.e., shape of the fingers), therefore, should be set everytime a grasp is performed.

        params: parameters used to get the transform pair (if any)
        ---
        return: a pair of transforms (an orientation in the standard description and its equivalent specific to the gripper)
        """
        raise NotImplementedError()
