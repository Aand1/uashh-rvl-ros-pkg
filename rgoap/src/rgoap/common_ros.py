'''
Created on Jul 24, 2013

@author: felix
'''

import roslib; roslib.load_manifest('rgoap')
import rospy

import rostopic
import tf

from uashh_smach.platform.move_base import MoveBaseState, pose_orientation_to_quaternion

from std_msgs.msg import Empty
from nav_msgs.msg import Path
from nav_msgs.srv import GetPlan, GetPlanRequest
from geometry_msgs.msg import PoseStamped

from common import Action, Condition, Precondition, Effect, VariableEffect, Goal

from smach_bridge import SMACHStateWrapperAction
from rospy.service import ServiceException


## ROS specific class specializations

class ROSTopicCondition(Condition):
    """Mirrors a ROS message field of a topic as its value.
    Note that this Condition's value remains None until a message is received.
    """
    def __init__(self, state_name, topic, topic_class, field=None, msgeval=None):
        Condition.__init__(self, state_name)
        self._topic = topic
        self._field = field
        self._subscriber = rospy.Subscriber(topic, topic_class, self._callback)
        if msgeval is None:
            assert field is not None
            msgeval = rostopic.msgevalgen(field)
        self._msgeval = msgeval

        self._value = None

    def __repr__(self):
        return '<%s topic=%s field=%s>' % (self.__class__.__name__, self._topic, self._field)

    def _callback(self, msg):
        self._value = self._msgeval(msg)
#        print 'callback with: ', self._value

    def get_value(self):
        return self._value


# TODO: create super class ROSTopicAction(Action):


## concrete usable classes (no constructor parameters anymore)

class ResetBumperAction(Action):

    def __init__(self):
        Action.__init__(self,
                        [Precondition(Condition.get('robot.bumpered'), True)],
                        [Effect(Condition.get('robot.bumpered'), False)])
        self._publisher = rospy.Publisher('/bumper_reset', Empty)

    def check_freeform_context(self):
        return self._publisher.get_num_connections() > 0  # unsafe

    def run(self, next_worldstate):
        print 'num of subscribers: ', self._publisher.get_num_connections()
        print 'sending bumper_reset message..'
        self._publisher.publish(Empty())
        rospy.sleep(1)  # TODO: find solution without sleep
        # TODO: integrate check for asynchronous action bodys

# TODO: implement denial of trivial actions (not changing conditions), if they're actually concerned?

class MoveBaseAction(SMACHStateWrapperAction):

    class CheckForPathVarEffect(VariableEffect):
        def __init__(self, condition):
            VariableEffect.__init__(self, condition)
            self.service_topic = '/move_base/make_plan'
            self._service_proxy = rospy.ServiceProxy(self.service_topic, GetPlan)
            self._planned_paths_pub = rospy.Publisher('/task_planning/goal_paths', Path)

        def _is_reachable(self, value, start_value):
            request = GetPlanRequest()
            request.start.header.stamp = rospy.Time.now()
            request.start.header.frame_id = '/map'
            request.start.pose = start_value
            request.goal.header.stamp = rospy.Time.now()
            request.goal.header.frame_id = '/map'
            request.goal.pose = value
            request.tolerance = 0.3 # meters in x/y
            rospy.loginfo("%s sending request: %s", self, request)
            try:
                response = self._service_proxy(request)
                rospy.logwarn("%s received response: %s", self, response)
                response.plan.header.frame_id = '/map'
                self._planned_paths_pub.publish(response.plan)
                return len(response.plan.poses) > 0
            except ServiceException as e:
                rospy.logerr(e)
                return None

    def __init__(self):
        self._condition = Condition.get('robot.pose')
        self._check_path_vareffect = MoveBaseAction.CheckForPathVarEffect(self._condition)
        SMACHStateWrapperAction.__init__(self, MoveBaseState(),
                        [Precondition(Condition.get('robot.bumpered'), False),
                         Precondition(Condition.get('robot.arm_pose_floor'), True)
                        ],
                        [self._check_path_vareffect])

    def check_freeform_context(self):
        # TODO: cache freeform context?
        if not self.state._action_client.wait_for_server(rospy.Duration(1)):
            rospy.logwarn("%s context check: cannot access move_base action server"
                          % self.__class__.__name__)
            return False
        try:
            self._check_path_vareffect._service_proxy.wait_for_service(1)
        except rospy.exceptions.ROSException:
            rospy.logwarn("%s context check: cannot access %s service server"
                          % (self.__class__.__name__,
                             self._check_path_vareffect.service_topic))
            return False
        return True

    def _generate_variable_preconditions(self, var_effects, worldstate, start_worldstate):
        effect = var_effects.pop()  # this action has one variable effect
        assert effect._condition is self._condition
        precond_value = start_worldstate.get_condition_value(Condition.get('robot.pose'))
        return [Precondition(effect._condition, precond_value, None)]

    def translate_worldstate_to_userdata(self, next_worldstate, userdata):
        goal_pose = next_worldstate.get_condition_value(Condition.get('robot.pose'))
        (_roll, _pitch, yaw) = tf.transformations.euler_from_quaternion(
                        pose_orientation_to_quaternion(goal_pose.orientation))
        userdata.x = goal_pose.position.x
        userdata.y = goal_pose.position.y
        userdata.yaw = yaw



class MoveToPoseGoal(Goal):
    tl = None

    def __init__(self, pose, frame, usability):
        if frame != '/map' and frame != 'map':
            if MoveToPoseGoal.tl is None:
                MoveToPoseGoal.tl = tf.TransformListener()
                rospy.sleep(1)
            pose_stamped = PoseStamped()
            pose_stamped.header.frame_id = frame
            pose_stamped.pose = pose
            #tf.Transformer().waitForTransform('/map', frame)
            pose_stmpd_in_map = MoveToPoseGoal.tl.transformPose('/map', pose_stamped)
            pose = pose_stmpd_in_map.pose
        Goal.__init__(self, [Precondition(Condition.get('robot.pose'), pose)], usability)


class LocalAwareGoal(Goal):
    def __init__(self):
        Goal.__init__(self, [Precondition(Condition.get('awareness'), 1)], 0.3)