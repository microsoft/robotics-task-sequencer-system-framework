**input/decoded parameters**

- @attach_direction - [1.0, 1.0, 1.0]
- @context (depends) - "context for example: move the left hand to place a juice to the table"

Vector of floats are represented in the base robot's coordinate.

@context could be used to trigger hint postures when solving the robot's IK etc.

**src configs**

- num_segments: int

**model requirements**

- combiner.setRobotEndEffector("place", decoded_parameters): rule to select end-effector when multiple
- combiner.setSensor(FORCE_6D, "place", decoded_parameters): rule to select camera when multiple

**controller requirements**

- end_effector.contact_link_names of type CONTACT_CENTER
- end_effector.contact_link_states of type CONTACT_CENTER
- sensor.getPhysicsState("Reset", {}) -> status - Status, None
- sensor.getPhysicsState("SurfaceContact", {}) -> status - Status, {contact_environment - bool}