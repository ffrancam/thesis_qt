#!/usr/bin/env python3
import rospy
import threading
from std_msgs.msg import String
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_dispatch_msgs.srv import DispatchService
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from std_srvs.srv import Empty
from qt_api import QTRobot
from thesis_qt.srv import SentimentAnalyzer


class CheckEmotionAction:

    # Costo base di ogni azione nel PDDL.
    # medium > easy, hard > medium perché sono più impegnative.
    BASE_COEFFICIENTS = {
        'ask_easy':     1.0,
        'ask_medium':   1.1,
        'ask_hard':     1.2,
        'mime_easy':    1.0,
        'mime_medium':  1.1,
        'mime_hard':    1.2,
        'sound_easy':   1.0,
        'sound_medium': 1.1,
        'sound_hard':   1.2,
        'image_easy':   1.0,
        'image_medium': 1.1,
        'image_hard':   1.2,
    }

    # Moltiplicatore di penalità: scoraggia tutte le difficoltà della stessa categoria
    CATEGORY_PENALTY = 5.0

    def __init__(self):
        rospy.init_node('check_emotion_action_node')

        self.counter = 1
        self.last_action = None
        self.action_id_to_name = {}
        self.last_user_response = ""
        self.last_emotion_label = "N"

        # Modalità manuale: se True, l'etichetta dell'emozione viene letta da tastiera
        self.manual_emotion = rospy.get_param('~manual_emotion', False)
        if self.manual_emotion:
            rospy.logwarn("[CheckEmotion] Manual emotion mode ENABLED — emotion labels will be read from keyboard.")

        self.qt = QTRobot()

        rospy.Subscriber('/rosplan_plan_dispatcher/action_dispatch',
                         ActionDispatch, self.action_callback)
        rospy.Subscriber('/rosplan_plan_dispatcher/action_feedback',
                         ActionFeedback, self.feedback_callback)
        rospy.Subscriber('/qt_robot/user_response',
                         String, self.user_response_callback)
        rospy.Subscriber('/emotion/analysis',
                         String, self.emotion_callback)

        self.feedback_pub = rospy.Publisher('/rosplan_plan_dispatcher/action_feedback',
                                            ActionFeedback, queue_size=10)

        print("Waiting for ROSPlan services...")
        services = [
            '/rosplan_knowledge_base/update',
            '/rosplan_knowledge_base/state/functions',
            '/rosplan_knowledge_base/state/propositions',
            '/rosplan_knowledge_base/state/goals',
            '/rosplan_problem_interface/problem_generation_server',
            '/rosplan_planner_interface/planning_server',
            '/rosplan_parsing_interface/parse_plan',
            '/rosplan_plan_dispatcher/cancel_dispatch',
            '/rosplan_plan_dispatcher/dispatch_plan',
            '/sentiment_analyzer',
        ]
        for s in services:
            rospy.wait_for_service(s)

        self.update_kb        = rospy.ServiceProxy('/rosplan_knowledge_base/update', KnowledgeUpdateService)
        self.get_functions    = rospy.ServiceProxy('/rosplan_knowledge_base/state/functions', GetAttributeService)
        self.get_goals        = rospy.ServiceProxy('/rosplan_knowledge_base/state/goals', GetAttributeService)
        self.get_propositions = rospy.ServiceProxy('/rosplan_knowledge_base/state/propositions', GetAttributeService)
        self.generate_problem = rospy.ServiceProxy('/rosplan_problem_interface/problem_generation_server', Empty)
        self.plan             = rospy.ServiceProxy('/rosplan_planner_interface/planning_server', Empty)
        self.parse_plan       = rospy.ServiceProxy('/rosplan_parsing_interface/parse_plan', Empty)
        self.cancel_dispatch  = rospy.ServiceProxy('/rosplan_plan_dispatcher/cancel_dispatch', Empty)
        self.dispatch_plan    = rospy.ServiceProxy('/rosplan_plan_dispatcher/dispatch_plan', DispatchService)
        self.sentiment_analyzer = rospy.ServiceProxy('/sentiment_analyzer', SentimentAnalyzer)

        print("✓ Check Emotion Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #
    #  CALLBACKS                                                           #
    # ------------------------------------------------------------------ #

    def emotion_callback(self, msg):
        if msg.data:
            self.last_emotion_label = msg.data

    def user_response_callback(self, msg):
        if msg.data:
            self.last_user_response = msg.data
            print(f"[CheckEmotion] User response saved: '{self.last_user_response}'")

    def action_callback(self, msg):
        self.action_id_to_name[msg.action_id] = msg.name

        if msg.name != 'check_emotion':
            return

        transcript    = self.last_user_response
        self.last_user_response = ""
        emotion_label = self._get_emotion_label()

        threading.Thread(
            target=self._check_emotion_logic,
            args=(msg.action_id, transcript, emotion_label),
            daemon=True
        ).start()

    def feedback_callback(self, msg):
        if msg.status == ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE:
            name = self.action_id_to_name.get(msg.action_id)
            if name:
                self.last_action = name
                print(f"✓ Last completed action updated: {self.last_action}")

    # ------------------------------------------------------------------ #
    #  EMOTION LABEL                                                       #
    # ------------------------------------------------------------------ #

    def _get_emotion_label(self):
        """
        Restituisce l'etichetta dell'emozione corrente.
        Se manual_emotion=True, la legge da tastiera (stdin).
        Altrimenti usa il valore più recente da MorphCast.
        """
        if self.manual_emotion:
            print("\n[CheckEmotion] Manual mode: inserisci l'etichetta emozione (es. Joy, Anger, Fear, Sadness, N): ", end='', flush=True)
            label = input().strip()
            print(f"[CheckEmotion] Emozione manuale ricevuta: '{label}'")
            return label if label else "N"
        return self.last_emotion_label

    # ------------------------------------------------------------------ #
    #  LOGICA PRINCIPALE                                                   #
    # ------------------------------------------------------------------ #

    def _check_emotion_logic(self, action_id, transcript, emotion_label):
        print(f"\n=== Executing check_emotion (action_id={action_id}) ===")
        print(f"    Last completed action : {self.last_action}")
        print(f"    Emotion label         : {emotion_label}")
        self.send_feedback(action_id, ActionFeedback.ACTION_ENABLED)

        # Caso 1: ultima azione era introduce_game → skip
        # if self.last_action == 'introduce_game':
        #     print("[CheckEmotion] Last action was 'introduce_game', skipping emotion check.")
        #     self.apply_effects()
        #     self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
        #     print(f"✓ Action {action_id} completed (skipped)!\n")
        #     return

        # Caso 2: nessuna emozione disponibile
        if not emotion_label or emotion_label == "N" or emotion_label == "SU" or emotion_label == "H":
            print("[CheckEmotion] No emotion available, applying effects only.")
            #self._update_coefficients_based_on_last()
            self.apply_effects()
            self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
            print(f"✓ Action {action_id} completed (no emotion)!\n")
            return

        # Caso 3: emozione disponibile → confronta con target KB
        target_e = self.get_function_value('human_e')
        target_p = self.get_function_value('human_p')
        target_a = self.get_function_value('human_a')
        print(f"    Target KB → E={target_e}, P={target_p}, A={target_a}")

        success, epa, epa_squared = self.qt.get_emotion(emotion_label)
        if not success:
            print(f"[CheckEmotion] Label '{emotion_label}' non riconosciuta, applico solo effetti.")
            self.apply_effects()
            self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
            print(f"✓ Action {action_id} completed (unknown label)!\n")
            return

        sent_e, sent_p, sent_a = epa[0], epa[1], epa[2]
        print(f"    Emotion EPA → E={sent_e}, P={sent_p}, A={sent_a}")

        tol = 1e-6
        match = (
            abs(sent_e - target_e) < tol and
            abs(sent_p - target_p) < tol and
            abs(sent_a - target_a) < tol
        )

        if match:
            print("✓ EPA match! Proceeding normally.")
            self.apply_effects()
            self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
            print(f"✓ Action {action_id} completed!\n")
        else:
            print("⚠ EPA mismatch! Triggering replan...")
            self._update_function('human_e',    sent_e)
            self._update_function('human_p',    sent_p)
            self._update_function('human_a',    sent_a)
            self._update_function('human_e_sq', sent_e ** 2)
            self._update_function('human_p_sq', sent_p ** 2)
            self._update_function('human_a_sq', sent_a ** 2)

            current_goals = self.get_goals('').attributes
            self.send_feedback(action_id, ActionFeedback.ACTION_FAILED)
            self.cancel_dispatch()
            threading.Thread(
                target=self.execute_replan_thread,
                args=(current_goals,),
                daemon=True
            ).start()

    # ------------------------------------------------------------------ #
    #  AGGIORNAMENTO COEFFICIENTI PER AZIONE                              #
    # ------------------------------------------------------------------ #

    def _update_coefficients_based_on_last(self):
        """
        Penalizza solo la categoria dell'ultima azione (es. 'image'),
        lasciando che n_easy/n_medium/n_hard gestiscano la progressione di difficoltà.
        """

        # 1. Reset completo ai valori base
        for action_name, base_val in self.BASE_COEFFICIENTS.items():
            coeff_fluent = action_name + '_coeff'
            self._update_function(coeff_fluent, base_val)
            print(f"   Reset {coeff_fluent} = {base_val}")

        if self.last_action not in self.BASE_COEFFICIENTS:
            print(f"   [Coefficients] last_action='{self.last_action}' non è un'azione di gioco, nessuna penalità applicata.")
            return

        # 2. Estrai la categoria (es. 'image' da 'image_easy')
        for suffix in ('_easy', '_medium', '_hard'):
            if self.last_action.endswith(suffix):
                category = self.last_action[:-len(suffix)]
                break
        else:
            print(f"   [Coefficients] Impossibile estrarre categoria da '{self.last_action}'.")
            return

        # 3. Penalizza tutte le difficoltà della stessa categoria
        for diff in ('easy', 'medium', 'hard'):
            coeff_name = f"{category}_{diff}_coeff"
            base_val   = self.BASE_COEFFICIENTS[f"{category}_{diff}"]
            penalized  = base_val * self.CATEGORY_PENALTY
            self._update_function(coeff_name, penalized)
            print(f"⚠ Category penalty: {coeff_name} → {penalized}")

    # ------------------------------------------------------------------ #
    #  REPLAN                                                              #
    # ------------------------------------------------------------------ #

    def execute_replan_thread(self, current_goals):
        try:
            rospy.sleep(1.0)

            # Salva i contatori PRIMA che generate_problem li sovrascriva
            n_easy      = self.get_function_value('n_easy')
            n_medium    = self.get_function_value('n_medium')
            n_hard      = self.get_function_value('n_hard')
            n_questions = self.get_function_value('n_questions')
            print(f"[Replan] Saved counters: n_easy={n_easy}, n_medium={n_medium}, n_hard={n_hard}, n_questions={n_questions}")

            self._update_coefficients_based_on_last()
            self._update_predicate(
                KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
                'emotion_checked', []
            )
            print("Restoring goals...")
            self._restore_goals(current_goals)

            # Ripristina i contatori
            self._update_function('n_easy',      n_easy)
            self._update_function('n_medium',    n_medium)
            self._update_function('n_hard',      n_hard)
            self._update_function('n_questions', n_questions)
            print(f"✓ Restored counters: n_easy={n_easy}, n_medium={n_medium}, n_hard={n_hard}, n_questions={n_questions}")

            print("\n=== STARTING REPLAN SEQUENCE ===")
            self.generate_problem()
            rospy.sleep(0.5)
            self._patch_problem_metric()
            self.plan()
            rospy.sleep(0.5)
            self.parse_plan()
            rospy.sleep(0.5)
            print("Dispatching new plan...")
            self.dispatch_plan()
            print("✓ Replanning completed!")
        except Exception as e:
            rospy.logerr(f"✗ Replanning failed: {e}")
            import traceback
            traceback.print_exc()

    # ------------------------------------------------------------------ #
    #  HELPERS                                                             #
    # ------------------------------------------------------------------ #

    def apply_effects(self):
        print(">>> apply_effects chiamata!")
        self._update_predicate(
            KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
            'emotion_checked', []
        )
        props = self.get_propositions('')
        print(f">>> propositions dopo apply_effects: {[a.attribute_name for a in props.attributes]}")

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

    def _remove_predicate(self, predicate_name, parameters=[]):
        req = KnowledgeUpdateServiceRequest()
        req.update_type = KnowledgeUpdateServiceRequest.REMOVE_KNOWLEDGE
        item = KnowledgeItem()
        item.knowledge_type = KnowledgeItem.FACT
        item.attribute_name = predicate_name
        item.values = [KeyValue(key=k, value=v) for k, v in parameters]
        item.is_negative = False
        req.knowledge = item
        try:
            self.update_kb(req)
            rospy.loginfo(f"KB: Removed predicate '{predicate_name}'")
        except rospy.ServiceException as e:
            rospy.logerr(f"KB remove failed for '{predicate_name}': {e}")

    def _update_function(self, function_name, value):
        req = KnowledgeUpdateServiceRequest()
        req.update_type = KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE
        item = KnowledgeItem()
        item.knowledge_type = KnowledgeItem.FUNCTION
        item.attribute_name = function_name
        item.values = []
        item.function_value = float(value)
        req.knowledge = item
        try:
            self.update_kb(req)
            rospy.loginfo(f"KB: Set function '{function_name}' = {value}")
        except rospy.ServiceException as e:
            rospy.logerr(f"KB update failed for function '{function_name}': {e}")

    def get_function_value(self, function_name):
        try:
            res = self.get_functions(function_name)
            for attr in res.attributes:
                if attr.attribute_name == function_name:
                    return attr.function_value
        except rospy.ServiceException as e:
            rospy.logerr(f"Failed to get function '{function_name}': {e}")
        return 0.0

    def send_feedback(self, action_id, status):
        feedback = ActionFeedback()
        feedback.action_id = action_id
        feedback.status = status
        self.feedback_pub.publish(feedback)


if __name__ == '__main__':
    try:
        CheckEmotionAction()
    except rospy.ROSInterruptException:
        pass