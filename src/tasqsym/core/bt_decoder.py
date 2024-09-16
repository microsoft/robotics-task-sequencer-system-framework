# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import asyncio

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.interface.blackboard as blackboard
import tasqsym.core.interface.envg_interface as envg_interface
import tasqsym.core.interface.skill_interface as skill_interface


class TaskSequenceDecoder:

    def __init__(self):

        # logging
        self.log_last_executed_node_name = ""
        self.log_last_executed_node_id = []

    async def runTree(self, bt: dict,
                      board: blackboard.Blackboard, rsi: skill_interface.SkillInterface, envg: envg_interface.EngineInterface,
                      start_from_node_id: list[int]=[], escape_at_node_id: list[int]=[]) -> tss_structs.Status:

        self.log_last_executed_node_name = ""
        self.log_last_executed_node_id = []

        # set start/escape settings if continuing from some node or executing a partial part of the tree
        self.start_from_node_id = start_from_node_id
        self.escape_at_node_id = escape_at_node_id

        # the top of the tree can be seen as a single node sequence
        nodes = bt["root"]["BehaviorTree"]["Tree"]
        task = asyncio.create_task(self.runSequence(nodes, board, rsi, envg, [0]))
        status = await task

        rsi.cleanup()

        return status

    async def parseControl(self, node: dict,
                           board: blackboard.Blackboard, rsi: skill_interface.SkillInterface, envg: envg_interface.EngineInterface,
                           node_id: list[int]) -> tss_structs.Status:

        if "Sequence" in node:
            node_id.append(0)
            task = asyncio.create_task(self.runSequence(node["Sequence"], board, rsi, envg, node_id))
            status = await task
            del node_id[-1]
        elif "Fallback" in node:
            node_id.append(0)
            task = asyncio.create_task(self.runFallback(node["Fallback"], board, rsi, envg, node_id))
            status = await task
            del node_id[-1]
        elif "RetryUntilSuccessful" in node:  # decorator must be a single child
            task = asyncio.create_task(self.retryUntilSuccessful(node["RetryUntilSuccessful"], board, rsi, envg, node_id))
            status = await task
        elif "Node" in node:
            task = asyncio.create_task(self.runNode(node, board, rsi, envg, node_id))
            status = await task
            if status.status == tss_constants.StatusFlags.SKIPPED: status.status = tss_constants.StatusFlags.SUCCESS  # ok
        else:
            print("BehaviorTreeControl: unknown node in Sequence", node)
            return tss_structs.Status(tss_constants.StatusFlags.UNEXPECTED)

        return status

    async def runSequence(self, nodes: list[dict],
                          board: blackboard.Blackboard, rsi: skill_interface.SkillInterface, envg: envg_interface.EngineInterface,
                          node_id: list[int]) -> tss_structs.Status:

        print('runSequence', nodes, node_id)
 
        for node in nodes:
            control_node = asyncio.create_task(self.parseControl(node, board, rsi, envg, node_id))
            status = await control_node
            if status.status != tss_constants.StatusFlags.SUCCESS: return status
            node_id[-1] += 1
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def runFallback(self, nodes: list[dict],
                          board: blackboard.Blackboard, rsi: skill_interface.SkillInterface, envg: envg_interface.EngineInterface,
                          node_id: list[int]) -> tss_structs.Status:
 
        print('runFallback', nodes, node_id)
 
        for node in nodes:
            control_node = asyncio.create_task(self.parseControl(node, board, rsi, envg, node_id))
            status = await control_node
            if (status.status == tss_constants.StatusFlags.SUCCESS) \
                or (status.status == tss_constants.StatusFlags.ABORTED) \
                      or (status.status == tss_constants.StatusFlags.ESCAPED):
                return status
            node_id[-1] += 1
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def runNode(self, node: dict,
                      board: blackboard.Blackboard, rsi: skill_interface.SkillInterface, envg: envg_interface.EngineInterface,
                      node_id: list[int]) -> tss_structs.Status:

        print('runNode', node, node_id)

        # if before specified start node id, skip
        if len(self.start_from_node_id) > 0:
            if len(node_id) != len(self.start_from_node_id):
                return tss_structs.Status(tss_constants.StatusFlags.SKIPPED)
            for n, num in enumerate(node_id):
                if num != self.start_from_node_id[n]:
                    return tss_structs.Status(tss_constants.StatusFlags.SKIPPED)
            self.start_from_node_id = []  # clear id so that continuing nodes will run

        self.log_last_executed_node_id = node_id
        self.log_last_executed_node_name = node["Node"]

        # if condition node
        if node["Node"] == "CONDITION":
            print('condition', board.getBoardVariable(node["@variable_name"]))
            if board.getBoardVariable(node["@variable_name"]):
                return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)
            else:
                return tss_structs.Status(tss_constants.StatusFlags.FAILED)

        # otherwise skill node
        skill_name = node["Node"].lower()

        status = rsi.setDecoder(skill_name)
        if status.status != tss_constants.StatusFlags.SUCCESS:
            print(status.message)
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, status.reason, status.message)
        
        status = rsi.setTask(skill_name)
        if status.status != tss_constants.StatusFlags.SUCCESS:
            print(status.message)
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, status.reason, status.message)

        status = rsi.runDecoder(node, board, envg)
        if status.status != tss_constants.StatusFlags.SUCCESS:
            print(status.message)
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, status.reason, status.message)

        run_task = asyncio.create_task(rsi.runTask(envg, board))
        status = await run_task
        if status.status != tss_constants.StatusFlags.SUCCESS:
            print(status.message)
            return status

        # if this is the specified escape node, escape
        if len(self.escape_at_node_id) > 0:
            if len(node_id) == len(self.escape_at_node_id):
                is_escape_node = True
                for n, num in enumerate(node_id):
                    if num != self.escape_at_node_id[n]:
                        is_escape_node = False
                        break
                if is_escape_node: return tss_structs.Status(tss_constants.StatusFlags.ESCAPED)

        return status

    async def retryUntilSuccessful(self, node: dict,
                                   board: blackboard.Blackboard, rsi: skill_interface.SkillInterface, envg: envg_interface.EngineInterface,
                                   node_id: list[int]) -> tss_structs.Status:

        print('retryUntilSuccessful', node, node_id)

        while True:
            control_node = asyncio.create_task(self.parseControl(node, board, rsi, envg, node_id))
            status = await control_node
            if status.status == tss_constants.StatusFlags.SUCCESS: break
            elif (status.status == tss_constants.StatusFlags.ABORTED) \
                  or (status.status == tss_constants.StatusFlags.ESCAPED):
                return status
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)