# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import os
import json

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
from tasqsym.core.classes.engine_base import DataEngineBase


class DataEngine(DataEngineBase):
    """Store/open data in local file storage."""

    stored_data: dict[str, dict] = {}

    def __init__(self, class_id: str):
        super().__init__(class_id)

    async def init(self, general_config: dict, robot_structure_config: dict, engine_config: dict) -> tss_structs.Status:
        return self.load(general_config, robot_structure_config, engine_config)

    def load(self, general_config: dict, robot_structure_config: dict, engine_config: dict) -> tss_structs.Status:
        if type(engine_config) == str:
            filename = engine_config
            if filename[0] == '$': filename = os.environ.get(filename[1:]) # read from environment variable
            with open(filename) as f: data = json.load(f) # load file content
        else: data = engine_config

        for data_name, data_content in data.items(): self.stored_data[data_name] = data_content
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getData(self, cmd: str) -> tuple[tss_structs.Status, dict]:
        if cmd in self.stored_data:
            return (tss_structs.Status(tss_constants.StatusFlags.SUCCESS), self.stored_data[cmd])
        else:
            msg = "DataEngine: unknown command %s" % cmd
            return (tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg), {})

    def updateData(self, cmd: str, data: dict) -> tss_structs.Status:
        if cmd not in self.stored_data: print("DataEngine warning: storing new data %s" % cmd)
        self.stored_data[cmd] = data
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def save(self) -> tuple[tss_structs.Status, dict]:
        if "export_path" in self.stored_data:
            with open(self.stored_data["export_path"], 'w', encoding='utf-8') as f:
                json.dump(self.stored_data, f, ensure_ascii=False, indent=4)
        else:
            print("DataEngine warning: to save to file, please specify an 'export_path' in the data file.")
        return (tss_structs.Status(tss_constants.StatusFlags.SUCCESS), self.stored_data)

    async def close(self) -> tss_structs.Status:
        # nothing to do
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)