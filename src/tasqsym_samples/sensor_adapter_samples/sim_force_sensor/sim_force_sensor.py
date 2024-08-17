# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
from tasqsym.core.classes.physical_sensor import PhysicalSensor


class SimForceSensor(PhysicalSensor):

    def __init__(self, model_info: dict):
        super().__init__(model_info)

    def connect(self, model_info: dict, configs: dict) -> tss_structs.Status:
        """
        Write the connections to the real hardware here.
        In this example, there will be no real hardware connections as a simulated sensor.
        """
        print("=============== connected to the sim force sensor!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getPhysicsState(self, cmd: str, rest: tss_structs.Data) -> tuple[tss_structs.Status, tss_structs.Data]:
        """
        Write logic to obtain physical contact states.
        The default skill library requires obtaining the following contact state: SurfaceContact
        In this example, a dummy contact information will be generated.
        """

        if cmd == "Reset":
            """Reset the sensor (called to zero value drifts etc.)."""
            self.contact_frame = 0
            return (tss_structs.Status(tss_constants.StatusFlags.SUCCESS), None)
        elif cmd == "SurfaceContact":
            """The place skill requires detecting whether the robot (or object in hand) has contacted a surface."""
            if self.contact_frame < 7:
                self.contact_frame += 1
                print("=============== sim force sensor checking for surface contact ... not yet at contact")
                return (tss_structs.Status(tss_constants.StatusFlags.SUCCESS), tss_structs.Data({"contact_environment": False}))
            else:
                print("=============== sim force sensor detected a surface contact!")
                return (tss_structs.Status(tss_constants.StatusFlags.SUCCESS), tss_structs.Data({"contact_environment": True}))
        else:
            msg = "sim force sensor: no such command %s" % cmd
            return (tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg), None)

    def disconnect(self) -> tss_structs.Status:
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)