# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

from abc import abstractmethod, ABC
import openai
import tiktoken
import json
import os
import re
import time


enc = tiktoken.get_encoding("cl100k_base")  

class AIModel(ABC):

    # please define in child class before calling __init__()
    dir_system: str
    dir_prompt: str
    dir_query: str
    prompt_load_order: list[str]

    world: dict = {}  # please define compile_world() to fill in content

    def __init__(self, credentials: dict, use_azure: bool=True, logdir: str=''):
        self.use_azure = use_azure
        self.logdir = logdir  # log AOAI outputs if not an empty string
        if self.use_azure:
            self.api_version = "2024-02-01"
            self.client = openai.AzureOpenAI(
                # cf. https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#rest-api-versioning
                api_version=self.api_version,
                # cf. https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource?pivots=web-portal#create-a-resource
                azure_endpoint=credentials["AZURE_OPENAI_ENDPOINT"],
                api_key = credentials["AZURE_OPENAI_KEY"]
            )            
        else:
            self.client = openai.OpenAI(
                api_key = credentials["OPENAI_API_KEY"]
            )
        self.credentials = credentials
        self.messages = []
        self.max_token_length = 8000
        self.max_completion_length = 1000
        self.last_response = None
        self.last_response_raw = None
        self.query = ''
        self.instruction = ''
        self.current_time = time.time()
        self.waittime_sec = 5
        self.time_api_called = time.time() - self.waittime_sec
        self.retry_count_tolerance = 10

        # load prompt file
        fp_system = os.path.join(self.dir_system, 'system.txt')
        with open(fp_system) as f:
            data = f.read()
        self.system_message = {"role": "system", "content": data}

        for prompt_name in self.prompt_load_order:
            fp_prompt = os.path.join(self.dir_prompt, prompt_name + '.txt')
            with open(fp_prompt) as f:
                data = f.read()
            data_split = re.split(r'\[user\]\n|\[assistant\]\n', data)
            data_split = [item for item in data_split if len(item) != 0]
            # it start with user and ends with system
            assert len(data_split) % 2 == 0
            for i, item in enumerate(data_split):
                if i % 2 == 0: self.messages.append({"sender": "user", "text": item})
                else: self.messages.append({"sender": "assistant", "text": item})

        fp_query = os.path.join(self.dir_query, 'query.txt')
        with open(fp_query) as f:
            self.query = f.read()

    def reset_history(self): # clear the conversation history and reset the prompt
        self.messages = []
        for prompt_name in self.prompt_load_order:
            fp_prompt = os.path.join(self.dir_prompt, prompt_name + '.txt')
            with open(fp_prompt) as f:
                data = f.read()
            data_split = re.split(r'\[user\]\n|\[assistant\]\n', data)
            data_split = [item for item in data_split if len(item) != 0]
            # it start with user and ends with system
            assert len(data_split) % 2 == 0
            for i, item in enumerate(data_split):
                if i % 2 == 0: self.messages.append({"sender": "user", "text": item})
                else: self.messages.append({"sender": "assistant", "text": item})

    def create_prompt(self):
        if self.use_azure and self.api_version == '2022-12-01':
            prompt = ""
            prompt = "<|im_start|>system\n"
            prompt += self.system_message["content"]
            prompt += "\n<|im_end|>\n"
            for message in self.messages:
                prompt += f"\n<|im_start|>{message['sender']}\n{message['text']}\n<|im_end|>"
            prompt += "\n<|im_start|>assistant\n"
            print('prompt length: ' + str(len(enc.encode(prompt))))
            if len(enc.encode(prompt)) > self.max_token_length - \
                    self.max_completion_length:
                print('prompt too long. truncated.')
                # truncate the prompt by removing the oldest two messages
                self.messages = self.messages[2:]
                prompt = self.create_prompt()
        else:
            prompt = []
            prompt.append(self.system_message)
            for message in self.messages:
                prompt.append(
                    {"role": message['sender'], "content": message['text']})
            prompt_content = ""
            for message in prompt:
                prompt_content += message["content"]
            print('prompt length: ' + str(len(enc.encode(prompt_content))))
            if len(enc.encode(prompt_content)) > self.max_token_length - \
                    self.max_completion_length:
                print('prompt too long. truncated.')
                # truncate the prompt by removing the oldest two messages
                self.messages = self.messages[2:]
                prompt = self.create_prompt()
        return prompt

    def extract_json_part(self, text: str):
        # JSON part is between ```python and ``` on a new line
        try:
            start = text.index('```python') + len('```python')
            end = text.index('```', start)
            text_json = text[start:end].strip()  # Removing any leading/trailing whitespace
            return text_json
        except ValueError:
            # This means '```python' or closing '```' was not found in the text
            return None

    def generate(self, message, environment, is_user_feedback=False):
        if is_user_feedback:
            self.messages.append({'sender': 'user', 'text': message})
        else:
            text_base = self.query
            if text_base.find('[ENVIRONMENT]') != -1:
                text_base = text_base.replace(
                    '[ENVIRONMENT]', json.dumps(environment))
            if text_base.find('[INSTRUCTION]') != -1:
                text_base = text_base.replace('[INSTRUCTION]', message)
                self.instruction = text_base
            self.messages.append({'sender': 'user', 'text': text_base})

        if self.logdir != '':
            # file name includes the name of this file and the current time
            file_name = self.logdir + \
                str(time.strftime('%Y%m%d_%H%M%S', time.localtime())) + \
                '_aimodel_task_planning.txt'
            if self.use_azure and self.api_version == '2022-12-01':
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(self.create_prompt()) 
            else:
                with open(file_name, 'w', encoding='utf-8') as f:
                    for item in self.create_prompt():
                        f.write(item['content'])
                        f.write('\n')

        self.current_time = time.time()
        time_diff = self.current_time - self.time_api_called
        if time_diff < self.waittime_sec:
            print("waiting for " + str(self.waittime_sec - time_diff) + " seconds...")
            time.sleep(self.waittime_sec - time_diff)
        retry_count = 0
        while True:
            try:
                if self.use_azure and self.api_version == '2022-12-01':
                    deployment_name=self.credentials["AZURE_OPENAI_DEPLOYMENT_NAME_CHATGPT"]
                    response = self.client.chat.completions.create(
                        model=deployment_name,
                        prompt=self.create_prompt(),
                        temperature=0.2,#2.0,
                        max_tokens=self.max_token_length,
                        top_p=0.5,
                        frequency_penalty=0.0,
                        presence_penalty=0.0,
                        stop=["<|im_end|>"]) 
                    text = response['choices'][0]['text']
                elif self.use_azure and self.api_version in ['2023-05-15', '2023-12-01-preview', '2024-02-01'] :
                    deployment_name=self.credentials["AZURE_OPENAI_DEPLOYMENT_NAME_CHATGPT"]
                    response = self.client.chat.completions.create(
                        model=deployment_name,
                        # response_format={ "type": "json_object" },
                        messages=self.create_prompt(),
                        temperature=0.2,#2.0,
                        max_tokens=self.max_completion_length,
                        top_p=0.5,
                        frequency_penalty=0.0,
                        presence_penalty=0.0)
                    text = response.choices[0].message.content
                else:
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo-16k",
                        messages=self.create_prompt(),
                        temperature=0.2,#2.0,
                        max_tokens=self.max_completion_length,
                        top_p=0.5,
                        frequency_penalty=0.0,
                        presence_penalty=0.0)
                    text = response.choices[0].message.content
                self.time_api_called = time.time()
                try:
                    # analyze the response
                    tmp_last_response = text
                    tmp_last_response = self.extract_json_part(tmp_last_response)
                    tmp_last_response = tmp_last_response.replace("'", "\"")
                    self.json_dict = json.loads(tmp_last_response, strict=False)
                    break
                except BaseException:
                    return text
            except Exception as e:
                print(e)
                match = re.search("retry after (\d+) seconds", e.args[0])
                wait_time = int(match.group(1))
                print("api call failed due to rate limit. waiting for " + str(wait_time) + " seconds...")
                time.sleep(wait_time)
                continue
        self.last_response = tmp_last_response
        self.last_response_raw = text
        self.messages.append(
            {"sender": "assistant", "text": self.last_response_raw})
        return self.json_dict

    @abstractmethod
    def compile_world(self, data_engine) -> dict:  # requires implementation in child class
        """
        Load from the data engine the environment data representation to use in the prompts.
        data_engine:  The data lake about the environment to load from.
        ---
        return: The environment representation in the defined environment prompt format.
        """
        pass

    # currently only supports a single sequence
    @abstractmethod
    def encode(self, action_sequence: list[str], expected_outcome_states: dict, data_engine) -> dict:  # requires implementation in child class
        """
        Define the mapping between GPT (language-level) action outputs and TSS skilss.
        action_sequence:         Returned by GPT. The output sequence of actions.
        expected_outcome_states: Returned by GPT. The predicted state of the environment after performing all actions.
        data_engine:             The data lake about the environment to load data from and to.
        ---
        return: Sequence of TSS skills.
        """
        pass
