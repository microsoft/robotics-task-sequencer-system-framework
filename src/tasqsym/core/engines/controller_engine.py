# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import importlib
import asyncio

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.world_format as world_format

from tasqsym.core.classes.engine_base import ControllerEngineBase


class ControllerEngine(ControllerEngineBase):

    def __init__(self, class_id: str):

        super().__init__(class_id)

    async def init(self, general_config: dict, robot_structure_config: dict, engine_config: dict) -> tss_structs.Status:

        if "models" not in robot_structure_config:
            msg = "controller engine error: 'models' field missing in robot structure config"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        models = robot_structure_config["models"]

        def _loadStructure(config: dict, parent_id: str) -> tss_structs.Status:

            if len(config.keys()) != 1:
                msg = "controller engine error: invalid structure!"
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            
            if "sensor" in config:
                sensor = config["sensor"]
                if "unique_id" not in sensor:
                    msg = "controller engine error: found a sensor missing a 'unique_id'"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                if "type" not in sensor:
                    msg = "controller engine error: found a sensor missing a 'type'"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                if "parent_link" not in sensor:
                    msg = "controller engine error: found a sensor missing a 'parent_link'"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                if "sensor_frame" not in sensor:
                    msg = "controller engine error: found a sensor missing a 'sensor_frame'"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                if "physical_sensor" not in sensor:
                    msg = "controller engine error: found a sensor missing 'physical_sensor'"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                if "parent_id" == "":
                    msg = "controller engine error: parent id of a sensor cannot be empty"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                sensor_type = tss_constants.SensorRole[sensor["type"].upper()]
                physical_sensor_str = sensor["physical_sensor"]
                path_ = '.'.join(physical_sensor_str.split('.')[:-1])
                class_ = physical_sensor_str.split('.')[-1]
                module_ = importlib.import_module(path_)
                sensor_info = {
                    "unique_id": sensor["unique_id"],
                    "type": sensor_type,
                    "parent_id": parent_id, "parent_link": sensor["parent_link"],
                    "sensor_frame": sensor["sensor_frame"]
                }
                self.sensors[sensor["unique_id"]] = getattr(module_, class_)(sensor_info)
                if "configs" in sensor: sensor_configs = sensor["configs"]
                else:
                    print("controller engine warning: no 'configs' found for physical sensor")
                    sensor_configs = {}
                status = self.sensors[sensor["unique_id"]].connect(sensor_info, sensor_configs)
                if status.status != tss_constants.StatusFlags.SUCCESS: return status
                # sensor cannot have childs
                return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

            robot = config[list(config.keys())[0]]
            if "unique_id" not in robot:
                msg = "controller engine error: found a %s missing a 'unique_id'" % list(config.keys())[0]
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            if "physical_robot" not in robot:
                msg = "controller engine error: found a %s missing 'physical_robot'" % list(config.keys())[0]
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            if "parent_link" not in robot:
                msg = "controller engine error: found a %s missing 'parent_link'" % list(config.keys())[0]
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            robot_info = {
                "unique_id": robot["unique_id"],
                "parent_id": parent_id,
                "parent_link": robot["parent_link"]
            }
            if ("configs" in robot) and ("physical_robot" in robot["configs"]): robot_configs = robot["configs"]["physical_robot"]
            else:
                print("controller engine warning: no 'configs' found for physical robot")
                robot_configs = {}

            physical_robot_str = robot["physical_robot"]
            path_ = '.'.join(physical_robot_str.split('.')[:-1])
            class_ = physical_robot_str.split('.')[-1]
            module_ = importlib.import_module(path_)
            self.robots[robot["unique_id"]] = getattr(module_, class_)(robot_info)
            status = self.robots[robot["unique_id"]].connect(robot_info, robot_configs)
            if status.status != tss_constants.StatusFlags.SUCCESS: return status

            if ("childs" in robot) and (len(robot["childs"]) > 0):
                for child_robot in robot["childs"]:
                    status = _loadStructure(child_robot, robot["unique_id"])
                    if status.status != tss_constants.StatusFlags.SUCCESS: return status

            return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

        for rm in models:
            status = _loadStructure(rm, "")
            if status.status != tss_constants.StatusFlags.SUCCESS:
                self.cleanup()
                return status

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)


    async def updateActualRobotStates(self) -> tss_structs.Status:

        updates: list[asyncio.Coroutine] = []

        unique_ids = []
        for unique_id, robot in self.robots.items():
            updates.append(robot.getLatestState())
            unique_ids.append(unique_id)

        update_task = asyncio.gather(*updates, return_exceptions=False)
        robot_states: list[tss_structs.RobotState] = await update_task

        self.latest_robot_state = tss_structs.CombinedRobotState({}, tss_structs.Status(tss_constants.StatusFlags.SUCCESS))
        for k, rs in enumerate(robot_states):
            self.latest_robot_state.robot_states[unique_ids[k]] = rs
            if rs.status.status != tss_constants.StatusFlags.SUCCESS:
                print(unique_ids[k], rs.status.message)  # print error message
                self.latest_robot_state.status = tss_structs.Status(tss_constants.StatusFlags.FAILED)

        return self.latest_robot_state.status

    async def update(self, world_state: world_format.WorldStruct) -> world_format.WorldStruct:

        desired_actions = world_state.combined_robot_state.desired_actions.actions
        latest_states = world_state.combined_robot_state.actual_states.robot_states

        controls: list[asyncio.Coroutine] = []

        """Generate list of control methods to execute."""
        for unique_id, input_actions in desired_actions.items():

            if len(input_actions) == 0: continue

            # element 0 should be the main goal to solve, whereas other elements can be used as additional information
            solveby_type = input_actions[0].solveby_type

            if solveby_type == tss_constants.SolveByType.FORWARD_KINEMATICS:
                controls.append(self.robots[unique_id].sendJointAngles(input_actions, latest_states[unique_id]))

            elif solveby_type == tss_constants.SolveByType.NAVIGATION3D:
                # may need to rewrite below input as a list if a MobileManipulator also contains an FK goal
                controls.append(self.robots[unique_id].sendBasePose(input_actions, latest_states[unique_id]))

            elif solveby_type == tss_constants.SolveByType.INVERSE_KINEMATICS:
                controls.append(self.robots[unique_id].sendTargetMotion(input_actions, latest_states[unique_id]))

            elif solveby_type == tss_constants.SolveByType.POINT_TO_IK:
                controls.append(self.robots[unique_id].sendPointToMotion(input_actions, latest_states[unique_id]))

            elif solveby_type == tss_constants.SolveByType.CONTROL_COMMAND:
                controls.append(self.robots[unique_id].sendControlCommand(input_actions, latest_states[unique_id]))

            elif solveby_type == tss_constants.SolveByType.INIT_ROBOT:
                controls.append(self.robots[unique_id].init(input_actions, latest_states[unique_id]))

            else: raise Exception("ControllerEngine encountered unknown type!")

        """Execute control methods."""
        print('controller engine info: sending controls ...')
        self.control_task = asyncio.gather(*controls, return_exceptions=False)
        try:
            success_flags: list[tss_structs.Status] = await self.control_task
            self.control_task = None
            status = tss_structs.Status(tss_constants.StatusFlags.SUCCESS)
            for s in success_flags:
                if s.status != tss_constants.StatusFlags.SUCCESS:
                    status.message += '; ' + s.message
        except asyncio.CancelledError:
            print('controller engine info: cancelling controls ...')
            self.control_task = None

            # emergency stop
            if self.emergency_stop_request:
                self.emergency_stop_request = False
                # stop handled externally, requires quick finish, return here
                return world_format.WorldStruct(
                    world_format.CombinedRobotStruct(
                        self.latest_robot_state, world_state.combined_robot_state.desired_actions, tss_structs.Status(tss_constants.StatusFlags.ABORTED)),
                    world_state.component_states)

            # aborts should be setup here to avoid 'coroutine never awaited' warnings
            aborts: list[asyncio.Coroutine] = []
            # cancel task
            for unique_id, input_actions in desired_actions.items():
                input_action = input_actions[0]
                if input_action.solveby_type == tss_constants.SolveByType.FORWARD_KINEMATICS:
                    aborts.append(self.robots[unique_id].abortJointAngles())
                elif input_action.solveby_type == tss_constants.SolveByType.NAVIGATION3D:
                    aborts.append(self.robots[unique_id].abortBasePose())
                elif input_action.solveby_type == tss_constants.SolveByType.INVERSE_KINEMATICS:
                    aborts.append(self.robots[unique_id].abortTargetMotion())
                elif input_action.solveby_type == tss_constants.SolveByType.POINT_TO_IK:
                    aborts.append(self.robots[unique_id].abortPointToMotion())
                elif input_action.solveby_type == tss_constants.SolveByType.CONTROL_COMMAND:
                    aborts.append(self.robots[unique_id].abortControlCommand())
            await asyncio.gather(*aborts, return_exceptions=False)
            status = tss_structs.Status(tss_constants.StatusFlags.ABORTED)
        print('controller engine info: finished controls')

        """Update states for the later pipeline."""
        update_task = asyncio.create_task(self.updateActualRobotStates())
        await update_task

        return world_format.WorldStruct(
            world_format.CombinedRobotStruct(
                self.latest_robot_state, world_state.combined_robot_state.desired_actions, status),
            world_state.component_states)


    async def close(self) -> tss_structs.Status:

        self.cleanup()

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)