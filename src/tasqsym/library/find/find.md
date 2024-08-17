**input/decoded parameters**

- @target_description (required) - "some_object_name" / "some description about the object using a sentence"
- @context (depends) - "context for example: find the juice in the kitchen"

@context could be used to choose the recognition method etc.

**output variables**

- {find_result} - {"name": "some_object_name", "position": [1.0, 1.0, 1.0], "orientation": [0.0, 0.0, 0.0, 1.0], "scale": [1.0, 1.0, 1.0], "accuracy": "low"}
- {find_true} - true

Vector of floats are represented in the world (map) coordinate.

**model requirements**

- combiner.getRecognitionMethod("find", decoded_parameters): rule to select recognition method
- combiner.setSensor(CAMERA_3D, "find", decoded_parameters): rule to select camera when multiple
- camera_parent.getConfigurationForTask("find", decoded_parameters): arm/body configuration for recognition

**controller requirements**

- camera_parent.getLinkTransform(camera_id): camera transform at the time of recognition
- camera.getSceneryState(method - str, {target_description - str, camera_transform - Pose, base_transform - Pose}) -> status - Status, {detected_pose - Pose, detected_scale - np.ndarray, detection_accuracy - float}