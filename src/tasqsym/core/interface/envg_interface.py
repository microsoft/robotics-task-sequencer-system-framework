# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import copy
import importlib
import asyncio

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
import tasqsym.core.common.world_format as world_format
import tasqsym.core.classes.engine_base as engine_base


class EngineInterface:
    """
    Class managing the execution pipeline including monitoring orchestration / simulator orchestration.
    """

    # essential engines
    kinematics_env: engine_base.KinematicsEngineBase = None
    controller_env: engine_base.ControllerEngineBase = None

    # optional for encoder-decoder situation sharing
    data_env: engine_base.DataEngineBase = None

    """
    optional for simulated sensors and training
    please use physics_sim and rendering_sim only if they differ from the controller_env
    physics_sim and rendering_sim exist only for simulator orchestration purposes
    """
    world_constructor_env: engine_base.WorldConstructorEngineBase = None
    physics_sim: engine_base.SimulationEngineBase = None
    rendering_sim: engine_base.SimulationEngineBase = None


    def __init__(self):
        pass


    async def init(self, general_config: dict, rs_config: dict, envg_config: dict) -> tss_structs.Status:
        """
        async in case asynchronous initiation is required in the future.
        """

        # cleanup in case some old settings are running
        cleanup_tasks: list[asyncio.Coroutine] = []
        if self.kinematics_env is not None:
            cleanup_tasks.append(asyncio.create_task(self.kinematics_env.close()))
        if self.controller_env is not None:
            cleanup_tasks.append(asyncio.create_task(self.controller_env.close()))
        if self.data_env is not None:
            cleanup_tasks.append(asyncio.create_task(self.data_env.close()))
        if self.physics_sim is not None:
            cleanup_tasks.append(asyncio.create_task(self.physics_sim.close()))
        if self.rendering_sim is not None:
            cleanup_tasks.append(asyncio.create_task(self.rendering_sim.close()))

        if len(cleanup_tasks) > 0:  # can be 0 if first-time loading of config
            self.run_close = asyncio.gather(*cleanup_tasks, return_exceptions=False)
            success_flags: list[tss_structs.Status] = await self.run_close
            status = tss_structs.Status(tss_constants.StatusFlags.SUCCESS)
            for s in success_flags:
                if s.status != tss_constants.StatusFlags.SUCCESS:
                    status.message = '; ' + s.message
            if status.status != tss_constants.StatusFlags.SUCCESS: return status
            await asyncio.sleep(1.)  # just in case for clean finish
            # remove all running engines
            self.kinematics_env = None
            self.controller_env = None
            self.data_env = None
            self.world_constructor_env = None
            self.physics_sim = None
            self.rendering_sim = None

        # load config
        if "kinematics" not in envg_config or envg_config["kinematics"] is None:
            msg = "envg config error: must have the 'engines/kinematics' field and cannot be null!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        if "controller" not in envg_config or envg_config["controller"] is None:
            msg = "envg config error: must have the 'engines/controller' field and cannot be null!"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)
        if "data" not in envg_config:
            msg = "envg config error: must have the 'engines/data' field, set to 'null' if not used"
            return tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg)

        # simulation only engines (not required for real robot)
        if "world_constructor" in envg_config:
            status, self.world_constructor_env = self._getEngine("world_constructor", envg_config["world_constructor"])
            if status.status != tss_constants.StatusFlags.SUCCESS:  return status
        if "physics_sim" in envg_config:
            status, self.physics_sim = self._getEngine("physics_sim", envg_config["physics_sim"])
            if status.status != tss_constants.StatusFlags.SUCCESS:  return status
        if "rendering_sim" in envg_config:
            status, self.rendering_sim = self._getEngine("rendering_sim", envg_config["rendering_sim"])
            if status.status != tss_constants.StatusFlags.SUCCESS:  return status

        # essential engine
        status, self.kinematics_env = self._getEngine("kinematics", envg_config["kinematics"])
        if status.status != tss_constants.StatusFlags.SUCCESS:  return status

        # essential engine
        status, self.controller_env = self._getEngine("controller", envg_config["controller"])
        if status.status != tss_constants.StatusFlags.SUCCESS:  return status

        # setup data engine
        status, self.data_env = self._getEngine("data", envg_config["data"])
        if status.status != tss_constants.StatusFlags.SUCCESS:  return status
        if self.data_env is not None:
            status = await self.data_env.init(general_config, rs_config, envg_config["data"].get("config", {}))
            if status.status != tss_constants.StatusFlags.SUCCESS: return status

        # initiate all other engines
        init_tasks: list[asyncio.Coroutine] = []
        if self.kinematics_env is not None:
            init_tasks.append(asyncio.create_task(self.kinematics_env.init(general_config, rs_config, envg_config["kinematics"].get("config", {}))))
        if self.controller_env is not None:
            init_tasks.append(asyncio.create_task(self.controller_env.init(general_config, rs_config, envg_config["controller"].get("config", {}))))
        if self.physics_sim is not None:
            init_tasks.append(asyncio.create_task(self.physics_sim.init(general_config, rs_config, envg_config["physics_sim"].get("config", {}))))
        if self.rendering_sim is not None:
            init_tasks.append(asyncio.create_task(self.rendering_sim.init(general_config, rs_config, envg_config["rendering_sim"].get("config", {}))))

        # note, since kinematics_env and controller_env cannot be None, always some initiation task
        self.run_initiation = asyncio.gather(*init_tasks, return_exceptions=False)
        success_flags: list[tss_structs.Status] = await self.run_initiation
        status = tss_structs.Status(tss_constants.StatusFlags.SUCCESS)
        for s in success_flags:
            if s.status != tss_constants.StatusFlags.SUCCESS:
                status.message += '; ' + s.message

        return status


    def _getEngine(self, ename: str, engine_details: dict) -> tuple[tss_structs.Status, engine_base.EngineBase]:
        if engine_details is None: return (tss_structs.Status(tss_constants.StatusFlags.SUCCESS), None)

        if "engine" not in engine_details:
            msg = "envg config error: 'engines/%s/engine' field required, specify the path.class string" % ename
            return (tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg), None)
        engine_module = ".".join(engine_details["engine"].split(".")[0:-1])
        engine_class = engine_details["engine"].split(".")[-1]

        if "class_id" not in engine_details:  # only used for world_constructor and loading components to simulators
            msg = "envg config error: 'engines/%s/class_id' field required, \
                if the engine connects to the same world as the world constructor, must have the same id" % ename
            return (tss_structs.Status(tss_constants.StatusFlags.FAILED, message=msg), None)
        class_id = engine_details["class_id"]

        engine_module = importlib.import_module(engine_module)
        engine: engine_base.EngineBase = getattr(engine_module, engine_class)(class_id)

        return (tss_structs.Status(tss_constants.StatusFlags.SUCCESS), engine)


    async def callEnvironmentLoadPipeline(self, world_construct_params: dict={}) -> tss_structs.Status:
        """
        Load components and initial robot state to all engines.
        world_construct_params: parameters for world construction if any (to use only for simulation training)
        ---
        return: success or errors if any
        """
        print("callEnvironmentLoadPipeline")

        """
        Component loading (for simulation only).
        """
        if self.world_constructor_env is None:
            print("warning: world constructor env is null, not loading components")
            components: list[world_format.ComponentStruct] = []
        else: components = self.world_constructor_env.getSpawnComponents(world_construct_params)

        """
        Load the initial robot state.
        """
        update_task = asyncio.create_task(self.controller_env.updateActualRobotStates())
        await update_task
        start_robot_state = self.controller_env.getLatestRobotStates()

        """
        Reset engines and load components/robots.
        Resets are valid for the physics, scenery, and controller engines (only if the controller is a simulator).
        """

        resets: list[asyncio.Coroutine] = []
        if self.controller_env.control_in_simulated_world: resets.append(self.controller_env.reset())
        if self.physics_sim is not None: resets.append(self.physics_sim.reset())
        if self.rendering_sim is not None: resets.append(self.rendering_sim.reset())
        if len(resets) > 0:
            reset_task = asyncio.gather(*resets, return_exceptions=False)
            success_flags: list[tss_structs.Status] = await reset_task
            for s in success_flags:
                if s.status != tss_constants.StatusFlags.SUCCESS:
                    return s

        """
        Load components orignated from the world constructor.
        Valid for the physics, scenery, and controller engines (only if the controller is a simulator).
        If the engine is identical to the world constructor, will skip.
        """

        self.latest_component_states = copy.deepcopy(components)
        c_loads: list[asyncio.Coroutine] = []
        if self.world_constructor_env is not None:  # if is None, cannot load components
            class_ids = [self.world_constructor_env.class_id]
            if self.controller_env.control_in_simulated_world and (self.controller_env.class_id not in class_ids):
                c_loads.append(self.controller_env.loadComponents(components))
                class_ids.append(self.controller_env.class_id)
            if (self.physics_sim is not None) and (self.physics_sim.class_id not in class_ids):
                c_loads.append(self.physics_sim.loadComponents(components))
                class_ids.append(self.physics_sim.class_id)
            if (self.rendering_sim is not None) and (self.rendering_sim.class_id not in class_ids):
                c_loads.append(self.rendering_sim.loadComponents(components))
                class_ids.append(self.rendering_sim.class_id)
            if len(c_loads) > 0:
                c_load_task = asyncio.gather(*c_loads, return_exceptions=False)
                success_flags: list[tss_structs.Status] = await c_load_task
                for s in success_flags:
                    if s.status != tss_constants.StatusFlags.SUCCESS:
                        return s

        """
        Load robot orginates from the controller engine. Below for the physics and scenery engine.
        """

        r_loads: list[asyncio.Coroutine] = []
        if self.physics_sim is not None: r_loads.append(self.physics_sim.loadRobot(start_robot_state))
        if self.rendering_sim is not None: r_loads.append(self.rendering_sim.loadRobot(start_robot_state))
        if len(r_loads) > 0:
            r_load_task = asyncio.gather(*r_loads, return_exceptions=False)
            success_flags: list[tss_structs.Status] = await r_load_task
            for s in success_flags:
                if s.status != tss_constants.StatusFlags.SUCCESS:
                    return s

        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)


    async def callEnvironmentUpdatePipeline(self, input_actions: tss_structs.CombinedRobotAction) -> tss_structs.Status:
        """
        Execute the environment engine pipeline.
        input_action: the desired actions of the robot
        ---
        return: success or errors if any
        """
        print("callEnvironmentUpdatePipeline")

        world_state = world_format.WorldStruct(
            world_format.CombinedRobotStruct(
                self.controller_env.getLatestRobotStates(),
                input_actions,
                tss_structs.Status(tss_constants.StatusFlags.UNKNOWN)
            ),
            self.latest_component_states)

        """
        Run the kinematics engine (may add/remove/replace actions, kind of a buffer for correcting actions).
        """
        get_desired_states =  asyncio.create_task(self.kinematics_env.update(world_state))
        updated_state = await get_desired_states

        if updated_state.status.status != tss_constants.StatusFlags.SUCCESS:
            print(updated_state.status.message)
            return updated_state.status
        
        """
        Execute actions with the controller engine.
        """
        execute_actions = asyncio.create_task(self.controller_env.update(updated_state))
        updated_state = await execute_actions

        if updated_state.status.status != tss_constants.StatusFlags.SUCCESS:
            print("aborted engine pipeline at controller engine!")
            return updated_state.status

        """
        Update the simulation worlds if any (only if sensor values are obtained from simulation worlds).
        Note, physics always runs before rendering (not in parallel) in case component states are updated using physics.
        """

        if self.physics_sim is not None:
            update_env = asyncio.create_task(self.physics_sim.update(updated_state))
            updated_state = await update_env
            if updated_state.status.status != tss_constants.StatusFlags.SUCCESS:
                print("aborted engine pipeline at physics engine!")
                return updated_state.status

        if self.rendering_sim is not None:
            update_env = asyncio.create_task(self.rendering_sim.update(updated_state))
            updated_state = await update_env
            if updated_state.status.status != tss_constants.StatusFlags.SUCCESS:
                print("aborted engine pipeline at rendering engine!")
                return updated_state.status

        self.latest_component_states = copy.deepcopy(updated_state.component_states)
        return updated_state.status
