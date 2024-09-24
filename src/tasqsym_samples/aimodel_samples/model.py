# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import os
import tasqsym.core.common.constants as tss_constants
import tasqsym.core.classes.engine_base as engine_base  # just for type hints
import tasqsym_encoder.aimodel.aimodel_base as aimodel_base


class PickPlaceScenario(aimodel_base.AIModel):

    def __init__(self, credentials: dict, use_azure: bool=True, logdir: str=''):
        dirpath = './src/tasqsym_samples/aimodel_samples'
        self.dir_system = os.path.join(dirpath, 'system')
        self.dir_prompt = os.path.join(dirpath, 'prompt')
        self.dir_query = os.path.join(dirpath, 'query')
        self.action_definitions_file = os.path.join(dirpath, 'action_definitions.json')
        self.prompt_load_order = [
            'role_prompt',
            'environment_prompt',
            'action_prompt',
            'output_prompt',
            'example_prompt'
        ]
        super().__init__(credentials, use_azure, logdir)
        self.situation = ""

    def compile_world(self, data_engine: engine_base.DataEngineBase) -> dict:
        _, ao_rel = data_engine.getData("asset_object_relations")
        _, la_rel = data_engine.getData("location_asset_relations")

        status, robot_state = data_engine.getData("robot_state")
        if status.status != tss_constants.StatusFlags.SUCCESS:
            robot_state = {
                "is_grasping": [],
                "at_location": "",
                "hands_used_for_action": []
            }
        # else, use state saved after encoding previous instruction

        self.world = {
            "environment": {
                "asset_object_relations": ao_rel,
                "location_asset_relations": la_rel,
                "robot_state": robot_state
            }
        }

        print("world:", self.world)

    def handle_expected_outcome_states(self, expected_outcome_states: dict, data_engine: engine_base.DataEngineBase):
        """
        In a real operation, the data engine should be some cloud storage where the state about the environment is updated from the robot.
        For now, just assume GPT will keep track of the environment state through reasoning.
        """
        data_names = ["asset_object_relations", "robot_state"]
        for data_name in data_names:
            if data_name in expected_outcome_states:
                data_engine.updateData(data_name, expected_outcome_states[data_name])

    def my_node_parse_rule(self, node: dict, data_engine: engine_base.DataEngineBase) -> dict:
        # convert to robot-execution-level skills

        if node['node'] == "Prepare":
            return {
                "Node": "PREPARE"
            }

        elif node['node'] == "Find":
            target = node['@target']
            left_or_right = node['@side']
            context = "find the " + target + " on the " + left_or_right
            self.situation = "default situation"
            return {"Sequence": [
                {
                    "Node": "FIND",
                    "@target_description": target,
                    "@context": context
                },
                {
                    "Node": "LOOK",
                    "@target": "{find_result}",
                    "@context": context
                }
            ]}

        elif node['node'] == "Grab":
            _, obj_data = data_engine.getData("objects_metadata")
            target = node['@target']
            object_situation = self._getSituationKey(obj_data[target], self.situation)
            obj = obj_data[target][object_situation]
            return {
                "Node": "GRASP",
                "@grasp_type": obj["grasp_type"],
                "@hand_laterality": obj["hand_laterality"],
                "@approach_direction": obj["approach_direction"],
                "@target": target,
                "@context": "move the " + obj["hand_laterality"] + " hand to grasp a " + target + " using " + obj["grasp_type"] + " grasp"
            }

        elif node['node'] == "MoveToLocation":
            _, map_data = data_engine.getData("semantic_map_locations")
            loc = map_data[node['@location']]
            return {
                "Node": "NAVIGATION",
                "@destination": loc["position"],
                "@frame": "map",
                "@orientation": loc["orientation"],
                "@context": "move to the " + node['@location']
            }

        elif node['node'] == "MoveToObjectOrAsset":
            _, obj_data = data_engine.getData("objects_metadata")
            _, assets_data = data_engine.getData("assets_metadata")
            target = node['@target']
            if target in obj_data:
                object_situation = self._getSituationKey(obj_data[target], self.situation)
                obj = obj_data[target][object_situation]
                context = "move the " + obj["hand_laterality"] + " hand to a " + target + " using " + obj["grasp_type"] + " grasp"
            else:
                left_or_right = self.situation.split(" ")[0]
                asset_situation = self._getSituationKey(assets_data[target], "default situation")
                obj = assets_data[target][asset_situation]
                context = "move the " + left_or_right + " hand to a " + target

            res = {"Sequence": []}
            if obj["nav_position"] is not None:
                res["Sequence"].append(
                    {
                        "Node": "NAVIGATION",
                        "@destination": obj["nav_position"],
                        "@frame": "{find_result}",
                        "@context": context
                    }
                )
            res["Sequence"] += [
                {
                    "Node": "BRING",
                    "@destination": obj["bring_position"],
                    "@frame": obj["bring_frame"],
                    "@orientation": obj["bring_orientation"],
                    "@context": context
                },
                {
                    "Node": "LOOK",
                    "@target": "{find_result}",
                    "@context": context
                }
            ]
            return res

        elif node['node'] == "Release":
            _, obj_data = data_engine.getData("objects_metadata")
            object_situation = self._getSituationKey(obj_data[node['@target']], self.situation)
            obj = obj_data[node['@target']][object_situation]
            return {"Sequence": [
                {
                    "Node": "RELEASE",
                    "@depart_direction": obj["depart_direction"],
                    "@context": "release the " + obj["hand_laterality"] + " from the " + node['@target']
                },
                {
                    "Node": "BRING",
                    "@destination": None,
                    "@context": "move the " + obj["hand_laterality"] + " hand to self"
                }
            ]}

        elif node['node'] == "PickUp":
            _, obj_data = data_engine.getData("objects_metadata")
            _, assets_data = data_engine.getData("assets_metadata")
            obj_arg = node['@target']
            object_situation = self._getSituationKey(obj_data[obj_arg], self.situation)
            obj = obj_data[obj_arg][object_situation]
            asset_arg = node['@asset']
            asset_situation = self._getSituationKey(assets_data[asset_arg], "default situation")
            asset = assets_data[asset_arg][asset_situation]
            return {"Sequence": [
                {
                    "Node": "PICK",
                    "@detach_direction": asset["detach_direction"],
                    "@context": "move the " + obj["hand_laterality"] + " hand to pick a " + obj_arg + " from the " + asset_arg
                },
                {
                    "Node": "BRING",
                    "@destination": None,
                    "@context": "move the " + obj["hand_laterality"] + " hand to self"
                }
            ]}

        elif node['node'] == "Put":
            _, obj_data = data_engine.getData("objects_metadata")
            _, assets_data = data_engine.getData("assets_metadata")
            obj_arg = node['@target']
            object_situation = self._getSituationKey(obj_data[obj_arg], self.situation)
            obj = obj_data[obj_arg][object_situation]
            asset_arg = node['@asset']
            asset_situation = self._getSituationKey(assets_data[asset_arg], "default situation")
            asset = assets_data[asset_arg][asset_situation]
            return {
                "Node": "PLACE",
                "@attach_direction": asset["attach_direction"],
                "@context": "move the " + obj["hand_laterality"] + " hand to place a " + obj_arg + " to the " + asset_arg
            }

        else:
            out_node = {'Node': node['node']}
            for kk, vv in node.items():
                if kk == 'node': continue
                out_node.update({kk: vv})
            return out_node

    def _getSituationKey(self, data: dict, default_key: str):
        if default_key in data: return default_key
        elif len(data.keys()) == 1: return list(data.keys())[0]
        else:
            """Get closest match to instruction (in this example, only one situation so does not apply)."""
            pass