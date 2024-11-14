FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

#SHELL ["/bin/bash", "-c"]

RUN apt update && apt install -y --no-install-recommends && apt upgrade -y

RUN apt update && apt install python3-pip ssh xvfb git build-essential libssl-dev libffi-dev python3-dev -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# copy TSS
RUN mkdir /tsscore
ADD ./requirements.txt /tsscore/requirements.txt
ADD ./src/tasqsym /tsscore/src/tasqsym
ADD ./setup.py /tsscore/setup.py
WORKDIR /tsscore
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /tsscore/src/tasqsym_samples
RUN touch /tsscore/src/tasqsym_samples/__init__.py
ADD ./src/tasqsym_samples/sim_robot_sample_settings.json /tsscore/src/tasqsym_samples/sim_robot_sample_settings.json
ADD ./src/tasqsym_samples/generated_sequence_samples /tsscore/src/tasqsym_samples/generated_sequence_samples
ADD ./src/tasqsym_samples/robot_adapter_samples /tsscore/src/tasqsym_samples/robot_adapter_samples
ADD ./src/tasqsym_samples/sensor_adapter_samples /tsscore/src/tasqsym_samples/sensor_adapter_samples

RUN pip install .

# empty file, load using environment variables
RUN touch /none.env

CMD /bin/bash -c "python3 /tsscore/src/tasqsym/core.py --credentials /none.env --connection mqtt --config /tsscore/src/tasqsym_samples/sim_robot_sample_settings.json --btfile /tsscore/src/tasqsym_samples/generated_sequence_samples/throw_away_the_trash.json"