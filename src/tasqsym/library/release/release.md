**input parameters**

- @depart_direction - [1.0, 1.0, 1.0]
- @context (depends) - "context for example: move the left hand to pick a juice from the table"

Vector of floats are represented in the base robot's coordinate.

@context could be used to trigger hint postures when solving the robot's IK etc.

**assumptions**

- "focus end effector must be set by a prior skill"

**src configs**

- num_release_segments: int
- num_depart_segments: int

**model requirements**

- end_effector.getConfigurationForTask("release", decoded_parameters): pose for after release

**controller requirements**

- end_effector.contact_link_names of type CONTACT_CENTER
- end_effector.contact_link_states of type CONTACT_CENTER