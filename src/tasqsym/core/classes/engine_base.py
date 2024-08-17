# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

from __future__ import annotations
from abc import abstractmethod, ABC
import typing
import asyncio
import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.world_format as world_format
import tasqsym.core.classes.model_robot as model_robot
import tasqsym.core.classes.physical_robot as physical_robot
import tasqsym.core.classes.robot_combiner as robot_combiner
import tasqsym.core.classes.physical_sensor as physical_sensor


class EngineBase(ABC):
    """
    Base class for engines running under the framework's engine pipeline. 
    """

    class_id: str

    def __init__(self, class_id: str):
        """
        class_id: group identifier (assigned field, not used by the default engines)
        """
        self.class_id = class_id

    @abstractmethod
    async def init(self, general_config: dict, robot_structure_config: dict, engine_config: dict) -> tss_structs.Status:
        """
        Initiation rule of the engine.
        general_config:         general settings for the entire framework (assigned field, not used by the default engines)
        robot_structure_config: robot structure configurations
        engine_config:          configurations specific to this engine
        ---
        return: whether initiation was successful or not
        """
        pass

    async def update(self, world_state: world_format.WorldStruct) -> world_format.WorldStruct:
        """
        Update rule of the engine. Implementation not required for engines not in the pipeline (e.g., DataEngine).
        world_state: updates by an engine from a prior engine in the pipeline
        ---
        return: updates by the engine to pass to a later engine in the pipeline
        """
        raise NotImplementedError()

    @abstractmethod
    async def close(self) -> tss_structs.Status:
        """
        Closing rule of the engine. Implementation not required for engines not in the pipeline (e.g., DataEngine).
        ---
        return: whether close was successful or not
        """
        pass


