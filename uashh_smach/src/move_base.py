#!/usr/bin/env python

""" This file generates easy to use smach states needed to move the robot base. """

import roslib; roslib.load_manifest('uashh_smach')

import rospy
import tf

import math
import random
import threading

import smach
import smach_ros
from smach import State, Sequence
from smach_ros import ServiceState, SimpleActionState

from move_base_msgs.msg import MoveBaseGoal, MoveBaseAction
from geometry_msgs.msg import Pose, PoseStamped, Point, Quaternion 

import util



def pose_orientation_to_quaternion(msg):
    return [msg.x, msg.y, msg.z, msg.w]



    
def get_move_base_in_map_state(x, y):
    return get_move_base_state("/map", x, y)

def get_move_base_in_odom_state(x, y):
    return get_move_base_state("/odom", x, y)

'''Note: each state returned is only randomized once at initialization and then static.'''
def get_move_base_random_state():
    radius = random.random()*2 + 1  # 1-3 m
    #yaw = random.random()*TAU/2 - TAU/4    # +-90 deg
    yaw = random.random()*util.TAU*3/4 - util.TAU*3/8    # +-135 deg
    
    return get_move_base_state("/base_link", math.cos(yaw)*radius, math.sin(yaw)*radius, yaw)
    
'''Returns a MoveBaseGoal state which goal parameters are given via parameters at setup time.'''
def get_move_base_state(frame='/map', x=0, y=0, yaw=0):
    print "new goal: ", x, y, yaw
    base_goal = MoveBaseGoal()
    base_goal.target_pose.header.frame_id = frame
    base_goal.target_pose.header.stamp = rospy.Time.now()
        
    quat = tf.transformations.quaternion_from_euler(0, 0, yaw)
    base_goal.target_pose.pose.orientation = Quaternion(*quat)
    base_goal.target_pose.pose.position = Point(x, y, 0)
    
    return SimpleActionState('move_base', 
                             MoveBaseAction, 
                             goal=base_goal
                             )



'''move_base state with userdata input
frame defaults to '/map' if not given'''
class MoveBaseState(SimpleActionState):
    def __init__(self, frame='/map'):
        SimpleActionState.__init__(self, 'move_base', MoveBaseAction, input_keys=['x', 'y', 'yaw'], goal_cb=self._goal_cb)
        self.frame = frame
    
    def _goal_cb(self, userdata, old_goal):
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = self.frame
        goal.target_pose.header.stamp = rospy.Time.now()

        quat = tf.transformations.quaternion_from_euler(0, 0, userdata.yaw)
        goal.target_pose.pose.orientation = Quaternion(*quat)
        goal.target_pose.pose.position = Point(userdata.x, userdata.y, 0)
        return goal

        
'''radius range defaults to 1-3 m'''
class CalcRandomGoalState(State):
    def __init__(self, radius_min=1, radius_max=3):
        State.__init__(self, outcomes=['succeeded'], output_keys=['x', 'y', 'yaw'])
        self.radius_min = radius_min
        self.radius_max = radius_max
    
    def execute(self, ud):
        radius = random.random()*(self.radius_max - self.radius_min) + self.radius_min
        yaw = random.random() * util.TAU*3/4 - util.TAU*3/8    # +-135 deg
        
        ud.x = math.cos(yaw) * radius
        ud.y = math.sin(yaw) * radius
        ud.yaw = yaw
        return 'succeeded'


def get_random_goal_smach(frame):
    sq = Sequence(outcomes=['succeeded', 'aborted', 'preempted'], connector_outcome = 'succeeded') 
    
    sq.userdata.x = 0
    sq.userdata.y = 0
    sq.userdata.yaw = 0
    
    with sq: 
        # implicit usage of above userdata
        Sequence.add("CALC_RANDOM_GOAL", CalcRandomGoalState())
        Sequence.add("MOVE_RANDOM_GOAL", MoveBaseState(frame))
    
    return sq




