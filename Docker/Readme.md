# Running the core as a Docker container

## To build the core to a Docker container

From the project root, run:

```bash
docker build -t <docker_image_tag:ver> -f ./docker/Dockerfile .
```

## To run the core in a Docker container

To run the core as a Docker container that communicates with the server through MQTT,
 you can pass the MQTT configurations in environment variables to the container:

```env
MQTT_HOST_NAME: # mqtt server's host name or url
MQTT_TCP_PORT: # default "8883"
MQTT_USE_TLS: # default "true"
MQTT_TLS_INSECURE: # default "false", if True, no server cert validation
MQTT_CLIENT_AUTH: # default "password", can also be "cert" or "anonymous"
MQTT_CLIENT_ID: # str
MQTT_USERNAME: # str
MQTT_PASSWORD_FILE: # if MQTT_CLIENT_AUTH is "password"
MQTT_CA_FILE: # server CA cert if MQTT_USE_TLS is true
MQTT_CERT_FILE: # client cert if MQTT_CLIENT_AUTH is "cert"
MQTT_KEY_FILE: # client cert key if MQTT_CLIENT_AUTH is "cert"
```

To debug the docker container in VSCode, this is a sample `task.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "type": "docker-build",
      "label": "docker-build",
      "platform": "python",
      "dockerBuild": {
        "tag": "<docker_image_tag:ver",
        "dockerfile": "${workspaceFolder}/Docker/Dockerfile",
        "context": "${workspaceFolder}",
        "pull": true
      }
    },
    {
      "type": "docker-run",
      "label": "docker-run: debug",
      "dependsOn": [
        "docker-build"
      ],
      "dockerRun": {
        "env": {
          "MQTT_CLIENT_ID": "your_client_id",
          "MQTT_USERNAME": "your_user_name",
          "MQTT_PASSWORD_FILE": "/var/run/secrets/tokens/broker-sat",
          "MQTT_CA_FILE": "/var/run/certs/ca.crt",
          "MQTT_HOST_NAME": "your_mqtt_server",
          "MQTT_TCP_PORT": "your_mqtt_server_port",
        },
        "volumes": [
          {
            "localPath": "/path/to/ca.crt",
            "containerPath": "/var/run/certs/ca.crt"
          },
          {
            "localPath": "/path/to/mqtt_password",
            "containerPath": "/var/run/secrets/tokens/broker-sat"
          }
        ],
      },
      "python": {
        "file": "/tsscore/src/tasqsym/core.py",
        "args": [
          "--credentials",
          "/none.env",
          "--connection",
          "mqtt",
          "--config",
          "/tsscore/src/tasqsym_samples/sim_robot_sample_settings.json",
          "--btfile",
          "/tsscore/src/tasqsym_samples/generated_sequence_samples/throw_away_the_trash.json"
        ]
      },
    }
  ]
}
```

This is a sample `launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Server",
      "type": "debugpy",
      "request": "launch",
      "program": "src/tasqsym_encoder/server.py",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceRoot}/src",
      },
      "args": [
        "--credentials",
        "/path/to/credential_file",
        "--aoai",
        "--aimodel",
        "tasqsym_samples.aimodel_samples.model.PickPlaceScenario",
        "--config",
        "${workspaceRoot}/src/tasqsym_samples/encoder_sample_settings.json",
        "--connection",
        "mqtt",
      ]
    },
    {
      "name": "Core",
      "type": "debugpy",
      "request": "launch",
      "program": "src/tasqsym/core.py",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceRoot}/src",
        "MQTT_CLIENT_ID": "tsscore",
        "MQTT_CLIENT_AUTH": "password",
        "MQTT_USERNAME": "your_user_name",
        "MQTT_PASSWORD_FILE": "/path/to/password_file",
        "MQTT_CA_FILE": "/path/to/server_ca_crt",
        "MQTT_HOST_NAME": "your_mqtt_server",
        "MQTT_TCP_PORT": "8883",
        "MQTT_TLS_INSECURE": "false"
      },
      "args": [
        "--credentials",
        "/none.env",
        "--connection",
        "mqtt",
        "--config",
        "${workspaceRoot}/src/tasqsym_samples/sim_robot_sample_settings.json",
        "--btfile",
        "${workspaceRoot}/src/tasqsym_samples/generated_sequence_samples/throw_away_the_trash.json"
      ]
    },
    {
      "name": "Docker: Core",
      "type": "docker",
      "request": "launch",
      "preLaunchTask": "docker-run: debug",
      "python": {
        "pathMappings": [
          {
            "localRoot": "${workspaceFolder}",
            "remoteRoot": "/tsscore"
          }
        ],
        "projectType": "general",
      }
    }
  ]
}
```
