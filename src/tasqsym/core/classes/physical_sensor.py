# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

from abc import abstractmethod, ABC

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs


class PhysicalSensor(ABC):

    unique_id: str  # loaded on __init__()
    role: tss_constants.SensorRole  # loaded on __init__()

    parent_id: str     # loaded on __init__()
    parent_link: str   # loaded on __init__()
    sensor_frame: str  # loaded on __init__()

    def __init__(self, model_info: dict):
        self.unique_id = model_info["unique_id"]
        self.parent_id = model_info["parent_id"]
        self.parent_link = model_info["parent_link"]
        self.sensor_frame = model_info["sensor_frame"]
        self.role = model_info["type"]  # defined in config so that information can be loaded by the kinematics engine w/o initiating the sensor instance

    @abstractmethod
    def connect(self, model_info: dict, configs: dict) -> tss_structs.Status:
        """
        Connect to the sensor.
        model_info: sensor information from the robot structure file
        configs:    sensor-specific configurations specified in the robot structure file

        return: success status
        """
        pass

    @abstractmethod
    def disconnect(self) -> tss_structs.Status:
        """
        Disconnect from the sensor.
        model_info: sensor information from the robot structure file
        configs:    sensor-specific configurations specified in the robot structure file

        return: success status
        """
        pass

    def getPhysicsState(self, cmd: str, rest: tss_structs.Data) -> tuple[tss_structs.Status, tss_structs.Data]:
        """
        Get sensor data for sensors of type FORCE_6D. Implementation required if FORCE_6D type.
        cmd:       the type of data to obtain from the sensor
        rest:      any additional parameters for obtaining the data

        return: success status and sensor data
        """
        raise NotImplementedError()

    def getSceneryState(self, cmd: str, rest: tss_structs.Data) -> tuple[tss_structs.Status, tss_structs.Data]:
        """
        Get sensor data for sensors of type CAMERA_3D. Implementation required if CAMERA_3D type.
        cmd:       the type of data to obtain from the sensor
        rest:      any additional parameters for obtaining the data

        return: success status and sensor data
        """
        raise NotImplementedError()