class WaitForMsgState(smach.State):
    """This class acts as a generic message listener with blocking, timeout, latch and flexible usage.
    
    It is meant to be extended with a case specific class that initializes this one appropriately 
    and contains the msg_cb (or overloads execute if really needed).
    
    Its waitForMsg method implements the core functionality: waiting for the message, returning 
    the message itself or None on timeout.
    
    Its execute method wraps the waitForMsg and returns succeeded or aborted, depending on the returned 
    message beeing existent or None. Additionally, in the successfull case, the msg_cb, if given, will 
    be called with the message and the userdata, so that a self defined method can convert message data to 
    smach userdata.
    Those userdata fields have to be passed via 'additional_output_keys'.
    
    If the state outcome should depend on the message content, the msg_cb can dictate the outcome:
    If msg_cb returns True, execute() will return "succeeded".
    If msg_cb returns False, execute() will return "aborted".
    If msg_cb has no return statement, execute() will act as described above.
    
    If thats still not enough, execute() might be overloaded.
    
    If latch is True it will return the last received message, so one message might be returned indefinite times.
    """
    
    def __init__(self, topic, msg_type, msg_cb=None, additional_output_keys=[], latch=False):
        smach.State.__init__(self, outcomes=['succeeded', 'aborted'],  output_keys=additional_output_keys)
        self.latch = latch
        self.mutex = threading.Lock()
        self.msg = None
        self.msg_cb = msg_cb
        self.subscriber = rospy.Subscriber(topic, msg_type, self._callback, queue_size=1)

    def _callback(self, msg):
        self.mutex.acquire()
        self.msg = msg
        self.mutex.release()

    def waitForMsg(self):
        '''returns the message or None, not an outcome'''
        print 'Waiting for message...'
        # wait for a maximum of .. seconds
        for i in range(0, 30*100):
            self.mutex.acquire()
            if self.msg != None:
                print 'Got message.'
                message = self.msg
                
                if not self.latch:
                    self.msg = None
                
                self.mutex.release()
                return message
            self.mutex.release()
            rospy.sleep(.1)
        
        print 'Timeout!'
        return None

    def execute(self, ud):
        '''Default simplest execute(), see class description.'''
        msg = self.waitForMsg()
        if msg != None:
            # call callback if there is one
            if self.msg_cb != None:
                cb_result = self.msg_cb(msg, ud)
                # check if callback wants to dictate output
                if cb_result != None:
                    if cb_result:
                        return 'succeeded'
                    else:
                        return 'aborted'
            return 'succeeded'
        else:
            return 'aborted'


class WaitForGoalState(WaitForMsgState):
    def __init__(self):
        WaitForMsgState.__init__(self, '/move_base_task/goal', PoseStamped, self._msg_cb, additional_output_keys=['x', 'y', 'yaw'])

    def _msg_cb(self, msg, ud):
        ud.x = msg.pose.position.x
        ud.y = msg.pose.position.y
        (roll,pitch,yaw) = tf.transformations.euler_from_quaternion(pose_orientation_to_quaternion(msg.pose.orientation))
        ud.yaw = yaw




def _test_WaitForGoalState():
    rospy.init_node('smach')
    wfg = WaitForGoalState()
    print 'execute #1'
    wfg.execute(smach.UserData())
    print 'execute #2'
    wfg.execute(smach.UserData())
    print 'execute #3'
    wfg.execute(smach.UserData())
    #util.execute_smach_container(WaitForGoalState())






class HasMovedState(State):
    def _getXY(self):
        x,y,yaw = util.get_current_robot_position_in_odom_frame();
        return x,y
    
    def __init__(self, minimumDistance):
        smach.State.__init__(self, outcomes=['movement_exceeds_distance', 'movement_within_distance'])
        util.init_transform_listener()
        self.minimumDistance = minimumDistance
        self.lastX, self.lastY = self._getXY()

    def execute(self, userdata):
        currentX, currentY = self._getXY()
        currentDistance = math.sqrt(math.pow(currentX, 2) + math.pow(currentY, 2))
        rospy.logdebug("currentXY: %f,%f lastXY: %f,%f currentDistance: %f minimumDistance: %f", self.lastX, self.lastY, currentX, currentY, currentDistance, self.minimumDistance)
        if currentDistance >= self.minimumDistance:
            self.lastX = currentX
            self.lastY = currentY
            return 'movement_exceeds_distance'
        else:
            return 'movement_within_distance'


class ReadRobotPositionState(State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['succeeded'], output_keys=['x', 'y', 'yaw'])
        util.init_transform_listener();

    def execute(self, userdata):
        userdata.x, userdata.y, userdata.yaw = util.get_current_robot_position_in_odom_frame();
        return 'succeeded'



if __name__ == '__main__':
    _test_WaitForGoalState()
