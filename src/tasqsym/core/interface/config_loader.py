# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import importlib
import os
import json
import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.classes.engine_base as engine_base


class ConfigLoader:

    general_config: dict = None
    envg_config: dict = None
    robot_structure_config: dict = None
    skill_library_config: dict = None

    data_engine: engine_base.DataEngineBase = None

    def __init__(self):
        pass

    def expandRobotStructureConfig(self, configs: dict) -> tss_structs.Status:
        """
        Directly use this function if sending the robot structure file content between machines.
        If there are no machine-machine communications, should just call loadConfigs()
        """

        if "robot_structure" not in configs:
            msg = "config loader error: field 'robot_structure' missing in config!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        
        filename = configs["robot_structure"]

        if filename[0] == '$':  # read from environment variable
            filename = os.environ.get(filename[1:])
        
        # currently does not support loading config from storage

        with open(filename) as f:
            self.robot_structure_config = json.load(f)["robot_structure"]

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def expandSkillLibraryConfig(self, configs: dict) -> tss_structs.Status:
        """
        Directly use this function if sending the skill library file content between machines.
        If there are no machine-machine communications, should just call loadConfigs()
        """

        if "library" not in configs:
            msg = "config load error: field 'library' missing in config!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        libary_list_module_name = configs["library"]

        library_module = importlib.import_module(libary_list_module_name)
        self.skill_library_config = library_module.library

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def loadDataEngine(self, configs: dict) -> tss_structs.Status:
        """
        For encoder only.
        """

        if "engines" not in configs:
            msg = "config load error: field 'engines' missing in config!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        self.envg_config = configs["engines"]

        if "data" not in self.envg_config:
            msg = "config load error: field 'engines.data' missing in config!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        data_engine_config = self.envg_config["data"]
        if "engine" not in data_engine_config:
            msg = "config load error: field 'engines.data.engine' missing in config!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        engine_module = ".".join(data_engine_config["engine"].split(".")[0:-1])
        engine_class = data_engine_config["engine"].split(".")[-1]

        if "class_id" not in data_engine_config:
            msg = "config load error: field 'engines.data.class_id' missing in config!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        class_id = data_engine_config["class_id"]

        engine_module = importlib.import_module(engine_module)
        self.data_engine: engine_base.DataEngineBase = getattr(engine_module, engine_class)(class_id)
        self.data_engine.load(None, self.robot_structure_config, data_engine_config.get("config", {}))

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def saveUpdateDataEngineSettings(self) -> tss_structs.Status:
        """
        For encoder only.
        """

        if self.data_engine is None:
            msg = "config load error: tried to call write() of a null data engine!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        status, update_settings = self.data_engine.save()
        if status != tss_constants.StatusFlags.SUCCESS: return status

        self.envg_config["data"] = update_settings
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def loadConfigs(self, configs: dict) -> tss_structs.Status:
        """
        The 'library' field can be a path to a module or direct content.
        The 'robot_structure' field can be a path to a file or direct content.
        The direct content method is usually used when configs are sent between machines.
        Note that only the configs of the robot structure can be sent between machines.
        The robot adapter modules must exist on the machine where the core (decoder) is running.

        The 'engine' field must have direct content.
        Note that only the configs for the engine modules can be sent between machines.
        The module itself must exist on the machine where the core (decoder) is running.
        """

        if "general" not in configs:
            msg = "config load error: must have the 'general' field"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        self.general_config = configs["general"]

        if ("library" in configs) and (type(configs["library"]) != str):
            print("config load info: assuming library content is directly specified as field value is not a string")
            self.skill_library_config = configs["library"]
        elif self.skill_library_config is None:
            print("config load info: skill library not loaded yet, loading")
            status = self.expandSkillLibraryConfig(configs)
            if status.status != tss_constants.StatusFlags.SUCCESS: return status

        if ("robot_structure" in configs) and (type(configs["robot_structure"]) != str):
            print("config load info: assuming robot structure content is directly specified as field value is not a string")
            self.robot_structure_config = configs["robot_structure"]
        elif self.robot_structure_config is None:
            print("config load info: robot structure is not loaded yet, loading")
            status = self.expandRobotStructureConfig(configs)
            if status.status != tss_constants.StatusFlags.SUCCESS: return status

        if "engines" not in configs:
            msg = "config loader error: must have the 'engines' field"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        self.envg_config = configs["engines"]

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)