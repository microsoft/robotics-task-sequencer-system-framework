# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.action_formats as action_formats

import tasqsym.core.interface.envg_interface as envg_interface

ContactAnnotations = tss_structs.EndEffectorState.ContactAnnotations


"""
Reusable block of logics used by skill modules to obtain certain states.
"""

def getEndEffectorPoseToMaintain(control_link: ContactAnnotations, envg: envg_interface.EngineInterface) -> tuple[list[str], tss_structs.Pose]:
    """
    Returns the previous desired end effector pose if previous action was an IK action.
    Returns the current end effector state (for control_link) otherwise.
    """
    eef_id = envg.kinematics_env.getFocusEndEffectorRobotId()
    manip_id = envg.kinematics_env.getFocusEndEffectorParentId()
    previous_action_types = envg.kinematics_env.getLatestActionTypesInLog(manip_id)
    if tss_constants.SolveByType.INVERSE_KINEMATICS not in previous_action_types:  # desired end effector state is unknown can only refer to current state
        latest_state = envg.controller_env.getLatestRobotStates()
        eef_state: tss_structs.EndEffectorState = latest_state.robot_states[eef_id]
        source_links = [eef_state.contact_link_names[control_link]]
        current_eef_pose = eef_state.contact_link_states[control_link]
        eef_pose = tss_structs.Pose(current_eef_pose.position, current_eef_pose.orientation)
    else:
        eef_action: action_formats.IKAction = envg.kinematics_env.getActionsLog(manip_id, tss_constants.SolveByType.INVERSE_KINEMATICS)[0]
        eef_pose = tss_structs.Pose(eef_action.goal.position, eef_action.goal.orientation)
        source_links = eef_action.source_links
    return source_links, eef_pose

