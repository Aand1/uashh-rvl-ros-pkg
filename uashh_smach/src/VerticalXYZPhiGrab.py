#!/usr/bin/env python

""" This file provides a smach sequence of MoveArm calls that let the robot arm grab 
an object from above with the gripper in vertical downwards orientation.
"""

import roslib; roslib.load_manifest('uashh_smach')

import rospy
import tf
import math

import smach
import smach_ros
from smach import State, StateMachine, Sequence
from smach_ros import ServiceState, SimpleActionState

from geometry_msgs.msg import Pose, Quaternion
from arm_navigation_msgs.msg import MoveArmGoal, MoveArmAction, MotionPlanRequest, PositionConstraint, OrientationConstraint, JointConstraint, SimplePoseConstraint

import MoveJoints


PRE_GRAB_OFFSET = 0.1 # m
GRIPPER_MAX_WIDTH = 0.068 # m


def poseConstraintToPositionOrientationConstraints(pose_constraint):
    position_constraint = PositionConstraint()
    orientation_constraint = OrientationConstraint()
    position_constraint.header = pose_constraint.header
    position_constraint.link_name = pose_constraint.link_name
    position_constraint.position = pose_constraint.pose.position
    position_constraint.constraint_region_shape.type = 0
    position_constraint.constraint_region_shape.dimensions.append(2*pose_constraint.absolute_position_tolerance.x)
    position_constraint.constraint_region_shape.dimensions.append(2*pose_constraint.absolute_position_tolerance.y)
    position_constraint.constraint_region_shape.dimensions.append(2*pose_constraint.absolute_position_tolerance.z)

    position_constraint.constraint_region_orientation.x = 0.0
    position_constraint.constraint_region_orientation.y = 0.0
    position_constraint.constraint_region_orientation.z = 0.0
    position_constraint.constraint_region_orientation.w = 1.0

    position_constraint.weight = 1.0

    orientation_constraint.header = pose_constraint.header
    orientation_constraint.link_name = pose_constraint.link_name
    orientation_constraint.orientation = pose_constraint.pose.orientation
    orientation_constraint.type = pose_constraint.orientation_constraint_type

    orientation_constraint.absolute_roll_tolerance = pose_constraint.absolute_roll_tolerance
    orientation_constraint.absolute_pitch_tolerance = pose_constraint.absolute_pitch_tolerance
    orientation_constraint.absolute_yaw_tolerance = pose_constraint.absolute_yaw_tolerance
    orientation_constraint.weight = 1.0

    return (position_constraint, orientation_constraint)


def addGoalConstraintToMoveArmGoal(pose_constraint, move_arm_goal):
    position_constraint, orientation_constraint = poseConstraintToPositionOrientationConstraints(pose_constraint);
    move_arm_goal.motion_plan_request.goal_constraints.position_constraints.append(position_constraint)
    move_arm_goal.motion_plan_request.goal_constraints.orientation_constraints.append(orientation_constraint)




""" state that moves the gripper to a vertical position regarding x, y, z, phi and parent_frame from userdata """
class MoveVerticalGripperPoseActionState(SimpleActionState):
    def __init__(self):
        SimpleActionState.__init__(self, 'move_SchunkArm', MoveArmAction, input_keys=['x','y','z','phi','parent_frame'])
        pass
    
    def execute(self, userdata):
        self._goal.planner_service_name = "ompl_planning/plan_kinematic_path"
                
        motion_plan_request = MotionPlanRequest()
        motion_plan_request.group_name = "SchunkArm"
        motion_plan_request.num_planning_attempts = 1
        motion_plan_request.allowed_planning_time = rospy.Duration(5.0)
        motion_plan_request.planner_id = ""
        self._goal.motion_plan_request = motion_plan_request 
        
        desired_pose = SimplePoseConstraint()
        desired_pose.header.frame_id = userdata.parent_frame;
        desired_pose.link_name = "Gripper";
        desired_pose.pose.position.x = userdata.x;
        desired_pose.pose.position.y = userdata.y;
        desired_pose.pose.position.z = userdata.z;
        
        quat = tf.transformations.quaternion_from_euler(-math.pi/2, math.pi/2, userdata.phi)
        desired_pose.pose.orientation = Quaternion(*quat)
        desired_pose.absolute_position_tolerance.x = 0.02;
        desired_pose.absolute_position_tolerance.y = 0.02;
        desired_pose.absolute_position_tolerance.z = 0.02;
        desired_pose.absolute_roll_tolerance = 0.04;
        desired_pose.absolute_pitch_tolerance = 0.04;
        desired_pose.absolute_yaw_tolerance = 0.04;
        addGoalConstraintToMoveArmGoal(desired_pose, self._goal)
        
        srv_out = SimpleActionState.execute(self, userdata)
 
        return srv_out



""" """
def getVerticalGrabSequence(x, y, z, phi, grab_width, parent_frame):
    return _getVerticalSequence('grab', x, y, z, phi, grab_width, parent_frame)

def getVerticalDropSequence(x, y, z, phi, grab_width, parent_frame):
    return _getVerticalSequence('drop', x, y, z, phi, grab_width, parent_frame)
    
def _getVerticalSequence(task, x, y, z, phi, grab_width, parent_frame):
    
    sq = Sequence(
    outcomes = ['succeeded','aborted','preempted'],
    connector_outcome = 'succeeded')

    sq.userdata.x = x
    sq.userdata.y = y
    sq.userdata.z = z
    sq.userdata.z_pre = z + PRE_GRAB_OFFSET # cm pre grab position offset
    sq.userdata.phi = phi
    sq.userdata.parent_frame = parent_frame
    
    with sq:
        Sequence.add('MOVE_ARM_GRAB_PRE',
                       MoveVerticalGripperPoseActionState(),
                     
                        remapping={ 'x':'x',
                                    'y':'y',
                                    'z':'z_pre',
                                    'phi':'phi',
                                    'parent_frame':'parent_frame'}
                      )
        if(task == 'grab'):
            Sequence.add('MOVE_GRIPPER_OPEN', 
                           MoveJoints.getMoveGripperState(GRIPPER_MAX_WIDTH))
            
        Sequence.add('MOVE_ARM_GRAB',
                       MoveVerticalGripperPoseActionState(),
                        remapping={ 'x':'x',
                                    'y':'y',
                                    'z':'z',
                                    'phi':'phi',
                                    'parent_frame':'parent_frame'}
                      )
        if(task == 'grab'):
            Sequence.add('MOVE_GRIPPER_CLOSE', 
                           MoveJoints.getMoveGripperState(grab_width))
        else:
            Sequence.add('MOVE_GRIPPER_OPEN',
                           MoveJoints.getMoveGripperState(GRIPPER_MAX_WIDTH))
            
        Sequence.add('MOVE_ARM_GRAB_POST',
                       MoveVerticalGripperPoseActionState(),
                        remapping={ 'x':'x',
                                    'y':'y',
                                    'z':'z_pre',
                                    'phi':'phi',
                                    'parent_frame':'parent_frame'}
                      )

    return sq
