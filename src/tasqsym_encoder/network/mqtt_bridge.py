# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import sys
import asyncio
import json
import time
import paho.mqtt.client as mqtt
import tasqsym.assets.include.load_mqtt_config as load_mqtt_config


class MQTTBridgeOnServer:

    def __init__(self, mqtt_envfile: str):
        self.topic_d2c_feedback = "tasqsym/d2c/feedback"
        self.topic_c2d_command = "tasqsym/c2d/command"

        self.connected = False
        self.feedback = None
        self.mqtt_queue = {self.topic_d2c_feedback: {}}

        connection_settings = load_mqtt_config.get_connection_settings(mqtt_envfile)
        self.mqtt_client = load_mqtt_config.create_mqtt_client(connection_settings)

        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_publish = self.on_publish
        self.mqtt_client.on_subscribe = self.on_subscribe
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.connect(connection_settings['MQTT_HOST_NAME'], connection_settings['MQTT_TCP_PORT'], keepalive=connection_settings["MQTT_KEEP_ALIVE_IN_SECONDS"])
        self.mqtt_client.loop_start()

        elapsed = 0
        while not self.connected and elapsed < 5:
            time.sleep(1.)
            elapsed += 1
        if elapsed == 5:
            print('failed connection timeout')
            sys.exit(0)

        (_subscribe_result, subscribe_mid) = self.mqtt_client.subscribe(self.topic_d2c_feedback)
    def on_connect(self, _client, _userdata, _flags, rc):
        self.connected = (rc == mqtt.MQTT_ERR_SUCCESS)
    def on_publish(self, _client, _userdata, mid):
        print(f"Sent publish with message id {mid}")
    def on_subscribe(self, _client, _userdata, mid, _granted_qos):
        print(f"Subscribe for message id {mid} acknowledged by MQTT broker")
    def on_message(self, _client, _userdata, message):
        print(f"Received message on topic {message.topic} with payload {message.payload}")
        msg = json.loads(message.payload)
        self.mqtt_queue[message.topic][msg["id"]] = msg
    def on_disconnect(self, _client, _userdata, rc):
        print("Received disconnect with error='{}'".format(mqtt.error_string(rc)))

    def send_command(self, cmd, rest) -> int:
        timestamp = int(time.strftime("%Y%m%d%H%M%S", time.localtime()))
        data = {
            "id": timestamp,
            "command": cmd
        }
        data = {**data, **rest}
        # TODO: send_command to get topic (device id) as arg
        self.mqtt_client.publish(self.topic_c2d_command, json.dumps(data))
        return timestamp

    async def wait_feedback(self, timestamp) -> bool:
        print("waiting for %d in topic %s" % (timestamp, self.topic_d2c_feedback))
        try:
            while timestamp not in self.mqtt_queue[self.topic_d2c_feedback]:
                await asyncio.sleep(.1)
            self.feedback = self.mqtt_queue[self.topic_d2c_feedback].pop(timestamp)
        except asyncio.CancelledError:
            print('cancelled during monitoring')
            self.feedback = None
            return False
        return True

    def disconnect(self):
        self.mqtt_client.disconnect()