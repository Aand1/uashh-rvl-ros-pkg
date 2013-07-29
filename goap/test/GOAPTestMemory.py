'''
Created on Jul 5, 2013

@author: felix
'''
import unittest

from goap.goap import *
from goap.inheriting import *
from goap.planning import Planner, Node, PlanExecutor


#@unittest.skip
class TestSimple(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.worldstate = WorldState()

        self.memory.set_value('memory.counter', 0)

        print self.memory

        Condition._conditions_dict.clear()

        Condition.add('memory.counter', MemoryCondition(self.memory, 'counter'))

        Condition.initialize_worldstate(self.worldstate)

        print Condition.print_dict()

        self.actionbag = ActionBag()
        self.actionbag.add(MemoryChangeVarAction(self.memory, 'counter', 2, 3))
        self.actionbag.add(MemoryChangeVarAction(self.memory, 'counter', 0, 1))
        self.actionbag.add(MemoryChangeVarAction(self.memory, 'counter', 1, 2))
        self.actionbag.add(MemoryChangeVarAction(self.memory, 'counter', -2, 3))

        print self.actionbag

        self.goal = Goal([Precondition(Condition.get('memory.counter'), 3)])

        self.goal_inaccessible = Goal([Precondition(Condition.get('memory.counter'), 4)])

        print self.worldstate


    def testGoals(self):
        print '==', self.testGoals.__name__
        self.assertFalse(self.goal.is_valid(self.worldstate), 'Goal should not be valid yet')

    def testPlannerPos(self):
        print '==', self.testPlannerPos.__name__
        planner = Planner(self.actionbag, self.worldstate, self.goal)
        start_node = planner.plan()
        print 'start_node found: ', start_node
        self.assertIsNotNone(start_node, 'There should be a plan')
        self.assertIsInstance(start_node, Node, 'Plan should be a Node')
        self.assertEqual(len(start_node.parent_actions_path_list), 3, 'Start Node should have three actions')
        self.assertEqual(len(start_node.parent_nodes_path_list), 3, 'Start Node should have three parent nodes')

        PlanExecutor().execute(start_node)


    def testPlannerNeg(self):
        print '==', self.testPlannerNeg.__name__
        planner = Planner(self.actionbag, self.worldstate, self.goal_inaccessible)
        start_node = planner.plan()
        print 'start_node found: ', start_node
        self.assertIsNone(start_node, 'There should be no plan')


    def tearDown(self):
        print 'memory was:', self.memory


#@unittest.skip
class TestIncrementer(unittest.TestCase):

    def setUp(self):
        self.memory = Memory()
        self.worldstate = WorldState()

        self.memory.set_value('memory.counter', 0)

        print self.memory

        Condition._conditions_dict.clear()

        Condition.add('memory.counter', MemoryCondition(self.memory, 'counter'))

        Condition.initialize_worldstate(self.worldstate)

        self.actionbag = ActionBag()
        self.actionbag.add(MemoryIncrementerAction(self.memory, 'counter'))

        print Condition.print_dict()

        print self.actionbag

        self.goal = Goal([Precondition(Condition.get('memory.counter'), 3)])

        self.goal_inaccessible = Goal([Precondition(Condition.get('memory.counter'), -2)])

        print self.worldstate


    def testGoals(self):
        print '==', self.testGoals.__name__
        self.assertFalse(self.goal.is_valid(self.worldstate), 'Goal should not be valid yet')

    def testPlannerPos(self):
        print '==', self.testPlannerPos.__name__
        planner = Planner(self.actionbag, self.worldstate, self.goal)
        start_node = planner.plan()
        print 'start_node found: ', start_node
        self.assertIsNotNone(start_node, 'There should be a plan')
        self.assertIsInstance(start_node, Node, 'Plan should be a Node')
        self.assertEqual(len(start_node.parent_actions_path_list), 3, 'Plan should have three actions')


    def testPlannerPosUnneededCondition(self):
        Condition.add('memory.unneeded', MemoryCondition(self.memory, 'unneeded'))
        Condition.initialize_worldstate(self.worldstate)
        print 'reinitialized worldstate with unneeded condition: ', self.worldstate
        self.testPlannerPos()


    def testPlannerNeg(self):
        print '==', self.testPlannerNeg.__name__
        planner = Planner(self.actionbag, self.worldstate, self.goal_inaccessible)
        start_node = planner.plan()
        print 'start_node found: ', start_node
        self.assertIsNone(start_node, 'There should be no plan')

    def testPlannerNegPos(self):
        """Atm this happens to fail easily as the planner randomly follows up and down actions.
        action benefits needed..
        """
        print '==', self.testPlannerPos.__name__
        self.actionbag.add(MemoryIncrementerAction(self.memory, 'counter', -4))
        planner = Planner(self.actionbag, self.worldstate, self.goal_inaccessible)
        start_node = planner.plan()
        print 'start_node found: ', start_node
        self.assertIsNotNone(start_node, 'There should be a plan')
        self.assertIsInstance(start_node, Node, 'Plan should be a Node')
        self.assertEqual(len(start_node.parent_actions_path_list), 3, 'Plan should have three actions')


    def tearDown(self):
        print 'memory was:', self.memory



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
