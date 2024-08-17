# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import typing
import copy

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs


class FKAction(tss_structs.RobotAction):
    """Structure to specify the desired forward kinematics goal."""
    def __init__(self, goal: tss_structs.RobotState, configs={}):
        """
        goal:    the desired command values to send to the robot
        configs: not recommended for usage
        """
        super().__init__(tss_constants.SolveByType.FORWARD_KINEMATICS, configs)
        self.goal = copy.deepcopy(goal)

class IKAction(tss_structs.RobotAction):
    """Structure to specify the desired inverse kinematics goal."""
    def __init__(self, goal: tss_structs.Pose, source_links: list[str], fixed_shape: typing.Optional[tss_structs.RobotState]=None,
                 context: str='', start_posture: str='', end_posture: str='', posture_rate=1.0, configs={}):
        """
        The IKAction is tied to the manipulator robot. However, the source links (control links) are defined in the end-effector robot.
        For all skills other than grasping, the source link should be irrelevant to the shape (joint values) of the end-effector.

        goal:          position and orientation goal in the world coordinate to solve
        source_links:  the link to align the position and orientation (if size 2, first element is for position, second is for orientation)
        fixed_shape:   any robot state information to be aware of (if the contact link is a fingertip, requires the finger shape of the end-effector)
        context:       context may provide hints when solving IK
        start_posture: posture constraint A (optional if using Body Role Division IK)
        end_posture:   posture constraint B (optional if using Body Role Division IK)
        posture_rate:  how much to blend posture constraint A and B (optional if using Body Role Division IK)
        configs:       not recommended for usage
        """
        super().__init__(tss_constants.SolveByType.INVERSE_KINEMATICS, configs)
        self.goal = copy.deepcopy(goal)
        self.source_links = source_links
        self.fixed_shape = copy.deepcopy(fixed_shape)
        self.context = context
        self.start_posture = start_posture
        self.end_posture = end_posture
        self.posture_rate = posture_rate

class Nav3DAction(tss_structs.RobotAction):
    """Structure to specify the desired navigation goal."""
    def __init__(self, pose: tss_structs.Pose, relative_pose: tss_structs.Pose, dest_name: str,
                 context: str, timeout: float=-1, configs={}):
        """
        The same navigation goal is described in multiple ways (pose, relative_pose, dest_name) as the way of commanding may differ for each system.
        pose:          the desired position and orientation (the base's facing forward direction) in the world coordinate
        relative_pose: the desired position and direction relative to the current state of the base (may be used instead of pose for certain navigation systems)
        dest_name:     name of the location (may be used for certain navigation systems)
        context:       context may be used to provide some extra navigation configurations (e.g., lower convergence threshold if accuracy is not required)
        timeout:       abort task if takes longer than specified seconds (negative indicates infinity)
        configs:       not recommended for usage
        """
        super().__init__(tss_constants.SolveByType.NAVIGATION3D, configs)
        self.pose = pose
        self.relative_pose = relative_pose
        self.dest_name = dest_name
        self.context = context
        self.timeout = timeout

class PointToAction(tss_structs.RobotAction):
    """Structure to specify the desired point-to goal."""
    def __init__(self, point: tss_structs.Point, source_link: str, context: str, configs={}):
        """
        A type of IK action which, instead of providing a desired pose, provides a desired target point a link should point to.
        point:        the position in the world coordinate the source_link should point to
        source_link:  the link which points to the target point
        context:      context may be used to define the pose of the links when performing the pointing action
        """
        super().__init__(tss_constants.SolveByType.POINT_TO_IK, configs)
        self.point = point
        self.source_link = source_link
        self.context = context

class CommandAction(tss_structs.RobotAction):
    """Structure to specify a goal command."""
    def __init__(self, commands: dict, configs={}):
        """
        commands: goal command
        """
        super().__init__(tss_constants.SolveByType.CONTROL_COMMAND, configs)
        self.commands = commands
