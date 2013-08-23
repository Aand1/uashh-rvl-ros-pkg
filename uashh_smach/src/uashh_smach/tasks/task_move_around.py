#!/usr/bin/env python

""" This is a task to let the robot move around randomly. """

import roslib; roslib.load_manifest('uashh_smach')

import rospy
from smach import StateMachine

import uashh_smach.manipulator.look_around as look_around
import uashh_smach.platform.move_base as move_base
import uashh_smach.util as util


LOOKAROUND_SLEEP_DURATION = 2


def get_move_around_smach():
    sm = StateMachine(outcomes=['preempted', 'aborted'])
    #sm.set_initial_state('CHECK_MOVEMENT')

    with sm:
        StateMachine.add('SLEEP', util.SleepState(3),
                         transitions={'succeeded':'CHECK_ENABLED'})
        StateMachine.add('CHECK_ENABLED', util.CheckSmachEnabledState(),
                         transitions={'succeeded':'MOVE_RANDOMLY',
                                      'aborted':'SLEEP'})

        StateMachine.add('MOVE_RANDOMLY', move_base.get_random_goal_smach('/base_link'),
                         transitions={'succeeded':'SLEEP',
                                      'aborted':'CHECK_ENABLED'})

#        StateMachine.add("ARM_LOOK_AROUND", look_around.get_lookaround_smach(util.SleepState(LOOKAROUND_SLEEP_DURATION)),
#        StateMachine.add('ARM_LOOK_AROUND', util.SleepState(1),    # mockup

    return sm



def main():
    rospy.init_node('smach')
    util.execute_smach_container(get_move_around_smach(), enable_introspection=True)


if __name__ == '__main__':
    main()

