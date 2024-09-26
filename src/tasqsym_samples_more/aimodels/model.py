# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import json
import os
import tasqsym.core.classes.engine_base as engine_base  # just for type hints
import tasqsym_encoder.aimodel.aimodel_base as aimodel_base


class ComplexScenario(aimodel_base.AIModel):

    def __init__(self, credentials: dict, use_azure: bool=True, logdir: str=''):
        samples_dirpath = '../robotics-task-sequencer-system-framework/src/tasqsym_samples/aimodel_samples'
        self.dir_system = os.path.join(samples_dirpath, 'system')  # use same ones as tasqsym_samples
        self.dir_query = os.path.join(samples_dirpath, 'query')    # use same ones as tasqsym_samples

        more_dirpath = '../robotics-task-sequencer-system-framework/src/tasqsym_samples_more/aimodels'
        self.dir_prompt = os.path.join(more_dirpath, 'prompt')
        self.action_definitions_file = os.path.join(more_dirpath, 'action_definitions.json')
        self.prompt_load_order = [
            'role_prompt',
            'environment_prompt',
            'output_prompt',
            'action_prompt',
            'example_prompt'
        ]
        super().__init__(credentials, use_azure=use_azure, logdir=logdir, use_mini=False)
        self.situation = ""
        self.cmd_id = 0
        self.node_tag = -1

    def my_node_parse_rule(self, node: dict, data_engine: engine_base.DataEngineBase) -> dict:
        self.node_tag += 1

        if node['node'] == 'GoalCheck':
            location_name = node['@where_to_check']
            what_to_check = node['@what_to_check']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "prepare"
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "navigate to " + location_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "percept: " + what_to_check,
                        "@set_variable": "{perception_true}", "@set_value": False
                    },
                    {
                        "Node": "CONDITION", "@node_tag": self.node_tag,
                        "@variable_name": "{perception_true}"
                    }
                ]
            }
        
        elif node['node'] == 'PickUp':
            target_name = node['@object']
            asset_name = node['@asset']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text" : "find the " + target_name,
                        "@set_variable": "{find_true}", "@set_value": True
                    },
                    {
                        "Node": "CONDITION", "@node_tag": self.node_tag,
                        "@variable_name": "{find_true}"
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "bring the hand close to the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "grasp the " + target_name + " from the " + asset_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "pick up the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "bring the " + target_name + " close to the robot"
                    }
                ]
            }

        elif node['node'] == 'Place':
            target_name = node['@object']
            asset_name = node['@asset']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text" : "find the " + asset_name,
                        "@set_variable": "{find_true}", "@set_value": True
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "bring the hand close to the " + asset_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "place the " + target_name + " to the " + asset_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "release the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "tuck the robot arm"
                    }
                ]
            }

        elif node['node'] == 'GoTo':
            location_name = node['@location']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "navigate to " + location_name
                    }
                ]
            }
        
        elif node['node'] == 'PushButton':
            target_name = node['@object']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text" : "find the " + target_name,
                        "@set_variable": "{find_true}", "@set_value": True
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "bring the hand close to the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "push button"
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "tuck the robot arm"
                    }
                ]
            }
        
        elif node['node'] == 'Wipe':
            target_name = node['@object']
            asset_name = node['@asset']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text" : "find the " + asset_name,
                        "@set_variable": "{find_true}", "@set_value": True
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "bring the hand close to the " + asset_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "place the " + target_name + " to the " + asset_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "wipe the " + asset_name + " with the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "pick up the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "tuck the robot arm"
                    }
                ]
            }

        elif node['node'] == 'Open':
            target_name = "handle"
            asset_name = node['@asset']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text" : "find the " + target_name + " of the " + asset_name,
                        "@set_variable": "{find_true}", "@set_value": True
                    },
                    {
                        "Node": "CONDITION", "@node_tag": self.node_tag,
                        "@variable_name": "{find_true}"
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "bring the hand close to the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "grasp the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "open the " + asset_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "release the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "tuck the robot arm"
                    }
                ]
            }

        elif node['node'] == 'Close':
            target_name = node['@object']
            asset_name = node['@asset']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text" : "find the " + target_name + " of the " + asset_name,
                        "@set_variable": "{find_true}", "@set_value": True
                    },
                    {
                        "Node": "CONDITION", "@node_tag": self.node_tag,
                        "@variable_name": "{find_true}"
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "bring the hand close to the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "grasp the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "close the " + asset_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "release the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "tuck the robot arm"
                    }
                ]
            }

        elif node['node'] == 'VisualCheck':
            true_situation = node['@true_situation']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "percept: " + true_situation,
                        "@set_variable": "{perception_true}", "@set_value": False
                    },
                    {
                        "Node": "CONDITION", "@node_tag": self.node_tag,
                        "@variable_name": "{perception_true}"
                    }
                ]
            }
        
        elif node['node'] == 'Pour':
            asset_name = node['@asset']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text" : "find the " + asset_name,
                        "@set_variable": "{find_true}", "@set_value": True
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "bring the hand close to the " + asset_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "pour"
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "tuck the robot arm"
                    }
                ]
            }

        elif node['node'] == 'ThrowAway':
            target_name = node['@object']
            asset_name = node['@asset']
            return {
                "Sequence": [
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text" : "find the " + asset_name,
                        "@set_variable": "{find_true}", "@set_value": True
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "bring the hand close to the " + asset_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "release the " + target_name
                    },
                    {
                        "Node": "ACTION", "@node_tag": self.node_tag,
                        "@print_text": "tuck the robot arm"
                    }
                ]
            }
        
        elif node['node'] == 'EmptySequence':
            return {
                "Sequence": []
            }
        
        else:
            out_node = {'Node': node['node']}
            for kk, vv in node.items():
                if kk == 'node': continue
                out_node.update({kk: vv})
            return out_node

    def compile_world(self, data_engine: engine_base.DataEngineBase) -> dict:
        _, ao_rel = data_engine.getData("asset_object_relations")
        _, la_rel = data_engine.getData("location_asset_relations")
        self.world = {
            "environment": {
                "asset_object_relations": ao_rel,
                "location_asset_relations": la_rel
            }
        }

    def format_response(self, generated_response: str) -> tuple[bool, dict]:  # override in child class if needed

        # expected string for default implementation:
        # ```python
        # {"MAIN_SEQUENCE": '....', "ULTIMATE_GOAL": "...", "WHERE_TO_CHECK_GOAL": "..."}
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
        response_values_as_dict["MAIN_SEQUENCE"] = response_values_as_dict["MAIN_SEQUENCE"].replace("'", '"')

        # below is a specific sample template assuming a specific response value from GPT
        if response_values_as_dict["MAIN_SEQUENCE"].startswith("sequence"):
            tree_template = """
                root {
                    selector {
                        condition [GoalCheck, ULTIMATE_GOAL, WHERE_TO_CHECK_GOAL]
                        retry {
                            sequence {
                                MAIN_SEQUENCE
                                condition [GoalCheck, ULTIMATE_GOAL, WHERE_TO_CHECK_GOAL]
                            }
                        }
                    }
                }
            """
        else:
            tree_template = """
                root {
                    selector {
                        condition [GoalCheck, ULTIMATE_GOAL, WHERE_TO_CHECK_GOAL]
                        retry {
                            sequence {
                                sequence {
                                    MAIN_SEQUENCE
                                }
                                condition [GoalCheck, ULTIMATE_GOAL, WHERE_TO_CHECK_GOAL]
                            }
                        }
                    }
                }
            """
        tree_template = tree_template.replace("MAIN_SEQUENCE", response_values_as_dict["MAIN_SEQUENCE"])
        tree_template = tree_template.replace("ULTIMATE_GOAL", f'"{response_values_as_dict["ULTIMATE_GOAL"]}"')
        dslstr = tree_template.replace("WHERE_TO_CHECK_GOAL", f'"{response_values_as_dict["WHERE_TO_CHECK_GOAL"]}"')

        dslstr = self._format_dslstr(dslstr)
        with open(self.action_definitions_file, 'r') as file: action_definitions = json.loads(file.read())
        dsldict = self._dslstr2dict(dslstr, action_definitions)

        self.node_tag = -1  # reset node ID

        # must return with "task_sequence" field to work with server.py
        if dsldict is None: return (False, {})
        else: return (True, {"task_sequence": dsldict})