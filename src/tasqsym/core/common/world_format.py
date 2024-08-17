# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import typing
import copy

import tasqsym.core.common.structs as tss_structs


class CombinedRobotStruct:
    """Class to hold both the actual state and desired actions, used to pass information between engines in the execution pipeline."""
    def __init__(self, actual_states: tss_structs.CombinedRobotState, desired_actions: tss_structs.CombinedRobotAction, status: tss_structs.Status):
        self.actual_states = copy.deepcopy(actual_states)
        self.desired_actions = copy.deepcopy(desired_actions)
        self.status = status

class FunctionalStates:
    def __init__(self, states: typing.NamedTuple):
        self.states = states

class ComponentProperties:
    def __init__(self, properties: typing.NamedTuple):
        self.properties = properties

class ManipulationProperties:
    def __init__(self, properties: typing.NamedTuple):
        self.properties = properties

class ComponentStruct:
    """Class to hold the component states, used to pass information between engines in the execution pipeline (only for combined simulations)."""
    def __init__(self, name: str, pose: tss_structs.Pose, scale: tss_structs.Point, state: FunctionalStates,
                 url: str, properties: ComponentProperties, manipulation_props: ManipulationProperties):
        """
        The name, pose, scale, state of an object should be enough for updating an object existing in the world.
        All other fields are related to spawning the object into the world.

        name:  name of the object (used as an ID for updating the pose and states)
        pose:  position, orientation pair of the object (initial pose for spawning phase, updated pose for updating phase)
        scale: scale of the object
        state: states related to the object's function (e.g., joint values of an articulated object, amount of liquid in a container)
        url:                file to load from (only used during spawning phase)
        properties:         values to overwrite from the file when spawning the object (e.g., settings about whether an object is static, material randomization)
        manipulation_props: properties specific to manipulation (e.g., gripper-contact locations) which are not written in the file
        """
        self.name = name
        self.pose = pose
        self.scale = scale
        self.state = state
        self.url = url
        self.properties = properties
        self.manipulation_props = manipulation_props

class WorldStruct:
    """A common format to pass the state of the world between engines."""
    def __init__(self, combined_robot_state: CombinedRobotStruct, component_states: list[ComponentStruct]):
        """
        combined_robot_state: state of all robots and desired actions
        component_states:     state of loaded components (only for combined simulation)
        """
        self.combined_robot_state = combined_robot_state
        self.component_states = component_states
        self.status = combined_robot_state.status