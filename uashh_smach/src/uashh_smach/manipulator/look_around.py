#!/usr/bin/env python

""" This files generates POSES which let the robot look around to e.g. scan its environment.
These movements via move_arm.py are provided as a state machine container.
"""

import roslib; roslib.load_manifest('uashh_smach')

import rospy
import smach

import move_arm
import uashh_smach.util as util




### calculating lookaround poses

#POSE_DEFAULT = [0, 0, 0, 0, 0]
POSE_DEFAULT = [0, 0.5, 0.5, -2, 0]
POSES_LOOKAROUND_TURNINGS = [3, 2, 1, 0, -1, -2] # used for first joint
POSES_LOOKAROUND_TURNINGS_GLIMPSE = [1, -1]

POSES_LOOKAROUND = [ # without first joint!
                    [0.523, 1.309, -1.919, 0], # looking down
                    [0.523, 1.047, -1.745, 0], # a bit higher
                    [0.523, 0.689, -1.745, 0], # a bit below horizontally
                    [0.523, 0.444, -1.555, 0], # a bit above horizontally
                    [0.523, 0.444, -1.333, 0]  # a bit higher
                    ]


POSES = [POSE_DEFAULT]
for pose in POSES_LOOKAROUND:
    for turn in POSES_LOOKAROUND_TURNINGS:
        POSES.append([turn] + pose)
    POSES_LOOKAROUND_TURNINGS.reverse()
POSES.append(POSE_DEFAULT)


POSES_GLIMPSE = [POSE_DEFAULT]
POSES_GLIMPSE.extend([turn] + POSES_LOOKAROUND[2]
                    for turn in POSES_LOOKAROUND_TURNINGS_GLIMPSE)
POSES_GLIMPSE.append(POSE_DEFAULT)



def get_lookaround_smach(interjacent_state=None, glimpse=False):
    """if the interjacent state is not omitted it needs to have the
    outcome triple 'succeeded','aborted','preempted'.
    """
    sq = smach.Sequence(outcomes=['succeeded', 'aborted', 'preempted'],
                        connector_outcome='succeeded')

    _poses = POSES_GLIMPSE if glimpse else POSES

    with sq:
        for i in range(len(_poses)):
            sq.add('LOOKAROUND_MOVE_ARM_%d' % i,
                   move_arm.get_move_arm_to_joints_positions_state(_poses[i]))
            if interjacent_state is not None:
                sq.add('LOOKAROUND_INTERJACENT_STATE_%d' % i, interjacent_state)

    return sq




def _test_look_around():
    rospy.init_node('smach')

    print POSES
    print POSES_GLIMPSE

    sq = smach.Sequence(outcomes=['succeeded', 'aborted', 'preempted'],
                        connector_outcome='succeeded')

    with sq:
        smach.Sequence.add('LOOK_AROUND', get_lookaround_smach(util.SleepState(1)))
        smach.Sequence.add('GLIMPSE_AROUND', get_lookaround_smach(util.SleepState(1),
                                                                  glimpse=True))

    util.execute_smach_container(sq, enable_introspection=True)


if __name__ == '__main__':
    _test_look_around()