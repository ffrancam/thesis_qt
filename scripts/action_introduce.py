#!/usr/bin/env python3
import rospy
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_dispatch_msgs.srv import DispatchService
from rosplan_knowledge_msgs.srv import (
    KnowledgeUpdateService, KnowledgeUpdateServiceRequest,
    GetAttributeService
)
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from std_srvs.srv import Empty
from qt_api import QTRobot


class IntroduceAction:
    def __init__(self):
        rospy.init_node('introduce_action_node')
        print("Introduce Action Node started!")

        rospy.Subscriber('/rosplan_plan_dispatcher/action_dispatch',
                         ActionDispatch, self.action_callback)

        self.feedback_pub = rospy.Publisher('/rosplan_plan_dispatcher/action_feedback',
                                            ActionFeedback, queue_size=10)

        services = [
            '/rosplan_knowledge_base/update',
            '/rosplan_knowledge_base/state/goals',
            '/rosplan_problem_interface/problem_generation_server',
            '/rosplan_planner_interface/planning_server',
            '/rosplan_parsing_interface/parse_plan',
            '/rosplan_plan_dispatcher/cancel_dispatch',
            '/rosplan_plan_dispatcher/dispatch_plan',
        ]
        for s in services:
            rospy.wait_for_service(s)

        self.update_kb        = rospy.ServiceProxy('/rosplan_knowledge_base/update', KnowledgeUpdateService)
        self.get_goals        = rospy.ServiceProxy('/rosplan_knowledge_base/state/goals', GetAttributeService)
        self.generate_problem = rospy.ServiceProxy('/rosplan_problem_interface/problem_generation_server', Empty)
        self.plan             = rospy.ServiceProxy('/rosplan_planner_interface/planning_server', Empty)
        self.parse_plan_srv   = rospy.ServiceProxy('/rosplan_parsing_interface/parse_plan', Empty)
        self.cancel_dispatch  = rospy.ServiceProxy('/rosplan_plan_dispatcher/cancel_dispatch', Empty)
        self.dispatch_plan    = rospy.ServiceProxy('/rosplan_plan_dispatcher/dispatch_plan', DispatchService)

        self.qt = QTRobot()
        print("Introduce Action Interface ready!")
        rospy.spin()

    def action_callback(self, msg):
        if msg.name != 'introduce_game':
            return

        params = {kv.key: kv.value for kv in msg.parameters}
        print(f"\n=== Executing Action {msg.action_id} ===")

        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        success, user_said_no = self.execute()

        if success:
            self.apply_effects(user_said_no=user_said_no)
            if user_said_no:
                current_goals = self.get_goals('').attributes
                self.send_feedback(msg.action_id, ActionFeedback.ACTION_FAILED)
                print(f"✗ Action {msg.action_id} failed (user refused)!\n")
                self.cancel_dispatch()
                self._execute_replan(current_goals)
            else:
                self.send_feedback(msg.action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
                print(f"✓ Action {msg.action_id} completed!\n")
        else:
            self.apply_effects(user_said_no=True)
            current_goals = self.get_goals('').attributes
            self.send_feedback(msg.action_id, ActionFeedback.ACTION_FAILED)
            print(f"✗ Action {msg.action_id} failed!\n")
            self.cancel_dispatch()
            self._execute_replan(current_goals)

    def execute(self):
        try:
            self.qt.ts.sync([
                (0, lambda: self.qt.emotionShow('QT/happy')),
                (0, lambda: self.qt.talkText("Ti va di giocare a un gioco insieme?"))
            ])

            answer = 1
            # answer = None
            # for _ in range(2):
            #     transcript = self.qt.listen("listening_icon")
            #     answer = self.qt.check_yes_no(transcript)
            #     if answer is not None:
            #         break
            #     self.qt.talkText("Non ho capito, puoi rispondere sì o no?")

            if answer == 1:
                self.qt.ts.sync([
                    (0, lambda: self.qt.emotionShow('QT/happy')),
                    (0, lambda: self.qt.talkText(
                        "Perfetto! Ti farò delle domande e tu dovrai rispondere. Iniziamo!"
                    ))
                ])
                return True, False  # success, user_said_no=False

            else:
                self.qt.ts.sync([
                    (0, lambda: self.qt.emotionShow('QT/sad')),
                    (0, lambda: self.qt.talkText(
                        "Mi dispiace... capisco. Sono qui se cambi idea!"
                    ))
                ])
                return True, True  # success=True (eseguita), user_said_no=True

        except rospy.ServiceException as e:
            rospy.logerr(f"Service call failed: {e}")
            return False, False

    def apply_effects(self, user_said_no=False):
        self._update_predicate(
            KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
            'quiz_introduced', []
        )
        self._update_predicate(
            KnowledgeUpdateServiceRequest.REMOVE_KNOWLEDGE,
            'emotion_checked', []
        )
        if user_said_no:
            self._update_predicate(
                KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
                'can_conversate', []
            )

    def _execute_replan(self, current_goals):
        try:
            rospy.sleep(1.0)
            self._update_predicate(
                KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
                'emotion_checked', []
            )
            self._restore_goals(current_goals)
            print("\n=== STARTING REPLAN (user refused game) ===")
            self.generate_problem()
            rospy.sleep(0.5)
            self._patch_problem_metric()  # <---
            self.plan()
            rospy.sleep(0.5)
            self.parse_plan_srv()
            rospy.sleep(0.5)
            self.dispatch_plan()
            print("✓ Replanning completed!")
        except Exception as e:
            rospy.logerr(f"✗ Replanning failed: {e}")
            import traceback
            traceback.print_exc()

    def _patch_problem_metric(self):
        import rospkg
        rospack = rospkg.RosPack()
        problem_path = rospack.get_path('thesis_qt') + '/pddl/qt_test_problem.pddl'
        with open(problem_path, 'r') as f:
            content = f.read()
        if '(:metric' not in content:
            content = content.rstrip().rstrip(')')
            content += '\n(:metric minimize (total-cost))\n)\n'
            with open(problem_path, 'w') as f:
                f.write(content)
            print("✓ Metric patched in problem file.")
        else:
            print("✓ Metric already present.")

    def _restore_goals(self, goals):
        current = self.get_goals('').attributes
        for goal in current:
            req = KnowledgeUpdateServiceRequest()
            req.update_type = KnowledgeUpdateServiceRequest.REMOVE_GOAL
            req.knowledge = goal
            self.update_kb(req)
        for goal in goals:
            req = KnowledgeUpdateServiceRequest()
            req.update_type = KnowledgeUpdateServiceRequest.ADD_GOAL
            req.knowledge = goal
            self.update_kb(req)
        print(f"✓ Restored {len(goals)} goal(s)")

    def _update_predicate(self, update_type, predicate_name, parameters=[]):
        req = KnowledgeUpdateServiceRequest()
        req.update_type = update_type
        item = KnowledgeItem()
        item.knowledge_type = KnowledgeItem.FACT
        item.attribute_name = predicate_name
        item.values = [KeyValue(key=k, value=v) for k, v in parameters]
        item.is_negative = False
        req.knowledge = item
        try:
            self.update_kb(req)
            action = "Added" if update_type == KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE else "Removed"
            rospy.loginfo(f"KB: {action} predicate '{predicate_name}'")
        except rospy.ServiceException as e:
            rospy.logerr(f"KB update failed for '{predicate_name}': {e}")

    def send_feedback(self, action_id, status):
        feedback = ActionFeedback()
        feedback.action_id = action_id
        feedback.status = status
        self.feedback_pub.publish(feedback)


if __name__ == '__main__':
    try:
        IntroduceAction()
    except rospy.ROSInterruptException:
        pass