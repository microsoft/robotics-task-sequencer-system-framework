# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import time
import json
import os
import fastapi
from fastapi import WebSocket, Request, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sys
import signal
import enum
import dotenv
import uvicorn

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.interface.config_loader as config_loader

import tasqsym_encoder.aimodel.aimodel_base as aimodel_base


"""
credentials file content example:

# below required if --aoai option
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_KEY=
AZURE_OPENAI_DEPLOYMENT_NAME_CHATGPT=

# below required if --aoai flag disabled
OPENAI_API_KEY=
"""

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--credentials", help="credentials file")
parser.add_argument("--aimodel", help="aimodel python module as MODULE_PATH.CLASS")
parser.add_argument("--config", help="tasqsym config file also including data such as description about the environment")
parser.add_argument("--outdir", default="", help="directory to store intermediate outputs")
parser.add_argument("--aoai", action="store_true", help="add if using Azure OpenAI")
parser.add_argument("--connection", help="connection style to tasqsym (mqtt or empty) will not connect to tasqsym core if empty", default="")
parser.add_argument("--aioutput", action="store_true", help="add if showing aimodel output plans instead of the behavior tree")
parser.add_argument("--initcore", action="store_true", help="add if sending configurations loaded on the server to the core")

pargs, unknown = parser.parse_known_args()

# flags
encode_only_test = (pargs.connection == "")
use_azureOpenAI = pargs.aoai
show_output_from_ai = pargs.aioutput
send_configuration_to_core = pargs.initcore

# settings
if pargs.connection == "mqtt":
    """
    below required in credentials file content:
    MQTT_HOST_NAME=
    MQTT_USERNAME=
    MQTT_CLIENT_ID=
    MQTT_CERT_FILE=
    MQTT_KEY_FILE=
    MQTT_TCP_PORT=
    """
    import tasqsym_encoder.network.mqtt_bridge as mqtt_bridge
    network_client = mqtt_bridge.MQTTBridgeOnServer(pargs.credentials)
elif pargs.connection == "file":
    import tasqsym_encoder.network.file_access as file_access
    network_client = file_access.LocalFileBridge(pargs.credentials)
elif pargs.connection != "":
    raise Exception("unknown connection style %s" % pargs.connection)

azure_credentials = dotenv.dotenv_values(pargs.credentials)
output_dir = pargs.outdir

# load AI model
aimodel_modstr = pargs.aimodel
import importlib
aimodel_path = '.'.join(aimodel_modstr.split('.')[:-1])
aimodel_class_name = aimodel_modstr.split('.')[-1]
aimodel_module = importlib.import_module(aimodel_path)


# load data and settings
cfl = config_loader.ConfigLoader()

def loadConfigs(configs: dict):
    status = cfl.expandRobotStructureConfig(configs)
    if status.status != tss_constants.StatusFlags.SUCCESS:
        print("setup warning: could not expand robot structure config")

    status = cfl.expandSkillLibraryConfig(configs)
    if status.status != tss_constants.StatusFlags.SUCCESS:
        print("setup warning: could not expand skill library config")

    status = cfl.loadDataEngine(configs)
    if status.status != tss_constants.StatusFlags.SUCCESS:
        raise Exception("setup failed: could not access data engine")
    status = cfl.saveUpdateDataEngineSettings()  # data engine may expand/upload content from local files using this method
    if status.status != tss_constants.StatusFlags.SUCCESS:
        raise Exception("setup failed: could not update data engine")

    configs["library"] = cfl.skill_library_config
    configs["robot_structure"] = cfl.robot_structure_config
    configs["engines"] = cfl.envg_config
    return configs

with open(pargs.config) as f:
    tss_configs = loadConfigs(json.load(f))
if cfl.data_engine is None: raise Exception("setup failed: could not load data")


"""
Main code begins here.
"""

templates = Jinja2Templates(directory="../robotics-task-sequencer-system-framework/src/tasqsym_encoder/htmls")

app = fastapi.FastAPI()


class ServerState(enum.Enum):
    ON_TASK_REQUEST = "wait task request"
    ON_USER_CONFIRMATION = "process user confirmation"
    ON_TASK_SEND = "process task send"

