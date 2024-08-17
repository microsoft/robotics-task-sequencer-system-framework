# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import typing
import importlib
import asyncio

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs

import tasqsym.core.classes.skill_base as skill_base
import tasqsym.core.classes.skill_decoder as skill_decoder
import tasqsym.core.interface.blackboard as blackboard
import tasqsym.core.interface.envg_interface as envg_interface


class SkillInterface:
    """
    Class managing skill termination, skill switching.
    """

    task: skill_base.Skill = None
    decoder: skill_decoder.Decoder = None
    library: dict = None

    interrupt_pending: bool = False   # used when skill cannot be interrupted immediately

    def __init__(self):
        pass


    def init(self, general_config: dict, library: dict) -> tss_structs.Status:

        if len(library.keys()) == 0:
            msg = "skill_interface error: library list cannot be empty! call EnvironmentEngine.init() and import library_list_module_name"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        self.library = library
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)


    def setDecoder(self, skill_name: str) -> tss_structs.Status:

        if self.library is None:
            msg = "skill_interface error: skill library is empty! must call a successful init()!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if skill_name not in self.library:
            msg = "skill_interface error: could not find skill %s in library" % skill_name
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if "decoder" not in self.library[skill_name]:
            msg = "skill_interface error: skill %s missing an essential field 'decoder'" % skill_name
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if "decoder_configs" not in self.library[skill_name]: configs = {}
        else: configs = self.library[skill_name]["decoder_configs"]

        decoder_path = '.'.join(self.library[skill_name]["decoder"].split('.')[:-1])
        decoder_class = self.library[skill_name]["decoder"].split('.')[-1]
        decoder_module = importlib.import_module(decoder_path)
        self.decoder = getattr(decoder_module, decoder_class)(configs)

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)


    def setTask(self, skill_name: str) -> tss_structs.Status:

        if self.library is None:
            msg = "skill_interface error: skill library is empty! must call a successful init()!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        # setDecoder() called before setTask() so skill_name must exist in self.library

        if "src" not in self.library[skill_name]:
            msg = "skill_interface error: skill %s missing an essential field 'src'" % skill_name
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        
        if "src_configs" not in self.library[skill_name]: configs = {}
        else: configs = self.library[skill_name]["src_configs"]
        
        skill_path = '.'.join(self.library[skill_name]["src"].split('.')[:-1])
        skill_class = self.library[skill_name]["src"].split('.')[-1]
        skill_module = importlib.import_module(skill_path)
        self.task = getattr(skill_module, skill_class)(configs)

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)
    

    def runDecoder(self, encoded_params: dict, board: blackboard.Blackboard, envg: envg_interface.EngineInterface) -> tss_structs.Status:

        if self.decoder is None:
            msg = "skill_interface error: tried to run decoder before being set!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        status = self.decoder.decode(encoded_params, board)
        if status.status != tss_constants.StatusFlags.SUCCESS: return status

        status = self.decoder.fillRuntimeParameters(encoded_params, board, envg)

        return status


    async def runTask(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard) -> tss_structs.Status:

        if (self.task is None) or (self.decoder is None):
            msg = "skill_interface error: tried to run skill before setup!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        if not self.decoder.isReadyForExecution():
            msg = "skill_interface error: flag indicates decoder has not yet been decoded! \
                  make sure Decoder class sets decoded to True on decode() call"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        skill_params = self.decoder.asConfig()

        run_init = asyncio.create_task(self._initTask(envg, skill_params))
        status = await run_init
        if status.status != tss_constants.StatusFlags.SUCCESS: return status

        while True:
            iterate_once = asyncio.create_task(self._iterateOnce(envg))
            status = await iterate_once
            if status.status != tss_constants.StatusFlags.SUCCESS:
                return status
            if status.reason == tss_constants.StatusReason.SUCCESSFUL_TERMINATION:
                break

        run_finish = asyncio.create_task(self._finishTask(envg, board))
        status = await run_finish

        """
        Abort if abort is pending (note, abort status is prioritized against failure status).
        Abort completely terminates the sequence whereas failures could trigger fallback skills.
        """
        if self.interrupt_pending:
            self.interrupt_pending = False
            return tss_structs.Status(tss_constants.StatusFlags.ABORTED)

        return status


    async def cancelTask(self, envg: envg_interface.EngineInterface, emergency_stop: bool) -> tss_structs.Status:

        # emergency stop is triggered regardless of system state
        if emergency_stop:
            envg.controller_env.emergency_stop_request = True
            if envg.controller_env.control_task is not None:
                envg.controller_env.control_task.cancel()
            estop = asyncio.create_task(envg.controller_env.emergencyStop())
            status = await estop
            return status

        # usual task cancel process (only valid when controllers are running)
        if self.task is None:
            msg = 'skill_interface warning: unexpected call to abort when a sequence is not running'
        
        elif not self.task.interruptible_skill:
            msg = 'skill_interface warning: tried to abort but skill is non-interruptible, waiting for skill finish before abort'
            self.interrupt_pending = True

        elif envg.controller_env.control_task is None:
            msg = 'skill_interface error: could not cancel due to bad timing! please retry later'
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        else:
            msg = 'skill_interface: cancel during controller execution!'
            envg.controller_env.emergency_stop_request = False
            envg.controller_env.control_task.cancel()

        print(msg)
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS, message=msg)


    def cleanup(self):

        self.task = None
        self.decoder = None
        self.interrupt_pending = False


    async def _initTask(self, envg: envg_interface.EngineInterface, skill_params: dict) -> tss_structs.Status:

        status = self.task.init(envg, skill_params)
        if status.status != tss_constants.StatusFlags.SUCCESS: return status

        # anyInitiationAction must return the task name in the returned variable

        initiation_action = self.task.anyInitiationAction(envg)
        if initiation_action is not None:
            run_action = asyncio.create_task(envg.callEnvironmentUpdatePipeline(initiation_action))
            status = await run_action
            if status.status != tss_constants.StatusFlags.SUCCESS: return status
            status = self.task.anyPostInitation(envg)

        self.pt = 0

        return status


    async def _iterateOnce(self, envg: envg_interface.EngineInterface, action: typing.Optional[dict]=None) -> tss_structs.Status:

        observation = self._getStateVector(envg)

        if action is None: action = self.task.getAction(observation)
        terminate = self.task.getTerminal(observation, action)

        if terminate:
            """
            Actions from getAction() will not be sent on termination.
            A skill may explicitly perform a termination action if needed by returning actions using onFinish().
            However, the main purpose of onFinish() is to save 'flags' to the blackboard for continuing tasks.
            """
            return tss_structs.Status(
                tss_constants.StatusFlags.SUCCESS, tss_constants.StatusReason.SUCCESSFUL_TERMINATION
            )

        action_ = self.task.formatAction(action)

        update_engine_pipeline = asyncio.create_task(envg.callEnvironmentUpdatePipeline(action_))
        status = await update_engine_pipeline

        self.pt += 1
        return status
    

    async def _finishTask(self, envg: envg_interface.EngineInterface, board: blackboard.Blackboard, action: typing.Optional[dict]=None) -> tss_structs.Status:

        finishing_action = self.task.onFinish(envg, board)
        if finishing_action is not None:
            run_action = asyncio.create_task(envg.callEnvironmentUpdatePipeline(finishing_action))
            status = await run_action
            return status
        
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)


    def _getStateVector(self, envg: envg_interface.EngineInterface) -> dict:

        state = {}
        state["observable_timestep"] = self.pt  # "iteration", for reward definition etc.

        state = self.task.appendTaskSpecificStates(state, envg)

        return state
