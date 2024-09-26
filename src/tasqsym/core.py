# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import copy
import json
import asyncio

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.interface.config_loader as config_loader
import tasqsym.core.interface.blackboard as blackboard
import tasqsym.core.interface.envg_interface as envg_interface
import tasqsym.core.interface.skill_interface as skill_interface
import tasqsym.core.bt_decoder as bt_decoder


async def distribute_mode(default_tssconfig: str, network_client):
    global run_tree

    await network_client.connect()  # if connection is async

    envg = envg_interface.EngineInterface()
    rsi = skill_interface.SkillInterface()
    board = blackboard.Blackboard()
    tsd = bt_decoder.TaskSequenceDecoder(network_client)

    async def return_status(msgid, msgtype: str, status: tss_structs.Status):
        print(status.message)
        if msgid == "": return  # called from a non-remote execution
        data = {
            "id": msgid,
            "type": "response",
            "completion": (status.status == tss_constants.StatusFlags.SUCCESS),
            "status": {
                "error_code": status.status.name,
                "message": status.message
            }
        }
        print(data)
        await network_client.send_feedback(data)

    run_tree = None

    async def run_cb():
        """
        id: <id>
        command: "run"
        content: <behavior_tree_content>
        node_pointer: <start_node_id_if_any>
        ---
        id: <id_of_request_message>
        type: "response"
        completion: true/false
        status: {
            error_code: <code_in_StatusFlags>,
            message: <message_if_any>
        }
        logs: {
            node_name: <last_loaded_node_name>
            node_pointer: <last_loaded_node_id>
        }
        """
        global run_tree
        msg_command = "run"

        while True:
            if len(network_client.queue[msg_command]) == 0:
                await asyncio.sleep(.1)
                continue

            msg_details = copy.deepcopy(network_client.queue[msg_command][-1])  # only allows executing last command in queue
            network_client.queue[msg_command] = []  # clean queue
            print("got command %s" % msg_command)

            run_tree = asyncio.create_task(tsd.runTree(msg_details["content"], board, rsi, envg, msg_details["node_pointer"]))

            status = await run_tree
            await asyncio.sleep(3)  # to avoid message stuck from cancel
            run_tree = None
            data = {
                "id": msg_details["id"],
                "type": "response",
                "completion": (status.status == tss_constants.StatusFlags.SUCCESS),
                "status": {
                    "error_code": status.status.name,
                    "message": status.message
                },
                "logs": {
                    "node_name": tsd.log_last_executed_node_name,
                    "node_pointer": tsd.log_last_executed_node_id
                }
            }
            await network_client.send_feedback(data)

    async def load_config(msg_id, msg_content):
        global run_tree
        print("checking status of tss ...")
        if run_tree is not None:
            msg = "setup_cb(): cannot load configs while a sequence is already running. please retry on idling"
            await return_status(msg_id, "setup", tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg))
            return
        print("loading config ...")
        cfl = config_loader.ConfigLoader()
        status = cfl.loadConfigs(msg_content)
        if status.status != tss_constants.StatusFlags.SUCCESS:
            await return_status(msg_id, "setup", status)
            return
        print("initializing engines ...")
        status = await envg.init(cfl.general_config, cfl.robot_structure_config, cfl.envg_config)
        if status.status != tss_constants.StatusFlags.SUCCESS:
            await return_status(msg_id, "setup", status)
            return
        print("initializing skill library ...")
        status = rsi.init(cfl.general_config, cfl.skill_library_config)
        if status.status != tss_constants.StatusFlags.SUCCESS:
            await return_status(msg_id, "setup", status)
            return
        print("loading engines ...")
        status = await envg.callEnvironmentLoadPipeline()
        if status.status != tss_constants.StatusFlags.SUCCESS:
            await return_status(msg_id, "setup", status)
            return
        print("setup load done!")
        await return_status(msg_id, "setup", tss_structs.Status(tss_constants.StatusFlags.SUCCESS))

    async def setup_cb():
        """
        id: <id>
        command: "setup"
        content: <config_content>
        ---
        id: <id_of_request_message>
        type: "response"
        completion: true/false
        status: {
            error_code: <code_in_StatusFlags>,
            message: <message_if_any>
        }
        """
        msg_command = "setup"

        while True:
            if len(network_client.queue[msg_command]) == 0:
                await asyncio.sleep(.1)
                continue

            msg_details = copy.deepcopy(network_client.queue[msg_command][-1])  # only allows executing last command in queue
            msg_id = msg_details["id"]
            msg_content = msg_details["content"]
            network_client.queue[msg_command] = []  # clean queue
            print("got command %s" % msg_command)

            setup_task = asyncio.create_task(load_config(msg_id, msg_content))
            await setup_task

    async def abort_cb():
        """
        id: <id>
        command: "abort"
        emergency: true/false
        ---
        id: <id_of_request_message>
        type: "abort"
        completion: true/false
        status: {
            error_code: <code_in_StatusFlags>,
            message: <message_if_any>
        }
        """
        msg_command = "abort"
        global run_tree

        while True:
            if len(network_client.queue[msg_command]) == 0:
                await asyncio.sleep(.1)
                continue

            msg_details = copy.deepcopy(network_client.queue[msg_command][-1])  # only allows executing last command in queue
            msg_id = msg_details["id"]
            network_client.queue[msg_command] = []  # clean queue
            print("got command %s" % msg_command)

            if run_tree is None:
                msg = 'abort_cb(): unexpected call to abort when a sequence is not running'
                status = tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
                await return_status(msg_id, "abort", status)
                return

            cancel_tree = asyncio.create_task(rsi.cancelTask(envg, msg_details["emergency"]))
            status = await cancel_tree
            await return_status(msg_id, "abort", status)

    if default_tssconfig != "":
        with open(default_tssconfig) as f: configs = json.load(f)
        setup_task = asyncio.create_task(load_config("", configs))
        await setup_task  # regardless of success or not, will continue

    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    cbs = [run_cb(), setup_cb(), abort_cb()]
    await asyncio.gather(*cbs, return_exceptions=False)

    await network_client.disconnect()


