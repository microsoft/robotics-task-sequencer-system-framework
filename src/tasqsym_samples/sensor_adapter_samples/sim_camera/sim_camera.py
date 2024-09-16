# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import numpy as np
import json
import os

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.math as tss_math
from tasqsym.core.classes.physical_sensor import PhysicalSensor


class SimCamera(PhysicalSensor):

    def __init__(self, model_info: dict):
        super().__init__(model_info)

    def connect(self, model_info: dict, configs: dict) -> tss_structs.Status:
        """
        Write connections to the real hardware here.
        In this example, will load dummy values from a file instead.
        """

        """Load dummy values from dummy values file."""
        self.dummy_values_filename = configs["dummy_values_file"]

        if not os.path.isfile(self.dummy_values_filename):
            print("sim vision warning: detected an invalid dummy file path. code will crash when called getSceneryState()")
            return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

        with open(self.dummy_values_filename) as f: self.dummy_values = json.load(f)
        if "items" not in self.dummy_values:
            msg = "sim vision error: missing 'items' field in dummy values file"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        print("=============== connected to the sim vision sensor!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getSceneryState(self, cmd: str, rest: tss_structs.Data) -> tuple[tss_structs.Status, tss_structs.Data]:
        """
        Write logic to obtain detection results from the sensor.
        Make sure returned values are in world coordinate and orientations in standard description.
        In this example, will use dummy values.
        """

        """Read dummy values."""
        dummy_position = self.dummy_values["items"][rest.target_description]["position"]
        dummy_orientation = self.dummy_values["items"][rest.target_description]["orientation"]
        frame = self.dummy_values["items"][rest.target_description]["frame"]

        """Convert to world coordinate if needed."""
        if frame == "base":
            base_state: tss_structs.Pose = rest.base_transform
            basep = base_state.position
            baseq = base_state.orientation
            pos = np.array(basep) + np.array(tss_math.quat_mul_vec(baseq, dummy_position))
            rot = tss_math.quaternion_multiply(baseq, dummy_orientation)
        else:
            pos = dummy_position
            rot = dummy_orientation

        print("=============== got recognition results from the sim vision sensor!")
        return (
            tss_structs.Status(tss_constants.StatusFlags.SUCCESS),
            tss_structs.Data({
                "detected_pose": tss_structs.Pose(pos, rot),
                "detected_scale": np.array([1.0, 1.0, 1.0]),  # not detected
                "detection_accuracy": 1.0  # not calculated
            })
        )

    def disconnect(self) -> tss_structs.Status:
        """Write disconnection from the sensor here."""
        print("=============== disconnected from the sim vision sensor!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)