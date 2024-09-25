# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs


class ModelRobotCombiner:

    def __init__(self):
        pass

    def setEndEffectorRobot(self, task: str, params: dict) -> str:
        """
        Set the focus end-effector for the task.
        Implementation required only if the combined robot has multiple manipulators.

        task:   the name of the task requesting the focus end-effector
        params: parameters of the task to be used for the decision of the focus end-effector

        return: robot ID of the set end-effector
        """
        raise NotImplementedError()

    def setSensor(self, sensor_type: tss_constants.SensorRole, task: str, params: dict) -> str:
        """
        Set the focus sensor for the task.
        Implementation required only if the combined robot has multiple cameras.

        sensor_type: the sensor type of the focus sensor
        task:        the name of the task requesting the focus sensor
        params:      parameters of the current task to be used for the decision of the focus sensor

        return: sensor ID of the set sensor
        """
        raise NotImplementedError()

    def setMultipleEndEffectorRobots(self, task: str, params: dict) -> list[str]:
        """
        Set multiple focus end-effectors for the task.
        Implementation required only if the combined robot has multiple manipulators and performs a multiple manipulator task.

        task:   the name of the task requesting the focus end-effectors
        params: parameters of the task to be used for the decision of the focus end-effector

        return: list of end-effector robot IDs that were set
        """
        raise NotImplementedError()

    def getTaskTransform(self, task: str, params: dict, current_robot_states: tss_structs.CombinedRobotState) -> dict[str, dict[str, tss_structs.Pose]]:
        """
        Get the transformation from a specific frame to a specific link.
        Implementation required for certain skills (e.g., to calculate the footprint location for a navigation skill given parameters).

        task:                 the name of the task requesting the transformation
        params:               the parameters of the task to use for calculating the transformation
        current_robot_states: the current state of all robots in the combined robot tree

        return: transformations in the form {robot_id: {"frame->link": transform, ...}} (note, can return for multiple transforms)
        """
        raise NotImplementedError()

    def getRecognitionMethod(self, task: str, params: dict) -> str:
        """
        Get the recognition method to use for the specified task. Implementation required for certain skills (see each skill.md).

        task:   the name of the task requesting the method
        params: information which could be used for deciding the recognition method

        return: the name of the recognition method to use
        """
        raise NotImplementedError()