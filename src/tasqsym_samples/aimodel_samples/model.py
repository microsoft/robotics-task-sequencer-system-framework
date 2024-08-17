# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import os
import re
import tasqsym.core.common.constants as tss_constants
import tasqsym.core.classes.engine_base as engine_base  # just for type hints
import tasqsym_encoder.aimodel.aimodel_base as aimodel_base


class PickPlaceScenario(aimodel_base.AIModel):

    def __init__(self, credentials: dict, use_azure: bool=True, logdir: str=''):
        dirpath = './src/tasqsym_samples/aimodel_samples'
        self.dir_system = os.path.join(dirpath, 'system')
        self.dir_prompt = os.path.join(dirpath, 'prompt')
        self.dir_query = os.path.join(dirpath, 'query')
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
        _, loc_data = data_engine.getData("semantic_map_locations")
        locations = list(loc_data.keys())

        status, obj_props = data_engine.getData("object_properties")
        if status.status != tss_constants.StatusFlags.SUCCESS:
            _, obj_data = data_engine.getData("objects_metadata")
            objects = {}
            for obj_name in list(obj_data.keys()):
                objects[obj_name] = []
        else: objects = obj_props  # use state saved after encoding previous instruction

        status, asset_props = data_engine.getData("asset_properties")
        if status.status != tss_constants.StatusFlags.SUCCESS:
            _, assets_data = data_engine.getData("assets_metadata")
            assets = {}
            for asset_name in list(assets_data.keys()):
                assets[asset_name] = []
        else: assets = asset_props  # use state saved after encoding previous instruction

        status, hand_props = data_engine.getData("hand_properties")
        if status.status != tss_constants.StatusFlags.SUCCESS:
            hands = {
                "left": [], "right": []
            }
        else: hands = hand_props  # use state saved after encoding previous instruction

        _, ao_rel = data_engine.getData("asset_object_relations")
        _, la_rel = data_engine.getData("location_asset_relations")

        self.world = {
            "environment": {
                "locations": locations,
                "object_properties": objects,
                "asset_properties": assets,
                "hand_properties": hands,
                "asset_object_relations": ao_rel,
                "location_asset_relations": la_rel
            }
        }

        print("world:", self.world)

    def encode(self, action_sequence: list[str], expected_outcome_states: dict, data_engine: engine_base.DataEngineBase) -> dict:
        """
        In a real operation, the data engine should be some cloud storage where the state about the environment is updated from the robot.
        For now, just assume GPT will keep track of the environment state through reasoning.
        """
        data_names = ["object_properties", "asset_properties", "hand_properties", "asset_object_relations"]
        for data_name in data_names:
            if data_name in expected_outcome_states:
                data_engine.updateData(data_name, expected_outcome_states[data_name])

        # convert to TSS skills
        _, obj_data = data_engine.getData("objects_metadata")
        _, assets_data = data_engine.getData("assets_metadata")
        _, map_data = data_engine.getData("semantic_map_locations")

        task_models_save = []
        for task_item in action_sequence:
            pattern = r"\((.*?)\)"
            argument = None
            match = re.search(pattern, task_item)
            if match: argument = match.group(1)
            else: argument = None

            if task_item.startswith("Prepare"):
                tmp_element = {
                    "Node": "PREPARE"
                }
            elif task_item.startswith("Find"):
                target = argument.split(',')[0]
                left_or_right = argument.split(',')[-1].replace(' ', '')
                context = "find the " + target + " on the " + left_or_right

                tmp_element =  {
                    "Node": "FIND",
                    "@target_description": target,
                    "@context": context
                }
                task_models_save.append(tmp_element)
                tmp_element = {
                    "Node": "LOOK",
                    "@target": "{find_result}",
                    "@context": context
                }
                self.situation = "default situation"
            elif task_item.startswith("Grab"):
                target = argument.split(',')[0]
                object_situation = self._getSituationKey(obj_data[target], self.situation)
                obj = obj_data[target][object_situation]

                tmp_element = {
                    "Node": "GRASP",
                    "@grasp_type": obj["grasp_type"],
                    "@hand_laterality": obj["hand_laterality"],
                    "@approach_direction": obj["approach_direction"],
                    "@target": target,
                    "@context": "move the " + obj["hand_laterality"] + " hand to grasp a " + target + " using " + obj["grasp_type"] + " grasp"
                }
            elif task_item.startswith("MoveToLocation"):
                loc = map_data[argument]
                tmp_element = {
                    "Node": "NAVIGATION",
                    "@destination": loc["position"],
                    "@frame": "map",
                    "@orientation": loc["orientation"],
                    "@context": "move to the " + argument
                }
            elif task_item.startswith("MoveToObjectOrAsset"):
                target = argument
                if target in obj_data:
                    object_situation = self._getSituationKey(obj_data[target], self.situation)
                    obj = obj_data[target][object_situation]
                    context = "move the " + obj["hand_laterality"] + " hand to a " + target + " using " + obj["grasp_type"] + " grasp"
                else:
                    left_or_right = self.situation.split(" ")[0]
                    asset_situation = self._getSituationKey(assets_data[target], "default situation")
                    obj = assets_data[target][asset_situation]
                    context = "move the " + left_or_right + " hand to a " + target

                if obj["nav_position"] is not None:
                    tmp_element =  {
                        "Node": "NAVIGATION",
                        "@destination": obj["nav_position"],
                        "@frame": "{find_result}",
                        "@context": context
                    }
                    task_models_save.append(tmp_element)
                tmp_element =  {
                    "Node": "BRING",
                    "@destination": obj["bring_position"],
                    "@frame": obj["bring_frame"],
                    "@orientation": obj["bring_orientation"],
                    "@context": context
                }
                task_models_save.append(tmp_element)
                tmp_element = {
                    "Node": "LOOK",
                    "@target": "{find_result}",
                    "@context": context
                }
            elif task_item.startswith("Release"):
                object_situation = self._getSituationKey(obj_data[argument], self.situation)
                obj = obj_data[argument][object_situation]
                tmp_element =  {
                    "Node": "RELEASE",
                    "@depart_direction": obj["depart_direction"],
                    "@context": "release the " + obj["hand_laterality"] + " from the " + argument
                }
                task_models_save.append(tmp_element)
                tmp_element =  {
                    "Node": "BRING",
                    "@destination": None,
                    "@context": "move the " + obj["hand_laterality"] + " hand to self"
                }
            elif task_item.startswith("PickUp"):
                obj_arg = argument.split(',')[0]
                object_situation = self._getSituationKey(obj_data[obj_arg], self.situation)
                obj = obj_data[obj_arg][object_situation]
                asset_arg = argument.split(',')[-1].replace(' ', '')
                asset_situation = self._getSituationKey(assets_data[asset_arg], "default situation")
                asset = assets_data[asset_arg][asset_situation]
                tmp_element =  {
                    "Node": "PICK",
                    "@detach_direction": asset["detach_direction"],
                    "@context": "move the " + obj["hand_laterality"] + " hand to pick a " + obj_arg + " from the " + asset_arg
                }
                task_models_save.append(tmp_element)
                tmp_element =  {
                    "Node": "BRING",
                    "@destination": None,
                    "@context": "move the " + obj["hand_laterality"] + " hand to self"
                }
            elif task_item.startswith("Put"):
                obj_arg = argument.split(',')[0]
                object_situation = self._getSituationKey(obj_data[obj_arg], self.situation)
                obj = obj_data[obj_arg][object_situation]
                asset_arg = argument.split(',')[-1].replace(' ', '')
                asset_situation = self._getSituationKey(assets_data[asset_arg], "default situation")
                asset = assets_data[asset_arg][asset_situation]
                tmp_element =  {
                    "Node": "PLACE",
                    "@attach_direction": asset["attach_direction"],
                    "@context": "move the " + obj["hand_laterality"] + " hand to place a " + obj_arg + " to the " + asset_arg
                }
            else: continue
            task_models_save.append(tmp_element)

        task_models_save_json = {
            "root": {
                "BehaviorTree": {
                    "ID": "MainTree",
                    "Tree": [{"Sequence": task_models_save}]
                }
            }
        }
        return task_models_save_json

    def _getSituationKey(self, data: dict, default_key: str):
        if default_key in data: return default_key
        elif len(data.keys()) == 1: return list(data.keys())[0]
        else:
            """Get closest match to instruction (in this example, only one situation so does not apply)."""
            pass