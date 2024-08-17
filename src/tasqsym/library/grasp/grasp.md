**input parameters**

- @grasp_type (depends) - "power" / "precision" / "lazy"
- @hand_laterality (depends) - "right" / "left"
- @target (required) - "{find_result}" / "some_object_name"
- @approach_direction (required) - [1.0, 1.0, 1.0]
- @context (depends) - "context for example: move the left hand to a juice using power grasp"

Vector of floats are represented in the base robot's coordinate.

Depending on the @target value, the skill can use the results from a previous "find" skill, or run/re-run recognition within this skill.
The grasp skill will not trigger any movements on the robot before running the recognition (e.g., move the neck or arm)
and the purpose of the recognition is to obtain a more precise recognition before performing the grasp (e.g., re-check the object location using the hand camera).

@context could be used to trigger hint postures when solving the robot's IK etc.

**src configs**

- num_approach_segments: int
- num_grasp_segments: int

**decoded parameters**

- target_pose - Pose
- expected_start_position - np.ndarray
- grasp_type - str
- hand_laterality - str
- context - str

Target pose is represented in the world (map) coordinate.

**model requirements**

- combiner.setRobotEndEffector("grasp", decoded_parameters): rule to select end-effector when multiple
- end_effector.getConfigurationForTask("release", decoded_parameters): pose for before grasp
- end_effector.getConfigurationForTask("grasp", decoded_parameters): pose for at grasp
- end_effector.generateOrientationTransformPair(decoded_parameters): orientation in robot specific description and its equivalent in standard description (X-forward, Z-up)

Below required if running recognition in grasp
- combiner.getRecognitionMethod("grasp", decoded_parameters): rule to select recognition method
- combiner.setSensor(CAMERA_3D, "grasp", decoded_parameters): rule to select camera when multiple

**controller requirements**

- end_effector.contact_link_names of type CONTACT_CENTER
- end_effector.contact_link_states of type CONTACT_CENTER

Below required if running recognition in grasp
- camera_parent.getLinkTransform(camera_id): camera transform at the time of recognition
- camera.getSceneryState(method - str, {target_description - str, camera_transform - Pose, base_transform - Pose, skill_parameters - dict}) -> status - Status, {detected_pose - Pose, detected_scale - np.ndarray, detection_accuracy - float}