class ServerMemory:
    def __init__(self,
                 current_state: ServerState=ServerState.ON_TASK_REQUEST,
                 task_plan: dict={},
                 compiled_plan: dict={}):
        self.current_state = current_state
        self.task_plan = task_plan
        self.compiled_plan = compiled_plan

class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}
        self.models: dict[str, aimodel_base.AIModel] = {}
        self.states: dict[str, ServerMemory] = {}

    async def connect(self, websocket: WebSocket, session_id):
        if session_id in self.connections:
            await websocket.send_text("Error: Session ID already in use.")
            await websocket.close()
            return

        await websocket.accept()
        self.connections[session_id] = websocket

        self.models[session_id] = getattr(aimodel_module, aimodel_class_name)(
            azure_credentials,
            use_azure=use_azureOpenAI,
            logdir=output_dir)
        self.states[session_id] = ServerMemory()

    def resetstates(self, session_id: str):
        self.states[session_id] = ServerMemory()

    def disconnect(self, session_id: str):
        if session_id not in self.connections: return
        self.connections.pop(session_id)
        del self.models[session_id]

    async def send_personal_message(self, message: str, session_id: str):
        if session_id not in self.connections: return
        await self.connections[session_id].send_text(message)

    async def broadcast(self, message: str):
        for _, connection in self.connections.items():
            await connection.send_text(message)

manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('ui.html', {"request": request})

async def send_configs(configs: dict):
    if encode_only_test or (not send_configuration_to_core): return

    timestamp_setup = network_client.send_command("setup", {"content": configs})
    print("timestamp--- ", timestamp_setup)
    await network_client.wait_feedback(timestamp_setup)
    print(network_client.feedback)

async def send_task(bt: dict):
    if encode_only_test: return

    content = {
        "content": bt,
        "node_pointer": []
    }
    timestamp_run = network_client.send_command("run", content)
    print("timestamp--- ", timestamp_run)
    # await network_client.wait_feedback(timestamp_run)  # comment-in for synchronous call
    print(network_client.feedback)

async def send_cancel():
    if encode_only_test: return

    timestamp_abort = network_client.send_command("abort", {"emergency": False})
    print("timestamp--- ", timestamp_abort)
    await network_client.wait_feedback(timestamp_abort)  # depending on timing may fail
    print(network_client.feedback)

    return f"Cancelled instructions. Please send a new instruction."

async def send_estop():
    if encode_only_test: return

    timestamp_abort = network_client.send_command("abort", {"emergency": True})
    print("timestamp--- ", timestamp_abort)
    await network_client.wait_feedback(timestamp_abort)
    print(network_client.feedback)

    return f"Sent emergency stop. Please send recovery instructions."

async def notify(message, session_id: str):
    await manager.send_personal_message(message, session_id)

async def compile(task_plan: dict, session_id: str):
    """
    The task plan output (actions from GPT) is not a direct mapping to the skills in core.
    For example, move forward X[m] and move to location Z are both a 'navigation' skill in core,
    but, GPT will output them as two separate actions: WalkForward() and Navigate().
    """
    await notify(f"CONSOLE_LOG: compiling task model", session_id)
    action_sequence = task_plan["task_sequence"]  # currently does not support branching sequence

    if "environment_after" in task_plan: expected_outcome_states = task_plan["environment_after"]
    else: expected_outcome_states = None

    compiled_plan = manager.models[session_id].encode(action_sequence, expected_outcome_states, cfl.data_engine)

    operation_name = (
        time.strftime(
            "%Y%m%d_%H%M%S",
            time.localtime()) +
        "_operation")

    if output_dir != "":
        # save task plan output
        fp = os.path.join(output_dir, operation_name + '_task_plan.json')
        print(f'saving task model to {fp}')
        with open(fp, 'w') as f: json.dump(compiled_plan, f, indent=4)
        # save intermediate format locally
        fp = os.path.join(output_dir, operation_name + '_raw_task_plan.json')
        print(f'saving raw task plan to {fp}')
        with open(fp, 'w') as f: json.dump(task_plan, f, indent=4)

    return compiled_plan


