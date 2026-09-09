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
from engines.openai import OpenAI
from thesis_qt.srv import EvaluateResponse


class ImageHardAction:

    # (question_text, sound, correct_answer, description)
    QUESTIONS = {
        'q1':  ("africa",      "Guarda questa mappa. Come si chiama il continente evidenziato?",   "Africa", ""),
        'q2':  ("calamita",      "Questo pezzo di metallo riesce ad attirare altri pezzi di metallo senza toccarli. Che oggetto è?",     "una calamita / un magnete", ""),
        'q3':  ("ombra",    "Guarda attentamente l'ombra dell'albero. Il sole di trova a destra o a sinistra?",             "sinistra", "l'immagine mostra un albero con l'ombra a destra"),
        'q4':  ("impronte_cavallo",   "Sai dirmi di chi sono queste impronte?",   "di un cavallo", "l'immagine mostra delle impronte di un cavallo sulla neve"),
        'q5':  ("images",      "Guarda attentamente. C'è qualcosa che non torna: perchè il faro è a testa in giù?",    "perchè è il riflesso nell'acqua", "l'immagine mostra una pozzanghera con un faro riflesso"),
        'q6':  ("orologio",    "Sai dirmi che ore sono?", "11:55 / le 12 meno 5", "l'immagine mostra un orologio con le lancette che segnano le 11:55"),
        'q7':  ("pala_eolica",      "Cosa producono queste grandi pale girando?",    "energia / energia eolica", "l'immagine mostra delle pale eoliche"),
        'q8':  ("piramidi", "Questi enormi monumenti a punta di trovano nel deserto. Sai dirmi come si chiamano?",    "piramidi", "l'immagine mostra delle piramidi"),
        'q9':  ("pizza",      "Guarda questa pizza tagliata. Quante fette mancano per fare una pizaa intera?",    "due", "l'immagine mostra una pizza con 4 fette su 6"),
        'q10': ("owl",      "Guarda questo uccello. Quale 'superpotere' incredibile ha il suo collo?",    "può girare la testa quasi del tutto / può guardare dietro di sé con il collo", "viene mostrato un gufo"),
        'q11': ("torre_pisa",      "Questa torre è famosissima in tutto il mondo perchè è storta! Sai dirmi in quale città italiana si trova?",    "Pisa", "l'immagine mostra la Torre di Pisa"),
        'q12': ("baobab",      "Sai dirmi che albero è questo?",            "un baobab", "")
    }

    MAX_ATTEMPTS = 2

    def __init__(self):
        rospy.init_node('image_hard_action_node')
        print("Image Hard Action Node started!")

        self.shown_images = set()

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

        print("Image Hard Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def pick_image(self):
        available = [k for k in self.QUESTIONS if k not in self.shown_images]
        if not available:
            rospy.logwarn("Tutte le immagini sono già state mostrate! Resetto il pool.")
            self.shown_images.clear()
            available = list(self.QUESTIONS.keys())
        return random.choice(available)

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'image_hard':
            return

        image = self.pick_image()
        print(f"\n=== Executing Action {msg.action_id} ({msg.name} → {image}) ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        threading.Thread(
            target=self._image_hard_logic,
            args=(msg.action_id, image),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #

    def _image_hard_logic(self, action_id, image):
        success = self.execute(image)

        self.apply_effects(image, answered_correctly=success)

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

    def execute(self, image):
        try:
            if image not in self.QUESTIONS:
                rospy.logerr(f"Unknown image instance: {image}")
                return False

            filename, q_text, answer, description = self.QUESTIONS[image]

            self.qt.talkText(q_text)
            print(f"QT talking: '{q_text}'")

            attempt = 0
            while attempt < self.MAX_ATTEMPTS:
                self.qt.show_image(filename + "_icon")
                rospy.loginfo(f"In ascolto (tentativo {attempt + 1}/{self.MAX_ATTEMPTS})...")

                transcript = self.qt.listen()

                if not transcript:
                    self.qt.talkText("Non ho sentito nulla, puoi ripetere?")
                    continue

                self.qt.user_res_pub.publish(transcript)
                print(f"Umano ha detto: '{transcript}'")

                if self.qt.check_repeat_request(transcript):
                    self.qt.talkText(q_text)
                    self.qt.show_image(filename + "_icon")
                    continue

                attempt += 1
                is_last = (attempt == self.MAX_ATTEMPTS)

                result = self.evaluate_response(
                    question=q_text,
                    correct_answer=answer,
                    description=description,
                    user_res=transcript,
                    is_last_attempt=is_last
                )

                self.qt.hide_image()
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

    def apply_effects(self, image, answered_correctly: bool):
        self.shown_images.add(image)

        current_n = self._get_function('n_questions')
        self._update_function('n_questions', [], current_n + 1)

        current_hard = self._get_function('n_hard')
        self._update_function('n_hard', [], current_hard + 1)

        current_uses = self._get_function('image_uses')
        self._update_function('image_uses', [], current_uses + 1)

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
            rospy.logerr(f"KB update failed for '{predicate_name}': {e}")

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
        ImageHardAction()
    except rospy.ROSInterruptException:
        pass