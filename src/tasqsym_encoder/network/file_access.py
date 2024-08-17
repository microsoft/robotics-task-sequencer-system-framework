# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import os
import json
import time
import dotenv


class LocalFileBridge:

    feedback=None

    def __init__(self, env_filename: str):
        env_file_dict = dotenv.dotenv_values(env_filename)
        setting_names: list[str] = ['TASQSYM_ENCODER_OUTPUT_FILE']
        envfile_values = {k: v for k, v in env_file_dict.items() if k in setting_names}
        envvar_values = {k: v for k, v in os.environ.items() if k in setting_names}
        default_values = {
            'TASQSYM_ENCODER_OUTPUT_FILE': 'tasqsym_encoder_output.json'
        }
        final_values = {**default_values, **envvar_values, **envfile_values}
        self.outfile = final_values['TASQSYM_ENCODER_OUTPUT_FILE']

    def send_command(self, cmd, rest) -> int:
        timestamp = int(time.strftime("%Y%m%d%H%M%S", time.localtime()))
        if cmd == "run":
            with open(self.outfile, 'w', encoding='utf-8') as f:
                json.dump(rest["content"], f, ensure_ascii=False, indent=4)
            print("wrote to %s" % self.outfile)
        return timestamp

    async def wait_feedback(self, timestamp) -> bool: self.feedback = timestamp
            
    def disconnect(self): pass