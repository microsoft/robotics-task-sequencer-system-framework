# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

import asyncio

import tasqsym.core.common.constants as tss_constants
import tasqsym.core.common.structs as tss_structs
from tasqsym.core.classes.physical_robot import PhysicalRobot


class SimRobotController(PhysicalRobot):

    """Names of joints in the simulated robot."""
    joint_names: list[str] = [
        "arm_joint_0", "arm_joint_1", "arm_joint_2", "arm_joint_3", "arm_joint_4", "arm_joint_5",
        "neck_joint_r", "neck_joint_p", "neck_joint_y"
    ]

    base_transform = tss_structs.Pose(tss_structs.Point(0,0,0), tss_structs.Quaternion(0,0,0,1))

    def __init__(self, model_info: dict):
        """self.role must be set before calling super().__init__()."""
        self.role = tss_constants.RobotRole.MOBILE_MANIPULATOR
        super().__init__(model_info)

    def connect(self, model_info: dict, configs: dict) -> tss_structs.Status:
        """
        Write the connections to the real hardware here.
        For example, if this was a ROS-connecting robot, use roslibpy and create a controller like below:

            class JointTrajectoryPublisher:
                def __init__(self, rosclient, joint_names):
                    self.joints_pub = roslibpy.Topic(rosclient, 'topic_name', 'trajectory_msgs/JointTrajectory')
                    self.joint_names = joint_names
                async def send(self, joint_values, timesec=3.0):
                    msg = {
                        'header': {'frame_id': '', 'stamp': {'sec': 0, 'nanosec': 0}},
                        'joint_names': self.joint_names,
                        'points': [
                            {
                                'positions': joint_values,
                                'time_from_start': {'sec': int(timesec), 'nanosec': int((timesec - int(timesec))*1000000000)}
                            }
                        ]
                    }
                    self.joints_pub.publish(roslibpy.Message(msg))
                    return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)
            self.rosclient = roslibpy.Ros(host, port)

            try: self.rosclient.run(30)
            except: print('could not connect')
            if not self.rosclient.is_connected: return tss_structs.Status(tss_constants.StatusFlags.FAILED)

            self.controller = JointTrajectoryPublisher(self.rosclient, self.joint_names)
            return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

        In this example, there will be no real hardware connections as a simulated robot.
        """
        print("=============== connected to the sim robot controller!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def disconnect(self) -> tss_structs.Status:
        """
        Write the disconnections from the real hardware here.
        In this example, no real hardware connections are established as a simulated robot.
        """
        print("=============== disconnected from the sim robot controller!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def init(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Initiate the controller.
        For example, send the robot to some zero pose like below:

            send_task = asyncio.create_task(self.controller.send(zero_pose))
            res = await send_task

            return res

        """
        print("=============== initiating sim robot controller ...")
        await asyncio.sleep(1.0)
        print("=============== initiated the sim robot controller!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def getLatestState(self) -> tss_structs.RobotState:
        """
        Write the logic to get the latest state from the controller here.
        Since this example does not have real hardware connections, will just return some dummy state values.
        """
        print("=============== got the latest state from the sim robot controller")
        return tss_structs.ManipulatorState(
            self.joint_names,
            tss_structs.JointStates([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            self.base_transform
        )

    async def sendJointAngles(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Send joint angles to the controller.
        For example, like the below:

            action: action_formats.FKAction = desired_actions[0]
            send_task = asyncio.create_task(self.controller.send(action.goal.joint_states.positions))
            res = await send_task

            return res

        """
        print("=============== sending joint angles to the sim robot controller ...")
        await asyncio.sleep(1.0)
        print("=============== finished sending joint angles to the sim robot controller!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def abortJointAngles(self) -> tss_structs.Status:
        """
        Write the logic to cancel the joint angle command here.
        """
        print("=============== aborted sim robot joint angle movement!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def sendBasePose(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Send base movement to the controller.
        For example, like the below:

            action: action_formats.Nav3DAction = desired_actions[0]
            send_task = asyncio.create_task(self.nav_base_controller.send(action.pose))
            res = await send_task

            return res

        """
        print("=============== sending base movement to the sim robot controller ...")
        await asyncio.sleep(1.0)
        print("=============== finished sending base movements to the sim robot controller!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def abortBasePose(self) -> tss_structs.Status:
        """
        Write the logic to cancel the base movement command here.
        """
        print("=============== aborted sim robot base movement!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def sendTargetMotion(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Send a target pose in cartesian space to the controller.
        For example, like the below:

            c_goals = []
            for goal in desired_actions:
                ik_goal: action_formats.IKAction = goal
                c_goals.append((ik_goal.goal.position, ik_goal.goal.orientation, ik_goal.source_links))
            solution = self.iksolver.solve(c_goals)
            action = action_formats.FKAction(solution)

            send_task = asyncio.create_task(self.controller.send(action.goal.joint_states.positions))
            res = await send_task

            return res

        """
        print("=============== sending target pose to the sim robot controller ...")
        await asyncio.sleep(1.0)
        print("=============== finished sending the sim robot controller to the target pose!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def abortTargetMotion(self) -> tss_structs.Status:
        """
        Write the logic to cancel the target pose command here.
        """
        print("=============== aborted sim robot target motion!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def sendPointToMotion(self, desired_actions: list[tss_structs.RobotAction], ref_state: tss_structs.RobotState) -> tss_structs.Status:
        """
        Send point to movement to the controller.
        For example, like the below:

            ik_goal: action_formats.PointToAction = desired_actions[0]
            look_goal = [ik_goal.point[0], ik_goal.point[1], ik_goal.point[2]]
            solution = self.lookat_solver.solve(look_goal, ik_goal.source_link)
            action = action_formats.FKAction(solution)

            send_task = asyncio.create_task(self.controller.send(action.goal.joint_states.positions))
            res = await send_task

            return res

        """
        print("=============== sending point target to the sim robot controller ...")
        await asyncio.sleep(1.0)
        print("=============== finished sending the sim robot controller to point to the target!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def abortPointToMotion(self) -> tss_structs.Status:
        """
        Write the logic to cancel the point to command here.
        """
        print("=============== aborted sim robot point to motion!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    async def emergencyStop(self) -> tss_structs.Status:
        """
        Write the logic to send the emergency stop to the controller, if the robot has such capabilities.
        """
        print("=============== emergency stopped sim robot!")
        return tss_structs.Status(tss_constants.StatusFlags.SUCCESS)

    def getLinkTransform(self, link_name: str) -> tuple[tss_structs.Status, tss_structs.Pose]:
        """
        Write the logic to get the link transform from the controller here.
        Since this example does not have real hardware connections, will just return some dummy transform.
        """
        print("=============== getting the link transform for link %s" % link_name)
        return (tss_structs.Status(tss_constants.StatusFlags.SUCCESS), tss_structs.Pose())