class KinematicsEngineBase(EngineBase):
    """
    Base class for engines which access the robot model information.
    """

    base_id: str = ""
    end_effector_id: str = ""
    multiple_end_effector_ids: list[str] = []
    sensor_ids: dict[tss_constants.SensorRole, str] = {}

    robot_combiner: robot_combiner.ModelRobotCombiner = None
    robot_models: dict[str, model_robot.ModelRobot] = {}
    sensors: dict[str, dict] = {}  # unique_id, {type, parent_id, parent_joint, sensor_frame}

    coordinate_transforms: dict[str, dict[tss_structs.EndEffectorState.ContactAnnotations, tss_structs.TransformPair]] = {}

    def __init__(self, class_id: str):
        super().__init__(class_id)

    def cleanup(self):
        """
        Common cleanup procedure for the engine. In the child class, call within close().
        """
        self.base_id = ""
        self.end_effector_id = ""
        self.multiple_end_effector_ids = []
        self.sensor_ids = {}
        self.robot_combiner = None
        for _, model in self.robot_models.items():
            model.destroy()
        self.robot_models = {}
        self.sensors = {}

    def setEndEffectorRobot(self, task: str, params: dict):
        """
        Set the focus end-effector of the current task based on the rules defined by the robot model combiner.
        task:   the name of the current task
        params: parameters of the current task to be used for deciding the focus end-effector
        """
        cnt = 0
        for robot_id, model in self.robot_models.items():
            if model.role == tss_constants.RobotRole.END_EFFECTOR:
                end_effector_id = robot_id
                cnt += 1

        if cnt == 1:
            # if only one end-effector role robot, return the one and only
            self.end_effector_id = end_effector_id 
        else:
            self.end_effector_id = self.robot_combiner.setEndEffectorRobot(task, params)

    def setSensor(self, sensor_type: tss_constants.SensorRole, task: str, params: dict):
        """
        Set the focus sensor of the current task based on the rules defined by the robot model combiner.
        sensor_type: the sensor type of the focus sensor
        task:        the name of the current task
        params:      parameters of the current task to be used for deciding the focus sensor
        """
        if sensor_type not in self.sensor_ids: return

        sensors_of_target_type = []
        for sensor_id, sensor in self.sensors.items():
            if sensor["type"] == sensor_type: sensors_of_target_type.append(sensor_id)
        if len(sensors_of_target_type) == 1:
            # if only one sensor with the specified sensor type, return the one and only
            # this way, no need for the robot combiner to implement setSensor() if there is only one sensor
            self.sensor_ids[sensor_type] = sensors_of_target_type[0]
        else:
            self.sensor_ids[sensor_type] = self.robot_combiner.setSensor(sensor_type, task, params)

    def setMultipleEndEffectorRobots(self, task: str, params: dict):
        """
        Set the focus end-effectors of the current task based on the rules defined by the robot model combiner.
        task:   the name of the current task
        params: parameters of the current task to be used for deciding the focus end-effectors
        """
        self.multiple_end_effector_ids = self.robot_combiner.setMultipleEndEffectorRobots(task, params)

    def freeEndEffectorRobot(self):
        """
        Release the focus end-effector.
        """
        self.end_effector_id = ""

    def freeSensors(self, sensor_type: typing.Optional[tss_constants.SensorRole]=None):
        """
        Release the focus sensor.
        sensor_type: the sensor type of the focus sensor to release
        """
        if sensor_type is None:
            for sensor_type, _ in self.sensor_ids:
                self.sensor_ids[sensor_type] = ""
        else:
            if sensor_type in self.sensor_ids: self.sensor_ids[sensor_type] = ""

    def freeMultipleEndEffectorRobots(self):
        """
        Release the focus end-effectors.
        """
        self.multiple_end_effector_ids = []

    def getBaseRobotId(self) -> str:
        """
        Get the robot ID of the root(base) robot in the combined robot tree.
        ---
        return: robot ID
        """
        return self.base_id

    def getFocusEndEffectorRobotId(self) -> str:
        """
        Get the robot ID of the focus end-effector.
        ---
        return: robot ID
        """
        return self.end_effector_id
    
    def getFocusSensorId(self, sensor_type: tss_constants.SensorRole) -> str:
        """
        Get the sensor ID of the focus sensor.
        sensor_type: the sensor type of the focus sensor
        ---
        return: sensor ID
        """
        if sensor_type not in self.sensor_ids: return ""
        return self.sensor_ids[sensor_type]
    
    def getFocusSensorParentId(self, sensor_type: tss_constants.SensorRole) -> str:
        """
        Get the robot ID of the parent of the focus sensor.
        sensor_type: the sensor type of the focus sensor
        ---
        return: robot ID
        """
        if sensor_type not in self.sensor_ids: return ""
        sensor_id = self.sensor_ids[sensor_type]
        if (sensor_id in self.sensors) and ("parent_id" in self.sensors[sensor_id]):
            return self.sensors[sensor_id]["parent_id"]
        else: return ""

    def getFocusEndEffectorParentId(self) -> str:
        """
        Get the robot ID of the parent of the focus end-effector.
        ---
        return: robot ID
        """
        if (self.end_effector_id == "") or (self.end_effector_id not in self.robot_models): return ""
        else: return self.robot_models[self.end_effector_id].parent_id
    
    def getMultipleFocusEndEffectorRobotIds(self) -> list[str]:
        """
        Get the robot IDs of the focus end-effectors.
        ---
        return: robot IDs
        """
        return self.multiple_end_effector_ids

    def getTaskTransform(self, task: str, params: dict, current_robot_states: tss_structs.CombinedRobotState) -> dict[str, dict[str, tss_structs.Pose]]:
        """
        Get the transformation from a specific frame to a specific link using the calculation provided by the robot model combiner.
        task:                 the name of the current task requesting the transformation
        params:               the parameters of the task to use for calculating the transformation
        current_robot_states: the current state of all robots in the combined robot tree
        ---
        return: transformations in the form {robot_id: {"frame->link": transform, ...}} (note, can return for multiple transforms)
        """
        return self.robot_combiner.getTaskTransform(task, params, current_robot_states)

    def getRecognitionMethod(self, task: str, params: dict) -> str:
        """
        Get the recognition method to use for the current task based on the rules defined by the robot model combiner.
        task:   the name of the current task
        params: information which could be used for deciding the recognition method
        ---
        return: the name of the recognition method to use for the current task
        """
        return self.robot_combiner.getRecognitionMethod(task, params)

    def getConfigurationForTask(self, unique_id: str, task: str, params: dict, latest_state: tss_structs.RobotState) -> tss_structs.RobotState:
        """
        Get a predefined configuration from the robot model.
        unique_id:    the robot ID with the configuration definition
        task:         the name of the current task requesting the configuration
        params:       information which could be used for determining the configuration
        latest_state: the latest robot state of the target robot
        ---
        return: the predefined configuration
        """
        if unique_id not in self.robot_models: return None
        return self.robot_models[unique_id].getConfigurationForTask(task, params, latest_state)

    def generateOrientationTransformPair(self, unique_id: str, params: dict):
        """
        Generate and save a transform pair to handle orientation coordinate differences (see model_robot.py).
        Valid only for robots with an end-effector role.

        unique_id: the robot ID of the robot which generates the transform pair
        params:    parameters used to get the transform pair (if any)
        """
        if unique_id not in self.robot_models: return
        self.coordinate_transforms[unique_id] = self.robot_models[unique_id].generateOrientationTransformPair(params)

    def getOrientationTransform(self, unique_id: str, control_link: tss_structs.EndEffectorState.ContactAnnotations, desired_transform: tss_structs.Quaternion,
                                robot_transform: tss_structs.Quaternion) -> tss_structs.Quaternion:
        """
        Get the orientation of a robot's link which fulfills the desired orientation described in the "standard description" (see model_robot.py).
        Valid only for robots with an end-effector role.

        unique_id:         the robot ID (ID of the focus end-effector)
        control_link:      the link of interest
        desired_transform: the desired orientation of the control link in the "standard description"
        robot_transform:   the current orientation of the root (base) robot in the world coordinate
        ---
        return: the orientation of the control link in the robot-specific coordinate
        """
        if unique_id not in self.robot_models: return None
        if (unique_id in self.coordinate_transforms) and (control_link in self.coordinate_transforms[unique_id]):
            coordinate_transforms = self.coordinate_transforms[unique_id][control_link]
        else: coordinate_transforms = None  # not set yet
        return self.robot_models[unique_id].getOrientationTransform(control_link, desired_transform, coordinate_transforms, robot_transform)

    def getActionsLog(self, unique_id: str, action_type: typing.Optional[tss_constants.SolveByType]=None) -> list[tss_structs.RobotAction]:
        """
        Get the list of last used desired actions sent to a specific robot.
        unique_id:   the robot ID of interest
        action_type: filter a specific action type (returns all actions regardless of type if None)
        ---
        return: list of last used desired actions
        """
        if unique_id not in self.robot_models: return []
        # return all logs if None
        if action_type is None:
            import itertools
            return list(itertools.chain.from_iterable(self.robot_models[unique_id].desired_actions_log.values()))
        # return specified log only
        if action_type not in self.robot_models[unique_id].desired_actions_log: return []
        return self.robot_models[unique_id].desired_actions_log[action_type]

    def getLatestActionTypesInLog(self, unique_id: str) -> list[tss_constants.SolveByType]:
        """
        Get the action types of the most recent actions sent to a specific robot.
        unique_id: the robot ID of interest
        ---
        return: list of action types
        """
        if unique_id not in self.robot_models: return []
        return self.robot_models[unique_id].most_latest_action_types


