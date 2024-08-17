**input parameters**

- @destination (required) - [1.0, 1.0, 1.0] / null
- @frame (required if @destination is a vector of floats) - "map" / "current_state" / "{find_result}"
- @orientation (optional) - [0.0, 0.0, 0.0, 1.0]
- @context (depends) - "context for example: move to the kitchen"

@destination is defined with respect to the @frame parameter when using a vector of floats.
@frame="map" indicates relative to some origin of the loaded navigation map,
@frame="current_state" indicates relative to the current base robot's position and values are represented in the base robot's coordinate,
@frame="{find_result}" indicates relative to the values stored during the find skill and are represented in the detected target's coordinate.
Note that the destination refers to the position the robot base will land at the end of the skill.

If @orientation is empty, will maintain the current (/previous desired) base orientation.

@context could be used to calculate the destination w.r.t. the "{find_result}" etc.,
or used to explain the target location (could be some general language for language-based navigation) when @destination is null.

**decoded parameters**

- goal_type - point on map / relative movement / absolute movement / point from vision
- destination - list (coordinate depends on goal type)
- orientation - list (coordinate depends on goal type)
- target_details - dict {position, orientation, scale} (only if goal is from vision)
- context - str

**src configs**

- timeout: float
- stay_position_tolerance: float
- stay_orientation_tolerance: float
- navigation2d: bool

**model requirements**

Below required if using "{find_result}" as the frame:

- combiner.getTaskTransform(task, decoded_parameters, current_robot_states) -> dict[robot_id, dict[frame, pose]]: calculate where to stand given the context

Task transform here refers to the robot's standpoint which could be calculated based on the footprint size or reach range of the combined robot.
Task transform should return keys "map->base" and "base_old->base_new".