async def interface(user_input: str, session_id: str):
    print(user_input)
    while True:

        if user_input == 'cancel': return await send_cancel()  # cancel instructions

        if user_input == 'e-stop': return await send_estop()

        if manager.states[session_id].current_state == ServerState.ON_TASK_REQUEST:
            await notify(f"CONSOLE_LOG: handle task request", session_id)

            # send configs to the robot the first time an instruction is given (first time is determined by whether the world is loaded already or not)
            if len(manager.models[session_id].world) == 0: await send_configs(tss_configs)

            # load data set in the data engine (always update as state might have been updated after previous instruction)
            manager.models[session_id].compile_world(cfl.data_engine)

            # run GPT
            text_response = manager.models[session_id].generate(user_input, manager.models[session_id].world)
            print("result from instruction", text_response)
            format_success, json_dict = manager.models[session_id].format_response(text_response)

            # return to UI for user confirmation
            if format_success:
                """Compile process. Always enters this process upon user instruction."""
                manager.states[session_id].task_plan = json_dict
                # set the flag to wait for the user confirmation
                manager.states[session_id].compiled_plan = await compile(json_dict, session_id)
                manager.states[session_id].current_state = ServerState.ON_USER_CONFIRMATION
                if show_output_from_ai: return f"Please enter 'Y' if the following task is okay:", json.dumps(manager.states[session_id].task_plan, indent=4)
                else: return f"Please enter 'Y' if the following task is okay:", json.dumps(manager.states[session_id].compiled_plan, indent=4)
            else:
                return text_response

        elif manager.states[session_id].current_state == ServerState.ON_USER_CONFIRMATION:
            await notify(f"CONSOLE_LOG: handle user confirmation", session_id)
            if user_input == 'yes' or user_input == 'y' or user_input == 'Yes' or user_input == 'Y':
                manager.states[session_id].current_state = ServerState.ON_TASK_SEND
                manager.models[session_id].reset_history()
            else:
                await notify(f"CONSOLE_LOG: got correction from user", session_id)
                text_response = manager.models[session_id].generate(user_input, manager.models[session_id].world, is_user_feedback=True)
                print("result from feedback:", text_response)
                format_success, json_dict = manager.models[session_id].format_response(text_response)

                if format_success:
                    """Correction process. USUALLY DOES NOT ENTER THIS PROCESS UNLESS A USER CORRECTS THE INSTURCTION INSTEAD OF TYPING 'Y'."""
                    manager.states[session_id].task_plan = json_dict
                    manager.states[session_id].compiled_plan = await compile(json_dict, session_id)
                    if show_output_from_ai: return f"Please enter 'Y' if the following task is okay:", json.dumps(manager.states[session_id].task_plan, indent=4)
                    else: return f"Please enter 'Y' if the following task is okay:", json.dumps(manager.states[session_id].compiled_plan, indent=4)
                else:
                    manager.states[session_id].current_state = ServerState.ON_TASK_REQUEST
                    return text_response

        # depending on branch, will enter below right after ON_USER_CONFIRMATION
        if manager.states[session_id].current_state == ServerState.ON_TASK_SEND:
            await notify(f"CONSOLE_LOG: send task model", session_id)

            await send_task(manager.states[session_id].compiled_plan)
            print("send task plan done!")

            manager.states[session_id].current_state = ServerState.ON_TASK_REQUEST

            return f"Finished sending instructions. Please enter further instructions if any; or cancel the current instruction using the button in the buttom left."

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            print('waiting input...')
            data = await websocket.receive_text()
            print(data)
            if not data.startswith('['):  # "[command]" is an internal command
                await manager.send_personal_message(f"User: {data}", session_id)
            agent_return = await interface(data, session_id)
            if agent_return is not None:
                if isinstance(agent_return, tuple): await notify(f"Robot: " + agent_return[0] + '\n' + agent_return[1], session_id)
                else: await notify(f"Robot: " + agent_return, session_id)
            else: pass
    except WebSocketDisconnect:
        manager.disconnect(session_id)


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    import copy
    session_ids = copy.deepcopy(list(manager.connections.keys()))
    for session_id in session_ids:
        manager.disconnect(session_id)
    if not encode_only_test: network_client.disconnect()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

uvicorn.run(app, host="localhost", port=9100)