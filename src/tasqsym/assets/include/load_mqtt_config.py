# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import paho.mqtt.client as mqtt
import os
import ssl
import dotenv
from typing_extensions import Required
from typing_extensions import TypedDict


class ConnectionSettings(TypedDict, total=False):
    MQTT_HOST_NAME: Required[str]
    MQTT_TCP_PORT: Required[int]
    MQTT_USE_TLS: Required[bool]
    MQTT_TLS_INSECURE: Required[bool] # if True, no server cert validation is done
    MQTT_CLEAN_SESSION: Required[bool]
    MQTT_KEEP_ALIVE_IN_SECONDS: Required[int]
    MQTT_CLIENT_AUTH: Required[str] # if set, must be 'cert' or 'password' or 'anonymous'
    MQTT_CLIENT_ID: str
    MQTT_USERNAME: str
    MQTT_PASSWORD_FILE: str
    MQTT_CA_FILE: str
    MQTT_CERT_FILE: str
    MQTT_KEY_FILE: str

mqtt_setting_names: list[str] = [
    'MQTT_HOST_NAME',
    'MQTT_TCP_PORT',
    'MQTT_USE_TLS',
    'MQTT_TLS_INSECURE',
    'MQTT_CLEAN_SESSION',
    'MQTT_KEEP_ALIVE_IN_SECONDS',
    'MQTT_CLIENT_AUTH',
    'MQTT_CLIENT_ID',
    'MQTT_USERNAME',
    'MQTT_PASSWORD_FILE',
    'MQTT_CA_FILE',
    'MQTT_CERT_FILE',
    'MQTT_KEY_FILE'
]

def _convert_to_int(value: str, name: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise ValueError(f'{name} must be an integer')

def _convert_to_bool(value: str, name: str) -> bool:
    if value == 'true':
        return True
    elif value == 'false':
        return False
    else:
        raise ValueError(f'{name} must be true or false')

def get_connection_settings(env_filename: str) -> ConnectionSettings:
    env_file_dict = dotenv.dotenv_values(env_filename)
    envfile_values = {k: v for k, v in env_file_dict.items() if k in mqtt_setting_names}
    envvar_values = {k: v for k, v in os.environ.items() if k in mqtt_setting_names}
    default_values = {
        'MQTT_TCP_PORT': '8883',
        'MQTT_USE_TLS': 'true',
        'MQTT_TLS_INSECURE': 'false',
        'MQTT_CLEAN_SESSION': 'true',
        'MQTT_KEEP_ALIVE_IN_SECONDS': '30',
        'MQTT_CLIENT_AUTH': 'password',
        'MQTT_CLIENT_ID': '',
        'MQTT_CA_FILE': None,
        'MQTT_PASSWORD_FILE': None
    }

    final_values = {**default_values, **envvar_values, **envfile_values}

    if 'MQTT_HOST_NAME' not in final_values:
        raise ValueError('MQTT_HOST_NAME must be set')
    if final_values['MQTT_CLIENT_AUTH'] == 'password' and ('MQTT_PASSWORD_FILE' not in final_values or 'MQTT_USERNAME' not in final_values):
        raise ValueError('MQTT_USERNAME must be set if MQTT_PASSWORD_FILE is set')
    if final_values['MQTT_CLIENT_AUTH'] == 'cert' and ('MQTT_CERT_FILE' not in final_values or 'MQTT_KEY_FILE' not in final_values):
        raise ValueError('Client certificate and key files must be set if MQTT_CLIENT_AUTH is cert')
    if 'MQTT_TCP_PORT' in final_values:
        final_values['MQTT_TCP_PORT'] = _convert_to_int(final_values['MQTT_TCP_PORT'], 'MQTT_TCP_PORT')
    if 'MQTT_USE_TLS' in final_values:
        final_values['MQTT_USE_TLS'] = _convert_to_bool(final_values['MQTT_USE_TLS'], 'MQTT_USE_TLS')
    if 'MQTT_CLEAN_SESSION' in final_values:
        final_values['MQTT_CLEAN_SESSION'] = _convert_to_bool(final_values['MQTT_CLEAN_SESSION'], 'MQTT_CLEAN_SESSION')
    if 'MQTT_KEEP_ALIVE_IN_SECONDS' in final_values:
        final_values['MQTT_KEEP_ALIVE_IN_SECONDS'] = _convert_to_int(final_values['MQTT_KEEP_ALIVE_IN_SECONDS'],
                                                                     'MQTT_KEEP_ALIVE_IN_SECONDS')
    if 'MQTT_TLS_INSECURE' in final_values:
        final_values['MQTT_TLS_INSECURE'] = _convert_to_bool(final_values['MQTT_TLS_INSECURE'], 'MQTT_TLS_INSECURE')

    return final_values

def create_mqtt_client(connection_settings: ConnectionSettings):
    mqtt_client = mqtt.Client(
        client_id=connection_settings["MQTT_CLIENT_ID"],
        protocol=mqtt.MQTTv311,
        transport="tcp",
    )
    context = None
    if connection_settings['MQTT_USE_TLS']:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if connection_settings['MQTT_CA_FILE'] is not None:
            context.load_verify_locations(cafile=connection_settings['MQTT_CA_FILE'])
        else:
            context.load_default_certs()

    mqtt_password = None
    if connection_settings['MQTT_CLIENT_AUTH'] == 'password':
        with open(connection_settings['MQTT_PASSWORD_FILE'], 'r') as f:
            mqtt_password = f.read()
    elif connection_settings['MQTT_CLIENT_AUTH'] == 'cert':
        context.load_cert_chain(
            certfile=connection_settings['MQTT_CERT_FILE'],
            keyfile=connection_settings['MQTT_KEY_FILE']
        )
    mqtt_client.username_pw_set(connection_settings['MQTT_USERNAME'], mqtt_password)
    if context is not None:
        mqtt_client.tls_set_context(context)
        mqtt_client.tls_insecure_set(connection_settings['MQTT_TLS_INSECURE'])

    return mqtt_client