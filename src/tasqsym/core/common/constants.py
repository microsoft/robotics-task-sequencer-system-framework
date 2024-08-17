# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

from enum import Enum


"""Status signals."""

class StatusFlags(Enum):
    SUCCESS = 1
    FAILED = -1
    ABORTED = -2
    UNEXPECTED = -3
    SKIPPED = -4
    ESCAPED = -5
    UNKNOWN = -6

class StatusReason(Enum):
    NONE = 0
    SUCCESSFUL_TERMINATION = 1
    CONNECTION_ERROR = 2
    PROCESS_FAILURE = 3  # includes IK failure
    OTHER = 4

"""Skill action return types."""

class SolveByType(Enum):
    NULL_ACTION = 0
    FORWARD_KINEMATICS = 1
    INVERSE_KINEMATICS = 2
    NAVIGATION3D = 3
    POINT_TO_IK = 4
    CONTROL_COMMAND = 5
    INIT_ROBOT = 6

"""Robot types."""

class RobotRole(Enum):
    MOBILE_BASE = 0
    MANIPULATOR = 1
    END_EFFECTOR = 2
    MOBILE_MANIPULATOR = 3

"""Sensor types."""

class SensorRole(Enum):
    CAMERA_3D = 0
    FORCE_6D = 1