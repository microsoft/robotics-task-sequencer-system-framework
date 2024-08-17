**input parameters**

- @destination (required) - [1.0, 1.0, 1.0] / null
- @frame (required if @destination is a vector of floats) - "origin" / "current_state" / "{find_result}"
- @orientation (optional) - [0.0, 0.0, 0.0, 1.0] / "any"
- @context (depends) - "context for example: move the left hand to a table"

@destination is defined with respect to the @frame parameter when using a vector of floats.
@frame="origin" indicates relative to the base robot's origin frame and represented in the base robot's coordinate,
@frame="current_state" indicates relative to the current (/previous desired) end effector position but values are represented in the base robot's coordinate,
@frame="{find_result}" indicates relative to the values stored during the find skill and are represented in the detected target's coordinate.
Note that the destination refers to where the CONTACT_CENTER will land at the end of the skill.

When the @destination is null, bring will try to get a defined posture (configuration) based on @context.

If @orientation is empty, will maintain the current (/previous desired) end effector orientation.
If @orientation is "any," will tell the robot to solve position-only goals when solving the inverse kinematics.

@context could be used to trigger hint postures when solving the robot's inverse kinematics, decide the end effector to perform the skill etc.

**decoded parameters**

- goal_type - coordinate destination or from context
- destination - list (in world coordinate)
- orientation - list (in world coordinate)
- null_orientation_goal - bool
- context - str

**src configs**

- num_segments: int

**model requirements**

- combiner.setRobotEndEffector("bring", decoded_parameters): rule to select end-effector when multiple

Below required if resolving bring from @context instead of @destination.
- manipulator.getConfigurationForTask("bring", decoded_parameters): defined configuration

Below required if using @orientation
- end_effector.getOrientationTransform(CONTACT_CENTER, desired_transform, zero_transforms, base_transform)

**controller requirements**

- end_effector.contact_link_names of type CONTACT_CENTER
- end_effector.contact_link_states of type CONTACT_CENTER
