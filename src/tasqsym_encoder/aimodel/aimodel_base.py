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
import regex
import warnings
from collections import OrderedDict


enc = tiktoken.get_encoding("cl100k_base")  

class AIModel(ABC):

    # please define in child class before calling __init__()
    dir_system: str
    dir_prompt: str
    dir_query: str
    action_definitions_file: str
    prompt_load_order: list[str]

    world: dict = {}  # please define compile_world() to fill in content

    def __init__(self, credentials: dict, use_azure: bool=True, logdir: str='', use_mini: bool=False):
        self.use_azure = use_azure
        self.use_mini = use_mini
        self.logdir = logdir  # log AOAI outputs if not an empty string
        if self.use_azure:
            self.api_version = "2024-02-01"
            self.client = openai.AzureOpenAI(
                # cf. https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#rest-api-versioning
                api_version=self.api_version,
                # cf. https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource?pivots=web-portal#create-a-resource
                azure_endpoint = credentials["AZURE_OPENAI_ENDPOINT_GPT4OMINI"] if self.use_mini else credentials["AZURE_OPENAI_ENDPOINT"],
                api_key = credentials["AZURE_OPENAI_KEY_GPT4OMINI"] if self.use_mini else credentials["AZURE_OPENAI_KEY"]
            )            
        else:
            self.client = openai.OpenAI(
                api_key = credentials["OPENAI_API_KEY"]
            )
        self.credentials = credentials
        self.messages = []
        self.max_token_length = 8000
        self.max_completion_length = 1000
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
                # insert the action definitions loaded from file to the action prompt
                if data.find('ACTION_DEFINITIONS_PLACEHOLDER') != -1:  # only enters for action prompt
                    with open(self.action_definitions_file, 'r') as file:
                        action_definitions = file.read()
                    data = data.replace('ACTION_DEFINITIONS_PLACEHOLDER', action_definitions)
            data_split = re.split(r'\[user\]\n|\[assistant\]\n', data)
            data_split = [item for item in data_split if len(item) != 0]
            # messages start with "user" and ends with "system"
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
                with open(self.action_definitions_file, 'r') as file:
                    action_definitions = file.read()
                data = data.replace('ACTION_DEFINITIONS_PLACEHOLDER', action_definitions)
            data_split = re.split(r'\[user\]\n|\[assistant\]\n', data)
            data_split = [item for item in data_split if len(item) != 0]
            # messages start with "user" and ends with "system"
            assert len(data_split) % 2 == 0
            for i, item in enumerate(data_split):
                if i % 2 == 0: self.messages.append({"sender": "user", "text": item})
                else: self.messages.append({"sender": "assistant", "text": item})


    """Functions to get results from GPT."""

    def _create_prompt(self) -> str:
        prompt = []
        prompt.append(self.system_message)
        for message in self.messages:
            prompt.append({"role": message['sender'], "content": message['text']})
        prompt_content = ""
        for message in prompt:
            prompt_content += message["content"]
        print('prompt length: ' + str(len(enc.encode(prompt_content))))
        if len(enc.encode(prompt_content)) > self.max_token_length - self.max_completion_length:
            print('prompt too long. truncated.')
            # truncate the prompt by removing the oldest two messages
            self.messages = self.messages[2:]
            prompt = self._create_prompt()
        return prompt

    def _format_dslstr(self, text: str) -> str:
        lines = text.strip().splitlines()
        indent_level = 0
        formatted_lines = []
        for line in lines:
            stripped_line = line.strip()
            # remove "\" from the end of the line"
            stripped_line = stripped_line.rstrip("\\")
            stripped_line = stripped_line.replace("];", "]")
            stripped_line = stripped_line.replace("],", "]")
            # remove ; from the end of the line
            if not stripped_line: continue
            if stripped_line == "}": indent_level -= 1
            formatted_lines.append("    " * indent_level + stripped_line)
            if stripped_line.endswith("{"): indent_level += 1
        return "\n".join(formatted_lines)

    def _dslstr2dict(self, text: str, action_definitions: dict) -> dict:
        text = text.strip()
        if text.startswith("action") or text.startswith("condition"):
            parent_type = "action" if text.startswith("action") else "condition"
            start = text.find('[') + 1
            end = text.find(']', start)
            content = text[start:end].strip()
            node_content = self._dslstr2dict_parse_node(content, parent_type, action_definitions)
            return node_content
        elif text.startswith("root"):
            parent_type = "root"
            pattern = r'root (\{(?:[^{}]|(?1))*\})'
        elif text.startswith("sequence"):
            parent_type = "sequence"
            pattern = r'sequence (\{(?:[^{}]|(?1))*\})'
        elif text.startswith("selector"):
            parent_type = "selector"
            pattern = r'selector (\{(?:[^{}]|(?1))*\})'
        elif text.startswith("retry"):
            parent_type = "retry"
            pattern = r'retry (\{(?:[^{}]|(?1))*\})'
        else:
            warnings.warn("pattern was not set. probably input is not a valid format.")
            return None

        # get code block (e.g., "root {X}" => "{X}")
        try: matches = regex.findall(pattern, text)
        except:
            warnings.warn("pattern was not set. probably input is not a valid format.")
            return None

        if matches:
            content = max(matches, key=len)  # extract the longest match (the most outside block)
            content = content[1:-1]  # remove brackets (e.g., "{sequence {X}}" => "sequence {X}")
            if parent_type == "sequence" or parent_type == "selector": # child may have multiple nodes
                node_list = self._dslstr2dict_parse_nodes(content, action_definitions)
                return {parent_type: node_list}
            else: # single child (root and decorators by definition only have a single child)
                return {parent_type: self._dslstr2dict(content, action_definitions)}
        else:
            warnings.warn("No match found. Invalid format.")
            return None

    def _dslstr2dict_parse_node(self, text: str, node_type: str, action_definitions: dict) -> dict:
        content = text.split(',')
        # regardless of condition or action, mapped to action node
        # if is indeed a condition, remap to a CONDITION in model.py
        if len(content) == 1:  # node has zero args
            return {'node': content[0]}
        else:
            tmp_node = {'node': content[0]}
            action_list = action_definitions['Actions'] if node_type == 'action' else action_definitions['Conditions']
            for action in action_list:
                if action['Name'] == content[0]: break
                action = None
            if action is None: return {'node': content[0]}  # could not find arg definitions

            arg_info = action["Arguments"]
            for i, arg in enumerate(content[1:]):
                arg = arg.strip()
                try: arg = int(arg)
                except ValueError: arg = arg.strip('"')
                key = list(arg_info)[i]
                tmp_node[key] = arg
            return tmp_node

    def _dslstr2dict_parse_nodes(self, text: str, action_definitions: dict) -> dict:
        nodes = []
        i = 0
        while i < len(text):
            for key in ['condition', 'action']:
                if text[i:].startswith(key): break
                key = ""

            if key != "":
                start = text.find('[', i) + 1
                end = text.find(']', start)
                content = text[start:end].strip()
                node_content = self._dslstr2dict_parse_node(content, key, action_definitions)
                nodes.append(node_content)
                i = end + 1
            else:
                # Decorators are temporarily treated as a list as will be formatted in _parse_dict() anyway
                parent_type = ""
                for key in ['sequence', 'selector', 'retry']:
                    if text[i:].startswith(key):
                        parent_type = key
                        break
                if parent_type != "":
                    start = text.find('{', i) + 1
                    end = start
                    balance = 1  # We start after the opening '{', so we start with a balance of 1
                    while balance > 0:
                        if text[end] == '{': balance += 1
                        elif text[end] == '}': balance -= 1
                        end += 1
                    content = text[start:end-1]
                    node_list = self._dslstr2dict_parse_nodes(content, action_definitions)
                    nodes.append({parent_type: node_list})
                    i = end
                else:
                    i += 1  # Skip characters until we find a node type
        return nodes

    def generate(self, message: str, environment: str, is_user_feedback: bool=False) -> str:
        """
        Obtain a response from GPT from a user input string.
        message:          User input string.
        environment:      Current state of the environment (see compile_world()).
        is_user_feedback: Whether the user input string is a feedback to a previous generated reponse.

        return: Response from GPT.
        """
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
                    f.write(self._create_prompt())
            else:
                with open(file_name, 'w', encoding='utf-8') as f:
                    for item in self._create_prompt():
                        f.write(item['content'])
                        f.write('\n')

        self.current_time = time.time()
        time_diff = self.current_time - self.time_api_called
        if time_diff < self.waittime_sec:
            print("waiting for " + str(self.waittime_sec - time_diff) + " seconds...")
            time.sleep(self.waittime_sec - time_diff)

        while True:
            try:
                if self.use_azure:
                    deployment_name=self.credentials["AZURE_OPENAI_DEPLOYMENT_NAME_CHATGPT"]
                    response = self.client.chat.completions.create(
                        model=deployment_name,
                        # response_format={ "type": "json_object" },
                        messages=self._create_prompt(),
                        temperature=0.2,#2.0,
                        max_tokens=self.max_completion_length,
                        top_p=0.5,
                        frequency_penalty=0.0,
                        presence_penalty=0.0)
                    text = response.choices[0].message.content
                else:
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo-16k",
                        messages=self._create_prompt(),
                        temperature=0.2,#2.0,
                        max_tokens=self.max_completion_length,
                        top_p=0.5,
                        frequency_penalty=0.0,
                        presence_penalty=0.0)
                    text = response.choices[0].message.content
                self.time_api_called = time.time()
                break
            except Exception as e:
                print(e)
                match = re.search("retry after (\\d+) seconds", e.args[0])
                wait_time = int(match.group(1))
                print("api call failed due to rate limit. waiting for " + str(wait_time) + " seconds...")
                time.sleep(wait_time)
                continue
        self.messages.append({"sender": "assistant", "text": text})

        return text  # generated_response


    """Functions to generate skill-level trees from language-level trees."""

    def _map_tree(self, input_tree: dict, data_engine) -> dict:
        conv = OrderedDict({'root': {'BehaviorTree': {'ID': 'MainTree', 'Tree': []}}})
        conv['root']['BehaviorTree']['Tree'] = [self._parse_dict(input_tree['root'], data_engine)]
        return conv

    def _parse_list(self, nodes: list[dict], data_engine) -> list[dict]:
        tree = []
        for n in nodes:
            tree.append(self._parse_dict(n, data_engine))
        return tree

    def _parse_dict(self, v: dict, data_engine) -> dict:
        if 'node' in v: return self.my_node_parse_rule(v, data_engine)

        tree = {}
        for kk, vv in v.items():
            if kk == 'sequence':
                tree.update({'Sequence': self._parse_list(vv, data_engine)})

            elif kk == 'selector':
                tree.update({'Fallback': self._parse_list(vv, data_engine)})

            elif kk == 'retry':
                tree.update({'RetryUntilSuccessful': self._parse_dict(vv[0], data_engine)})
        return tree

    def encode(self, input_tree: dict, expected_outcome_states: dict, data_engine) -> dict:
        """
        Mapping from a tree using language-level action outputs to a tree using robot-executable skills.
        input_tree:              Language-level behavior tree generated using outputs from GPT.
        expected_outcome_states: The predicted state of the environment after performing all actions (if returned by GPT).
        data_engine:             The data lake about the environment to load data from and to.

        return: Behavior tree using robot-executable skills.
        """
        self.handle_expected_outcome_states(expected_outcome_states, data_engine)
        return self._map_tree(input_tree, data_engine)


    """Functions to implement by user."""

    @abstractmethod
    def compile_world(self, data_engine) -> dict:  # requires implementation in child class
        """
        Load from the data engine the environment data representation to use in the prompts.
        data_engine:  The data lake about the environment to load from.

        return: The environment representation in the defined environment prompt format.
        """
        pass

    def format_response(self, generated_response: str) -> tuple[bool, dict]:  # override in child class if needed
        """
        Format the response from GPT. For example, GPT could return values to be filled inside a template tree.
        generated_response: Response returned by GPT.

        return: Success flag, if success, formatted plan as a language-level behavior tree.
        """
        print("aimodel_base warning: using default implementation for format_response()")

        # expected string for default implementation:
        # ```python
        # {"task_sequence": '....', "environment_after": {...}}
        # ```

        # convert the response into a python dictionary
        start = generated_response.index('```python') + len('```python')
        end = generated_response.index('```', start)
        # handle single quotations and newlines
        splits = generated_response[start:end].strip().split("'")
        if len(splits) != 3:  # unexpected syntax around single quotations
            return (False, {})
        text_json = splits[0] + '"' + splits[1].replace('"', "'").replace("\n", "\\\\n") + '"' + splits[2]
        response_values_as_dict  = json.loads(text_json)
        # revert quotation format
        response_values_as_dict["task_sequence"] = response_values_as_dict["task_sequence"].replace("'", '"')

        # below is a specific sample template assuming a specific response value from GPT
        tree_template = """
            root {
                sequence {
                    TASK_SEQUENCE
                }
            }
        """
        dslstr = tree_template.replace("TASK_SEQUENCE", response_values_as_dict["task_sequence"])

        dslstr = self._format_dslstr(dslstr)
        with open(self.action_definitions_file, 'r') as file: action_definitions = json.loads(file.read())
        dsldict = self._dslstr2dict(dslstr, action_definitions)

        # must return with "task_sequence" field to work with server.py
        if dsldict is None: return (False, {})
        else: return (True, {"task_sequence": dsldict, "environment_after": response_values_as_dict["environment_after"]})

    def handle_expected_outcome_states(self, expected_outcome_states: dict, data_engine):
        """
        Use the predicted state to perform actions if any.
        expected_outcome_states: The predicted state of the environment after performing all actions (if returned by GPT).
        data_engine:             The data lake about the environment to load data from and to.
        """
        print("aimodel_base warning: using default implementation for handle_expected_outcome_states()")
        # default implementation does not use the outcome states

    def my_node_parse_rule(self, node: dict, data_engine) -> dict:  # override in class child if needed
        """
        Mapping from a language-level action node to a robot-executable skill node(s).
        node:                    Language-level action node in the behavior tree generated using outputs from GPT.
        expected_outcome_states: The predicted state of the environment after performing all actions (if returned by GPT).
        data_engine:             The data lake about the environment to load data from and to.

        return: Robot-executable skill node(s).
        """
        print("aimodel_base warning: using default implementation for my_node_parse_rule()")
        out_node = {'Node': node['node']}
        for kk, vv in node.items():
            if kk == 'node': continue
            out_node.update({kk: vv})
        return out_node
