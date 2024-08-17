**input parameters**

- @target (required) - "{find_result}" / null
- @context (depends) - "context for example: move the left hand to a juice using power grasp"

@context could be used to select the target sensor, or to solve the look action from language models instead of IK

**decoded parameters**

- target_point - np.ndarray
- context - str

**model requirements**

- combiner.setSensor(CAMERA_3D, "look", decoded_parameters): rule to select camera when multiple
