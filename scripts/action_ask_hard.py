#!/usr/bin/env python3
import random
import threading
import rospy
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_dispatch_msgs.srv import DispatchService
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from std_srvs.srv import Empty
from qt_api import QTRobot
from thesis_qt.srv import EvaluateResponse


class AskHardAction:

    QUESTIONS = {
        'q1':  {"question": "Qual è il fiume più lungo del mondo?",                          "correct_answer": ""},
        'q2':  {"question": "Quanti pianeti ci sono nel sistema solare?",                    "correct_answer": ""},
        'q3':  {"question": "Qual è il continente più grande della Terra?",                  "correct_answer": ""},
        'q4':  {"question": "In quale città si trova la Torre Eiffel?",                      "correct_answer": ""},
        'q5':  {"question": "In quale continente si trova il Giappone?",                     "correct_answer": ""},
        'q6':  {"question": "Qual è il monte più alto del mondo?",                           "correct_answer": ""},
        'q7':  {"question": "Chi ha scritto Pinocchio?",                                     "correct_answer": ""},
        'q8':  {"question": "Chi ha dipinto la Gioconda?",                                   "correct_answer": ""},
        'q9':  {"question": "Cosa usano i pesci per respirare sott'acqua?",                  "correct_answer": ""},
        'q10': {"question": "Qual è il colore che si ottiene mescolando tutti i colori?",    "correct_answer": ""},
        'q11': {"question": "Quanti giorni formano un anno?",                                "correct_answer": ""},
        'q12': {"question": "Qual è l'unico mammifero che sa volare?",                       "correct_answer": ""},
        'q13': {"question": "Qual è l'animale più veloce del mondo?",                        "correct_answer": ""},
        'q14': {"question": "Da quale pianta si ricava l'olio che usiamo per cucinare?",     "correct_answer": ""},
        'q15': {"question": "Tutti lo possono aprire, ma nessuno lo sa chiudere. Cos'è?",   "correct_answer": ""},
        'q16': {"question": "Ha i denti, ma non morde mai. Cos'è?",                          "correct_answer": ""},
    }

    MAX_ATTEMPTS = 2

    def __init__(self):
        rospy.init_node('ask_hard_action_node')
        print("Ask Hard Action Node started!")

        self.asked_questions = set()

        rospy.Subscriber('/rosplan_plan_dispatcher/action_dispatch',
                         ActionDispatch, self.action_callback)

        self.feedback_pub = rospy.Publisher('/rosplan_plan_dispatcher/action_feedback',
                                            ActionFeedback, queue_size=10)

        services = [
            '/rosplan_knowledge_base/update',
            '/rosplan_knowledge_base/state/functions',
            '/rosplan_knowledge_base/state/goals',
            '/rosplan_problem_interface/problem_generation_server',
            '/rosplan_planner_interface/planning_server',
            '/rosplan_parsing_interface/parse_plan',
            '/rosplan_plan_dispatcher/cancel_dispatch',
            '/rosplan_plan_dispatcher/dispatch_plan',
            '/response_evaluator',
        ]
        for s in services:
            rospy.wait_for_service(s)

        self.update_kb         = rospy.ServiceProxy('/rosplan_knowledge_base/update', KnowledgeUpdateService)
        self.get_functions     = rospy.ServiceProxy('/rosplan_knowledge_base/state/functions', GetAttributeService)
        self.get_goals         = rospy.ServiceProxy('/rosplan_knowledge_base/state/goals', GetAttributeService)
        self.generate_problem  = rospy.ServiceProxy('/rosplan_problem_interface/problem_generation_server', Empty)
        self.plan              = rospy.ServiceProxy('/rosplan_planner_interface/planning_server', Empty)
        self.parse_plan_srv    = rospy.ServiceProxy('/rosplan_parsing_interface/parse_plan', Empty)
        self.cancel_dispatch   = rospy.ServiceProxy('/rosplan_plan_dispatcher/cancel_dispatch', Empty)
        self.dispatch_plan     = rospy.ServiceProxy('/rosplan_plan_dispatcher/dispatch_plan', DispatchService)
        self.evaluate_response = rospy.ServiceProxy('/response_evaluator', EvaluateResponse)

        self.qt = QTRobot()

        print("Ask Hard Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def pick_question(self):
        available = [k for k in self.QUESTIONS if k not in self.asked_questions]
        if not available:
            rospy.logwarn("Tutte le domande sono già state fatte! Resetto il pool.")
            self.asked_questions.clear()
            available = list(self.QUESTIONS.keys())
        return random.choice(available)

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'ask_hard':
            return

        question = self.pick_question()
        print(f"\n=== Executing Action {msg.action_id} ({msg.name} → {question}) ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        threading.Thread(
            target=self._ask_hard_logic,
            args=(msg.action_id, question),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #

    def _ask_hard_logic(self, action_id, question):
        success = self.execute(question)

        self.apply_effects(question, answered_correctly=success)

        if not success:
            current_goals = self.get_goals('').attributes
            self.send_feedback(action_id, ActionFeedback.ACTION_FAILED)
            print(f"~ Action {action_id} completed (wrong answer).\n")
            self.cancel_dispatch()
            threading.Thread(
                target=self._execute_replan,
                args=(current_goals,),
                daemon=True
            ).start()
        else:
            self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
            print(f"✓ Action {action_id} completed!\n")

    # ------------------------------------------------------------------ #

    def execute(self, question):
        try:
            if question not in self.QUESTIONS:
                rospy.logerr(f"Unknown question instance: {question}")
                return False

            q_text = self.QUESTIONS[question]["question"]
            correct_answer = self.QUESTIONS[question]["correct_answer"]

            # self.qt.ts.sync([
            #     (0, lambda: self.qt.emotionShow('QT/happy')),
            #     (0, lambda: self.qt.talkText(q_text))
            # ])
            self.qt.talkText(q_text)
            #print(f"QT talking: '{q_text}'")
            rospy.loginfo(f"QT talking: '{q_text}'")

            attempt = 0
            while attempt < self.MAX_ATTEMPTS:
                rospy.loginfo(f"In ascolto (tentativo {attempt + 1}/{self.MAX_ATTEMPTS})...")

                transcript = self.qt.listen("listening_icon")

                if not transcript:
                    self.qt.talkText("Non ho sentito nulla, puoi ripetere?")
                    continue

                self.qt.user_res_pub.publish(transcript)
                print(f"Umano ha detto: '{transcript}'")

                if self.qt.check_repeat_request(transcript):
                    self.qt.ts.sync([
                        (0, lambda: self.qt.emotionShow('QT/happy')),
                        (0, lambda: self.qt.talkText(q_text))
                    ])
                    continue

                attempt += 1
                is_last = (attempt == self.MAX_ATTEMPTS)

                result = self.evaluate_response(
                    question=q_text,
                    correct_answer=correct_answer,
                    description='',
                    user_res=transcript,
                    is_last_attempt=is_last
                )

                if result.is_correct:
                    self.qt.ts.sync([
                        (0, lambda: self.qt.emotionShow('QT/happy')),
                        (0, lambda: self.qt.talkText(result.robot_feedback))
                    ])
                    return True
                else:
                    self.qt.ts.sync([
                        (0, lambda: self.qt.emotionShow('QT/sad')),
                        (0, lambda: self.qt.talkText(result.robot_feedback))
                    ])

            return False

        except rospy.ServiceException as e:
            rospy.logerr(f"Service call failed: {e}")
            return False

    # ------------------------------------------------------------------ #

    def apply_effects(self, question, answered_correctly: bool):
        self.asked_questions.add(question)

        current_n = self._get_function('n_questions')
        self._update_function('n_questions', [], current_n + 1)

        current_hard = self._get_function('n_hard')
        self._update_function('n_hard', [], current_hard + 1)

        current_uses = self._get_function('ask_uses')
        self._update_function('ask_uses', [], current_uses + 1)

        if answered_correctly:
            current_right = self._get_function('right_answers')
            self._update_function('right_answers', [], current_right + 1)
            self._update_predicate(
                KnowledgeUpdateServiceRequest.REMOVE_KNOWLEDGE,
                'answered_wrong', []
            )
            self._update_predicate(
                KnowledgeUpdateServiceRequest.REMOVE_KNOWLEDGE,
                'emotion_checked', []
            )
        else:
            current_wrong = self._get_function('wrong_answers')
            self._update_function('wrong_answers', [], current_wrong + 1)
            self._update_predicate(
                KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
                'answered_wrong', []
            )

        numeric_effects = {
            'robot_e':    3.44,  'robot_p':    2.93,  'robot_a':    0.92,
            'robot_e_sq': 11.8336, 'robot_p_sq': 8.5849, 'robot_a_sq': 0.8464,
            'human_e':    3.44,  'human_p':    2.93,  'human_a':    0.92,
            'human_e_sq': 11.8336, 'human_p_sq': 8.5849, 'human_a_sq': 0.8464,
        }
        for fluent_name, value in numeric_effects.items():
            self._update_function(fluent_name, [], value)

    # ------------------------------------------------------------------ #

    def _execute_replan(self, current_goals):
        try:
            rospy.sleep(1.0)
            self._restore_goals(current_goals)
            print("\n=== STARTING REPLAN (wrong answer) ===")
            self.generate_problem()
            rospy.sleep(0.5)
            self._patch_problem_metric()
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
        problem_path = rospack.get_path('thesis_qt') + '/pddl/problem_try.pddl'
        with open(problem_path, 'r') as f:
            content = f.read()

        if '(:metric minimize (total-cost))' in content:
            print("✓ Metric already present.")
            return

        # Rimuove eventuali (:metric ...) già presenti ma errati
        import re
        content = re.sub(r'\(:metric[^)]*\)', '', content)

        content = content.rstrip().rstrip(')')
        content += '\n(:metric minimize (total-cost))\n)\n'
        with open(problem_path, 'w') as f:
            f.write(content)
        print("✓ Metric patched in problem file.")

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

    # ------------------------------------------------------------------ #

    def _get_function(self, function_name):
        try:
            response = self.get_functions(function_name)
            for item in response.attributes:
                if item.attribute_name == function_name:
                    return item.function_value
        except rospy.ServiceException as e:
            rospy.logerr(f"Failed to get function '{function_name}': {e}")
        return 0.0

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
            rospy.logerr(f"KB update failed for predicate '{predicate_name}': {e}")

    def _update_function(self, function_name, parameters, value):
        req = KnowledgeUpdateServiceRequest()
        req.update_type = KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE
        item = KnowledgeItem()
        item.knowledge_type = KnowledgeItem.FUNCTION
        item.attribute_name = function_name
        item.values = [KeyValue(key=k, value=v) for k, v in parameters]
        item.function_value = float(value)
        req.knowledge = item
        try:
            self.update_kb(req)
            rospy.loginfo(f"KB: Set function '{function_name}' = {value}")
        except rospy.ServiceException as e:
            rospy.logerr(f"KB update failed for function '{function_name}': {e}")

    def send_feedback(self, action_id, status):
        feedback = ActionFeedback()
        feedback.action_id = action_id
        feedback.status = status
        self.feedback_pub.publish(feedback)


if __name__ == '__main__':
    try:
        AskHardAction()
    except rospy.ROSInterruptException:
        pass