async def standalone_mode(config_url: str, bt_file: str):

    with open(config_url) as f: configs = json.load(f)

    cfl = config_loader.ConfigLoader()
    status = cfl.loadConfigs(configs)
    if status.status != tss_constants.StatusFlags.SUCCESS:
        print(status.message)
        raise Exception("standalone_mode: failed to load general config!")

    envg = envg_interface.EngineInterface()
    status = await envg.init(cfl.general_config, cfl.robot_structure_config, cfl.envg_config)
    if status.status != tss_constants.StatusFlags.SUCCESS:
        print(status.message)
        raise Exception("standalone_mode: failed to init the engine interface!")

    rsi = skill_interface.SkillInterface()
    status = rsi.init(cfl.general_config, cfl.skill_library_config)
    if status.status != tss_constants.StatusFlags.SUCCESS:
        print(status.message)
        raise Exception("standalone_mode: failed to init the skill interface!")

    board = blackboard.Blackboard()

    status = await envg.callEnvironmentLoadPipeline()
    if status.status != tss_constants.StatusFlags.SUCCESS:
        raise Exception("standalone_mode: failed to load engine pipeline!")

    tsd = bt_decoder.TaskSequenceDecoder()
    with open(bt_file) as f: bt = json.load(f)

    run_tree = asyncio.create_task(tsd.runTree(bt, board, rsi, envg))
    await run_tree


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials", help="credentials file")
    parser.add_argument("--config", default="", help="specify if pre-loading any default config file")
    parser.add_argument("--connection", help="connection style to TSS (mqtt) will not connect to TSS core if empty", default="standalone")
    parser.add_argument("--btfile", help="task sequence to test (required only when running without server connections)", default="")
    pargs, unknown = parser.parse_known_args()

    # flags
    decode_only_test = (pargs.connection == "standalone")

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
        import tasqsym.assets.network.mqtt_bridge as mqtt_bridge
        network_client = mqtt_bridge.MQTTBridgeOnCore(pargs.credentials)
    elif pargs.connection != "standalone":
        raise Exception("unknown connection style %s" % pargs.connection)

    if decode_only_test:
        if pargs.config == "": raise Exception("config cannot be empty if testing without connections")
        if pargs.btfile == "": raise Exception("btfile cannot be empty if testing without connections")
        asyncio.run(standalone_mode(pargs.config, pargs.btfile))
    else:
        asyncio.run(distribute_mode(pargs.config, network_client))