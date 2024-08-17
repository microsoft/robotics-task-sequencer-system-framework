# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import copy
import importlib

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.world_format as world_format

from tasqsym.core.classes.engine_base import KinematicsEngineBase


class KinematicsEngine(KinematicsEngineBase):

    def __init__(self, class_id: str):

        super().__init__(class_id)

    async def init(self, general_config: dict, robot_structure_config: dict, engine_config: dict) -> tss_structs.Status:

        if "combiner" not in robot_structure_config:
            msg = "kinematics engine error: 'combiner' field missing in robot structure config"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        robot_combiner_path = '.'.join(robot_structure_config["combiner"].split('.')[:-1])
        robot_combiner_class = robot_structure_config["combiner"].split('.')[-1]
        robot_combiner_module = importlib.import_module(robot_combiner_path)
        self.robot_combiner = getattr(robot_combiner_module, robot_combiner_class)()

        if "models" not in robot_structure_config:
            msg = "kinematics engine error: 'models' field missing in robot structure config"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        
        models = robot_structure_config["models"]

        def _loadStructure(config: dict, parent_id: str) -> tss_structs.Status:

            if len(config.keys()) != 1:
                msg = "kinematics engine error: invalid structure!"
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

            if "sensor" in config:
                sensor = config["sensor"]
                if "unique_id" not in sensor:
                    msg = "kinematics engine error: found a sensor missing a 'unique_id'"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                if "type" not in sensor:
                    msg = "kinematics engine error: found a sensor missing a 'type'"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                if "parent_link" not in sensor:
                    msg = "kinematics engine error: found a sensor missing a 'parent_link'"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                if "sensor_frame" not in sensor:
                    msg = "controller engine error: found a sensor missing a 'sensor_frame'"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                if "parent_id" == "":
                    msg = "kinematics engine error: parent id of a sensor cannot be empty"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                sensor_type = tss_constants.SensorRole[sensor["type"].upper()]
                if sensor_type not in self.sensor_ids: self.sensor_ids[sensor_type] = sensor["unique_id"]
                self.sensors[sensor["unique_id"]] = {
                    "type": sensor_type,
                    "parent_id": parent_id, "parent_link": sensor["parent_link"],
                    "sensor_frame": sensor["sensor_frame"]
                }
                # sensor cannot have childs
                return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

            model_info = {}

            if "mobile_base" in config:
                robot = config["mobile_base"]
                if self.base_id != "":
                    msg = "kinematics engine error: found more than one mobile robot, this is not allowed"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                self.base_id = robot["unique_id"]
            elif "mobile_manipulator" in config:
                robot = config["mobile_manipulator"]
                if self.base_id != "":
                    msg = "kinematics engine error: found more than one mobile robot, this is not allowed"
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                self.base_id = robot["unique_id"]
            elif "manipulator" in config:
                robot = config["manipulator"]
                if self.base_id == "":
                    print("kinematics engine warning: detected manipulator %s as base" % robot["unique_id"])
                    self.base_id = robot["unique_id"]
            elif "end_effector" in config:
                robot = config["end_effector"]
                if self.end_effector_id == "": self.end_effector_id = robot["unique_id"]
            elif "tool" in config:
                robot = config["tool"]
                if self.end_effector_id == "": self.end_effector_id = robot["unique_id"]

            if "unique_id" not in robot:
                msg = "kinematics engine error: found a %s missing a 'unique_id'" % list(config.keys())[0]
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            if "model_robot" not in robot:
                msg = "kinematics engine error: found a %s missing 'model_robot'" % list(config.keys())[0]
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            if "parent_link" not in robot:
                msg = "kinematics engine error: found a %s missing 'parent_link'" % list(config.keys())[0]
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            if "configs" not in robot:
                msg = "kinematics engine error: found a %s missing 'configs'" % list(config.keys())[0]
                return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
            if ("configs" in robot) and ("model_robot" in robot["configs"]): model_configs = robot["configs"]["model_robot"]
            else:
                print("kinematics engine warning: no 'configs' found for model robot")
                model_configs = {}

            model_robot_str = robot["model_robot"]
            path_ = '.'.join(model_robot_str.split('.')[:-1])
            class_ = model_robot_str.split('.')[-1]
            module_ = importlib.import_module(path_)
            model_info["unique_id"] = robot["unique_id"]
            model_info["parent_id"] = parent_id
            model_info["parent_link"] = robot["parent_link"]
            self.robot_models[robot["unique_id"]] = getattr(module_, class_)(model_info)
            status = self.robot_models[robot["unique_id"]].create(model_info, model_configs)
            if status.status != tss_constants.StatusFlags.SUCCESS: return status

            if ("end_effector" in config) or ("tool" in config):
                if "parent_id" == "":
                    msg = "kinematics engine error: parent id of a %s cannot be empty" % list(config.keys())[0]
                    return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

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


    async def update(self, world_state: world_format.WorldStruct) -> world_format.WorldStruct:

        input_actions = world_state.combined_robot_state.desired_actions
        latest_state = world_state.combined_robot_state.actual_states

        desired_actions = tss_structs.CombinedRobotAction(input_actions.task, {})

        # temporary variables to log commanded action types
        latest_types: dict[str, list[tss_constants.SolveByType]] = {}  # unique_id, types
        latest_commands: dict[str, dict[str, list[tss_structs.RobotAction]]] = {}  # unique_id, {type, action}

        """Warn unexpected action inputs and also log actions."""
        for unique_id, robot_actions in input_actions.actions.items():

            """Add unique_id to temporary logging variables."""
            if unique_id not in latest_types:
                latest_types[unique_id] = []
                latest_commands[unique_id] = {}

            """Add unique_id to desired actions (note, controls will NOT be sent if list remains empty)"""
            if unique_id not in desired_actions.actions: desired_actions.actions[unique_id] = []

            """Main checking/logging procedure."""
            for input_action in robot_actions:

                if input_action.solveby_type == tss_constants.SolveByType.NULL_ACTION: continue

                if input_action.solveby_type == tss_constants.SolveByType.FORWARD_KINEMATICS:

                    if tss_constants.SolveByType.FORWARD_KINEMATICS in latest_types[unique_id]:
                        print("KinematicsEngine warning: detected multiple FK goals for one robot! this could lead to an unexpected behavior!")
                    desired_actions.actions[unique_id].append(input_action)

                elif input_action.solveby_type == tss_constants.SolveByType.INVERSE_KINEMATICS:

                    desired_actions.actions[unique_id].append(input_action)

                elif input_action.solveby_type == tss_constants.SolveByType.NAVIGATION3D:

                    if tss_constants.SolveByType.NAVIGATION3D in latest_types[unique_id]:
                        print("KinematicsEngine warning: detected multiple navigation goals for one robot! this could lead to an unexpected behavior!")
                    desired_actions.actions[unique_id].append(input_action)

                elif input_action.solveby_type == tss_constants.SolveByType.POINT_TO_IK:

                    desired_actions.actions[unique_id].append(input_action)

                elif input_action.solveby_type == tss_constants.SolveByType.CONTROL_COMMAND:

                    desired_actions.actions[unique_id].append(input_action)

                elif input_action.solveby_type == tss_constants.SolveByType.INIT_ROBOT:

                    if tss_constants.SolveByType.INIT_ROBOT in latest_types[unique_id]:
                        print("KinematicsEngine warning: detected multiple init goals for one robot! this could lead to an unexpected behavior!")
                    desired_actions.actions[unique_id].append(input_action)

                else: raise Exception("KinematicsEngine encountered unknown type!")

                """Log latest actions types."""
                latest_types[unique_id].append(input_action.solveby_type)

                """"Log latest actions."""
                if input_action.solveby_type not in latest_commands[unique_id]:
                    latest_commands[unique_id][input_action.solveby_type] = [copy.deepcopy(input_action)]
                else: latest_commands[unique_id][input_action.solveby_type].append(copy.deepcopy(input_action))

        """
        Robots with no actions will set the latest action as null.
        Note that, this not only indicates that the robot did not take any action,
        but also the possibility that a parent robot may have changed the robot's state.
        Desired actions are volatile and information about a past action is only valid when the actions are continuous.
        """
        for unique_id, _ in self.robot_models.items():
            self.robot_models[unique_id].most_latest_action_types = [tss_constants.SolveByType.NULL_ACTION]
        for unique_id, types in latest_types.items():
            self.robot_models[unique_id].most_latest_action_types = copy.deepcopy(types)
            for action_type in types:
                self.robot_models[unique_id].desired_actions_log[action_type] = latest_commands[unique_id][action_type]

        return world_format.WorldStruct(
            world_format.CombinedRobotStruct(latest_state, desired_actions, tss_structs.Status(tss_constants.StatusFlags.SUCCESS)),
            world_state.component_states)


    async def close(self) -> tss_structs.Status:

        self.cleanup()

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)