class ControllerEngineBase(EngineBase):
    """
    Base class for engines which access the robot controllers/sensors.
    """

    control_task: typing.Optional[asyncio.Future[list[typing.Any]]] = None
    emergency_stop_request = False

    latest_robot_state: tss_structs.CombinedRobotState = None
    robots: dict[str, physical_robot.PhysicalRobot] = {}
    sensors: dict[str, physical_sensor.PhysicalSensor] = {}  # unique_id, {type, parent_id, parent_joint, sensor_frame} : for TF

    control_in_simulated_world: bool = False  # please override in child class if True
                                              # engine pipeline will call loadComponents() and reset() if True

    def __init__(self, class_id: str):
        super().__init__(class_id)

    def cleanup(self):
        """
        Common cleanup procedure for the engine. In the child class, call within close().
        """
        for _, robot in self.robots.items():
            robot.disconnect()
        self.robots = {}
        self.sensors = {}

    @abstractmethod
    async def updateActualRobotStates(self) -> tss_structs.Status:
        """
        Get the current robot state from the controllers and store to latest_robot_state.
        ---
        return: whether state update was successful or not
        """
        pass
    
    def getLatestRobotStates(self) -> tss_structs.CombinedRobotState:
        """
        Get the latest robot state stored in the engine.
        ---
        return: robot state
        """
        return self.latest_robot_state

    def getSensorTransform(self, sensor_id: str) -> tuple[tss_structs.Status, tss_structs.Pose]:
        """
        Get the transformation between the world origin and the specified sensor's sensor frame.
        sensor_id: the sensor ID of interest
        ---
        return: success status and transformation
        """
        if sensor_id in self.sensors:
            parent_robot_id = self.sensors[sensor_id].parent_id
            if parent_robot_id in self.robots:
                return self.robots[parent_robot_id].getLinkTransform(self.sensors[sensor_id].sensor_frame)
        else: return (tss_structs.Status(tss_constants.StatusFlags.FAILED), tss_structs.Pose())

    async def reset(self) -> tss_structs.Status:
        """
        Reset the engine running the controller if the engine is some simulation environment.
        ---
        return: whether reset was successful
        """
        if self.control_in_simulated_world: raise NotImplementedError()

    async def loadComponents(self, components: list[world_format.ComponentStruct]) -> tss_structs.Status:
        """
        Load components to the engine if the engine running the controller is some simulation environment.
        ---
        return: whether load was successful
        """
        if self.control_in_simulated_world: raise NotImplementedError()

    async def emergencyStop(self) -> tss_structs.Status:
        """
        Emergency stop the controllers connected to the engine.
        ---
        return: whether stop was successful
        """
        stops: list[asyncio.Coroutine] = []
        for _, robot in self.robots.items():
            stops.append(robot.emergencyStop())
        success_flags = await asyncio.gather(*stops, return_exceptions=False)
        status = tss_structs.Status(tss_constants.StatusFlags.SUCCESS)
        for s in success_flags:
            if s.status != tss_constants.StatusFlags.SUCCESS:
                status.message += '; ' + s.message
                status.status = tss_constants.StatusFlags.FAILED
        return status

    def getPhysicsState(self, unique_id: str, cmd: str, rest: tss_structs.Data) -> tuple[tss_structs.Status, tss_structs.Data]:
        """
        Get sensor data for sensors of type FORCE_6D.
        unique_id: the sensor ID
        cmd:       the type of data to obtain from the sensor
        rest:      any additional parameters for obtaining the data
        ---
        return: success status and sensor data
        """
        if unique_id not in self.sensors: return (tss_structs.Status(tss_constants.StatusFlags.FAILED), None)
        if self.sensors[unique_id].role != tss_constants.SensorRole.FORCE_6D:
            return (tss_structs.Status(tss_constants.StatusFlags.FAILED), None)
        return self.sensors[unique_id].getPhysicsState(cmd, rest)

    def getSceneryState(self, unique_id: str, cmd: str, rest: tss_structs.Data) -> tuple[tss_structs.Status, tss_structs.Data]:
        """
        Get sensor data for sensors of type CAMERA_3D.
        unique_id: the sensor ID
        cmd:       the type of data to obtain from the sensor
        rest:      any additional parameters for obtaining the data
        ---
        return: success status and sensor data
        """
        if unique_id not in self.sensors: return (tss_structs.Status(tss_constants.StatusFlags.FAILED), None)
        if self.sensors[unique_id].role != tss_constants.SensorRole.CAMERA_3D:
            return (tss_structs.Status(tss_constants.StatusFlags.FAILED), None)
        return self.sensors[unique_id].getSceneryState(cmd, rest)


