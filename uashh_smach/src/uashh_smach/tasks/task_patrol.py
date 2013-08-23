#!/usr/bin/env python

""" This is a task that lets the robot patrol between two positions sent from e.g. rviz
and returns to the position it stood before moving in case of navigation failure. """

import roslib; roslib.load_manifest('uashh_smach')

import rospy

from smach import Sequence

import uashh_smach.platform.move_base as move_base
import uashh_smach.util as util



def get_patrol_smach():
    sq = Sequence(outcomes=['succeeded', 'aborted', 'preempted'],
                  connector_outcome='succeeded')

    sq.userdata.saved_position_x = 1
    sq.userdata.saved_position_y = 0
    sq.userdata.saved_position_yaw = 1

    sq.userdata.goal_position_1_x = 1
    sq.userdata.goal_position_1_y = 0
    sq.userdata.goal_position_1_yaw = 1

    sq.userdata.goal_position_2_x = 1
    sq.userdata.goal_position_2_y = 0
    sq.userdata.goal_position_2_yaw = 1


    wfg = move_base.WaitForGoalState() # We don't want multiple subscribers so we need one WaitForGoal state

    with sq:
        ## Add states to the container

        # save position
        Sequence.add('SAVE_ROBOT_POSITION', move_base.ReadRobotPositionState(),
                     remapping={'x':'saved_position_x',
                                'y':'saved_position_y',
                                'yaw':'saved_position_yaw'},
                     )

        ## command details

        # wait for goal 1
        Sequence.add('WAIT_FOR_GOAL_1', wfg,
                     remapping={'x':'goal_position_1_x',
                                'y':'goal_position_1_y',
                                'yaw':'goal_position_1_yaw'}
                         )

        # wait for goal 2
        Sequence.add('WAIT_FOR_GOAL_2', wfg,
                     remapping={'x':'goal_position_2_x',
                                'y':'goal_position_2_y',
                                'yaw':'goal_position_2_yaw'}
                         )

        ## action

        # nav to goal 1
        Sequence.add('MOVE_BASE_GO_1', move_base.MoveBaseState(),
                     remapping={'x':'goal_position_1_x',
                                'y':'goal_position_1_y',
                                'yaw':'goal_position_1_yaw'
                                },
                     transitions={'aborted':'MOVE_BASE_RETURN'}
                     )

        # wait
        Sequence.add('PAUSE_AT_GOAL_1', util.SleepState(5))

        # nav to goal 2
        Sequence.add('MOVE_BASE_GO_2', move_base.MoveBaseState(),
                     remapping={'x':'goal_position_2_x',
                                'y':'goal_position_2_y',
                                'yaw':'goal_position_2_yaw'
                                },
                     transitions={'aborted':'MOVE_BASE_RETURN'}
                     )

        # wait
        Sequence.add('PAUSE_AT_GOAL_2', util.SleepState(5),
                     transitions={'succeeded':'MOVE_BASE_GO_1'}     # loop
                     )


        ## ending

        # nav back
        Sequence.add('MOVE_BASE_RETURN', move_base.MoveBaseState(),
                     remapping={'x':'saved_position_x',
                                'y':'saved_position_y',
                                'yaw':'saved_position_yaw'
                                }
                     )

    return sq



def main():
    rospy.init_node('smach')
    util.execute_smach_container(get_patrol_smach(), enable_introspection=True)


if __name__ == '__main__':
    main()