class DataEngineBase(EngineBase):
    """
    Base class for engines which access the data storage.
    Used by both the task-sequence encoder (tasqsym_encoder) and decoder (tasqsym.core).
    The encoder should read from the data storage to load data, the decoder should upload the onsite situation to the data storage.
    """

    def __init__(self, class_id: str):
        super().__init__(class_id)

    @abstractmethod
    async def init(self, general_config: dict, robot_structure_config: dict, engine_config: dict) -> tss_structs.Status:
        """
        Used by the decoder as a compatible function in the engine pipeline.
        """
        pass

    @abstractmethod
    def load(self, general_config: dict, robot_structure_config: dict, engine_config: dict) -> tss_structs.Status:
        """
        Used by the encoder to load data.
        general_config:         general settings for the entire framework (assigned field, not used by the default engines)
        robot_structure_config: robot structure configurations
        engine_config:          configurations specific to this engine
        ---
        return: whether initiation was successful or not
        """
        pass

    @abstractmethod
    def getData(self, cmd: str) -> tuple[tss_structs.Status, dict]:
        """
        Get data from the loaded data or directly from the storage.
        cmd: the type of data to get
        ---
        return: success status and data
        """
        pass

    @abstractmethod
    def updateData(self, cmd: str, data: dict) -> tss_structs.Status:
        """
        Update information in the loaded data or in the storage. If loaded data, this will be a local change not affecting the storage.
        cmd:  the type of data to update
        data: the content of the updated information
        ---
        return: whether update was success or not
        """
        pass

    @abstractmethod
    def save(self) -> tuple[tss_structs.Status, dict]:
        """
        Used by the encoder to save data (e.g., output to a file or upload to a storage).
        ---
        return: success status and settings used for storing data (the returned settings should be passed to the decoder)
        """
        pass


class WorldConstructorEngineBase(EngineBase):
    """
    Base class for world constructor engines (initiating simulation engines and episode randomization during training).
    """

    def __init__(self, class_id: str):
        super().__init__(class_id)

    @abstractmethod
    def getSpawnComponents(self, params: dict) -> list[world_format.ComponentStruct]:
        """
        Spawn components within the engine.
        params: parameters for spawning components
        ---
        return: list of spawned components
        """
        pass


class SimulationEngineBase(EngineBase):
    """
    Base class for simulation engines. Use if connecting to a physics and/or rendering engine to simulate sensor values.
    """

    def __init__(self, class_id: str):
        super().__init__(class_id)

    @abstractmethod
    async def reset(self) -> tss_structs.Status:
        """
        Reset the engine world.
        ---
        return: successful or not
        """
        pass

    @abstractmethod
    async def loadRobot(self, init_state: tss_structs.CombinedRobotState) -> tss_structs.Status:
        """
        Load the robot inside the engine world.
        init_state: initial state of the robot on loading.
        ---
        return: successful or not
        """
        pass

    @abstractmethod
    async def loadComponents(self, components: list[world_format.ComponentStruct]) -> tss_structs.Status:
        """
        Load the components inside the engine world if any.
        components: list of components to load into the world
        ---
        return: successful or not
        """
        pass
