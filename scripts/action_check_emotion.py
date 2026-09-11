#!/usr/bin/env python3
"""
check_emotion_action.py — Integrazione completa con emoACT

Flusso ad ogni check_emotion:
  1. Invia emozione facciale utente a emoACT /navel_perception (porta 4000)
  2. Invia frase utente a emoACT /sentence_analysis (porta 4000), se disponibile
  3. Invia azione robot a emoACT /robot_action (porta 4000)
  4. Attende (polling) che emoACT ricalcoli l'emozione del robot
  5. Confronta EPA robot (emoACT) vs target KB → replan se mismatch
     (skip se label robot è N, SU, H)
  6. Confronta EPA umano (MorphCast) vs target KB → replan se mismatch
     (skip se label umano è N, SU, H)

emoACT deve girare con due processi:
  - Emotion_GenerationACT.py   (porta 3000)
  - Impression_EstimatorACT.py (porta 4000)
"""

import rospy
import threading
import time
import requests
import numpy as np

from std_msgs.msg import String
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_dispatch_msgs.srv import DispatchService
from rosplan_knowledge_msgs.srv import (
    KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
)
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from std_srvs.srv import Empty
from qt_api import QTRobot
from thesis_qt.srv import SentimentAnalyzer


# ---------------------------------------------------------------------------
# Costanti emoACT
# ---------------------------------------------------------------------------
EMOACT_EMOTION_GEN_URL = "http://192.168.1.3:3000"
EMOACT_IMPRESSION_URL  = "http://192.168.1.3:4000"   # Impression_EstimatorACT
EMOACT_TIMEOUT         = 2.0   # secondi per ogni chiamata REST
EMOACT_POLL_ATTEMPTS   = 6     # tentativi polling emozione robot
EMOACT_POLL_DELAY      = 0.8   # secondi tra un tentativo e l'altro

# Label per cui NON si triggera il replan (emozione non significativa)
SKIP_LABELS = {"N", "SU", "H"}

# Azioni di gioco che si aspettano una risposta verbale dall'utente
ACTIONS_EXPECTING_RESPONSE = {
    'ask_easy', 'ask_medium', 'ask_hard',
    'mime_easy', 'mime_medium', 'mime_hard',
    'sound_easy', 'sound_medium', 'sound_hard',
    'image_easy', 'image_medium', 'image_hard',
}

# Mappa azioni PDDL → (categoria, chiave) in emotion_behaviours.json
# categoria 'robot_behaviour' → self=False (robot agisce verso utente)
# categoria 'self_regulation' → self=True  (robot agisce su sé stesso)
# None → skip silenzioso
ACTION_TO_EMOACT_BEHAVIOUR = {
    # Azioni di gioco
    'ask_easy':          ('robot_behaviour', 'ask_question'),
    'ask_medium':        ('robot_behaviour', 'ask_question'),
    'ask_hard':          ('robot_behaviour', 'ask_question'),
    'mime_easy':         ('robot_behaviour', 'ask_question'),
    'mime_medium':       ('robot_behaviour', 'ask_question'),
    'mime_hard':         ('robot_behaviour', 'ask_question'),
    'sound_easy':        ('robot_behaviour', 'ask_question'),
    'sound_medium':      ('robot_behaviour', 'ask_question'),
    'sound_hard':        ('robot_behaviour', 'ask_question'),
    'image_easy':        ('robot_behaviour', 'ask_question'),
    'image_medium':      ('robot_behaviour', 'ask_question'),
    'image_hard':        ('robot_behaviour', 'ask_question'),
    # Gestione interazione
    'greet_warmly':      ('robot_behaviour', 'greet'),
    'say_goodbye':       ('robot_behaviour', 'say_goodbye'),
    'introduce_game':    ('robot_behaviour', 'introduce_quiz'),   # EPA vuoto → skip
    'conclude_game':     ('robot_behaviour', 'conclude_quiz'),    # EPA vuoto → skip
    'conversate':        ('robot_behaviour', 'converse'),
    # Regolazione robot → human
    'comfort':           ('robot_behaviour', 'comfort'),
    'take_a_break':      ('robot_behaviour', 'take_a_break'),
    'spark_curiosity':   ('robot_behaviour', 'spark_curiosity'),
    'tell_a_joke':       ('robot_behaviour', 'tell_a_joke'),
    'raise_stakes':      ('robot_behaviour', 'raise_stakes'),
    # Auto-regolazione robot → robot
    'calm_down':         ('self_regulation', 'calm_dowm'),        # typo dal JSON
    'ask_for_help':      ('self_regulation', 'ask_for_help'),
    'show_vulnerability':('self_regulation', 'show_vulnerability'),
    'reset_emotion':     ('self_regulation', 'reset_to_neutral'),
    # check_emotion non va notificato
    'check_emotion':     None,
}

# Mappa label MorphCast → label emoACT
MORPHCAST_TO_EMOACT = {
    'Joy':     'H',  'Happy':   'H',  'H':  'H',
    'Anger':   'A',  'Angry':   'A',  'A':  'A',
    'Fear':    'F',                   'F':  'F',
    'Sadness': 'SA', 'Sad':     'SA', 'SA': 'SA',
    'Surprise':'SU',                  'SU': 'SU',
    'Disgust': 'D',                   'D':  'D',
    'Neutral': 'N',                   'N':  'N',
    'Bored':   'B',  'Boredom': 'B',  'B':  'B',
}


class CheckEmotionAction:

    BASE_COEFFICIENTS = {
        'ask_easy':     1.0, 'ask_medium':   1.1, 'ask_hard':     1.2,
        'mime_easy':    1.0, 'mime_medium':  1.1, 'mime_hard':    1.2,
        'sound_easy':   1.0, 'sound_medium': 1.1, 'sound_hard':   1.2,
        'image_easy':   1.0, 'image_medium': 1.1, 'image_hard':   1.2,
    }
    CATEGORY_PENALTY = 10.0

    def __init__(self):
        rospy.init_node('check_emotion_action_node')

        self.counter = 1
        self.last_action = None
        self.action_id_to_name = {}
        self.last_user_response = ""
        self.last_emotion_label = "N"

        self.manual_emotion = rospy.get_param('~manual_emotion', False)
        if self.manual_emotion:
            rospy.logwarn("[CheckEmotion] Manual emotion mode ENABLED.")

        self.qt = QTRobot()

        rospy.Subscriber('/rosplan_plan_dispatcher/action_dispatch',
                         ActionDispatch, self.action_callback)
        rospy.Subscriber('/rosplan_plan_dispatcher/action_feedback',
                         ActionFeedback, self.feedback_callback)
        rospy.Subscriber('/qt_robot/user_response',
                         String, self.user_response_callback)
        rospy.Subscriber('/emotion/analysis',
                         String, self.emotion_callback)

        self.feedback_pub = rospy.Publisher(
            '/rosplan_plan_dispatcher/action_feedback', ActionFeedback, queue_size=10)

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
        transcript = self.last_user_response
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
                VALID_CATEGORIES = ('ask', 'mime', 'sound', 'image')
                for suffix in ('_easy', '_medium', '_hard'):
                    if name.endswith(suffix):
                        category = name[:-len(suffix)]
                        if category in VALID_CATEGORIES:
                            rospy.set_param('/last_game_action', name)
                        break

    # ------------------------------------------------------------------ #
    #  EMOTION LABEL (utente)                                             #
    # ------------------------------------------------------------------ #

    def _get_emotion_label(self):
        if self.manual_emotion:
            print("\n[CheckEmotion] Inserisci emozione (H, F, A, SA, SU, D, N, B): ",
                  end='', flush=True)
            label = input().strip().upper()
            return label if label else "N"
        return self.last_emotion_label

    # ------------------------------------------------------------------ #
    #  LOGICA PRINCIPALE                                                   #
    # ------------------------------------------------------------------ #

    def _check_emotion_logic(self, action_id, transcript, emotion_label):
        print(f"\n=== Executing check_emotion (action_id={action_id}) ===")
        print(f"    Last completed action : {self.last_action}")
        print(f"    Emotion label (human) : {emotion_label}")
        self.send_feedback(action_id, ActionFeedback.ACTION_ENABLED)

        # ------------------------------------------------------------------
        # Invia tutti i dati disponibili a emoACT
        # ------------------------------------------------------------------

        # PUlizia
        self._reset_emoact_flag()
        # 1a. Emozione utente → modifica identità utente in emoACT
        self._send_perception_to_emoact(emotion_label)

        # 1b. Frase utente → GPT inferisce comportamento verbale
        if transcript:
            self._send_sentence_to_emoact(transcript)
        elif self.last_action in ACTIONS_EXPECTING_RESPONSE:
            rospy.logwarn("[CheckEmotion] Nessuna risposta utente, invio segnale neutro a emoACT.")
            self._send_sentence_to_emoact("Ok.")

        # 1c. Azione robot → aggiorna impressione lato robot
        if self.last_action:
            self._notify_emoact_robot_action(self.last_action)

        # ------------------------------------------------------------------
        # Aspetta che emoACT ricalcoli l'emozione del robot
        # ------------------------------------------------------------------
        robot_label, robot_epa = self._poll_robot_emotion()

        # ------------------------------------------------------------------
        # Confronto EPA robot (emoACT) vs target KB
        # ------------------------------------------------------------------
        if robot_label is not None and robot_label not in SKIP_LABELS:
            target_re = self.get_function_value('robot_e')
            target_rp = self.get_function_value('robot_p')
            target_ra = self.get_function_value('robot_a')
            print(f"    Target KB robot → E={target_re}, P={target_rp}, A={target_ra}")
            print(f"    emoACT robot    → label={robot_label}, "
                  f"E={robot_epa[0]:.2f}, P={robot_epa[1]:.2f}, A={robot_epa[2]:.2f}")

            tol = 1e-6
            robot_match = (
                abs(robot_epa[0] - target_re) < tol and
                abs(robot_epa[1] - target_rp) < tol and
                abs(robot_epa[2] - target_ra) < tol
            )

            if robot_match:
                print("✓ Robot EPA match!")
            else:
                print("⚠ Robot EPA mismatch! Triggering replan...")
                self._update_function('robot_e',    robot_epa[0])
                self._update_function('robot_p',    robot_epa[1])
                self._update_function('robot_a',    robot_epa[2])
                self._update_function('robot_e_sq', robot_epa[0] ** 2)
                self._update_function('robot_p_sq', robot_epa[1] ** 2)
                self._update_function('robot_a_sq', robot_epa[2] ** 2)

                current_goals = self.get_goals('').attributes
                self.send_feedback(action_id, ActionFeedback.ACTION_FAILED)
                self.cancel_dispatch()
                threading.Thread(
                    target=self.execute_replan_thread,
                    args=(current_goals,),
                    daemon=True
                ).start()
                return  # replan avviato, esci
        else:
            print(f"[CheckEmotion] Robot label '{robot_label}' → skip confronto robot EPA.")

        # ------------------------------------------------------------------
        #  Confronto EPA umano vs target KB
        # ------------------------------------------------------------------
        if not emotion_label or emotion_label in SKIP_LABELS:
            print(f"[CheckEmotion] Human label '{emotion_label}' → skip confronto umano EPA.")
            self.apply_effects()
            self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
            print(f"✓ Action {action_id} completed (no emotion)!\n")
            return

        target_e = self.get_function_value('human_e')
        target_p = self.get_function_value('human_p')
        target_a = self.get_function_value('human_a')
        print(f"    Target KB human → E={target_e}, P={target_p}, A={target_a}")

        success, epa, _ = self.qt.get_emotion(emotion_label)
        if not success:
            print(f"[CheckEmotion] Label '{emotion_label}' non riconosciuta, applico solo effetti.")
            self.apply_effects()
            self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
            return

        sent_e, sent_p, sent_a = epa[0], epa[1], epa[2]
        print(f"    MorphCast human → label={emotion_label}, "
              f"E={sent_e:.2f}, P={sent_p:.2f}, A={sent_a:.2f}")

        tol = 1e-6
        human_match = (
            abs(sent_e - target_e) < tol and
            abs(sent_p - target_p) < tol and
            abs(sent_a - target_a) < tol
        )

        if human_match:
            print("✓ Human EPA match! Proceeding normally.")
            self.apply_effects()
            self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
            print(f"✓ Action {action_id} completed!\n")
        else:
            print("⚠ Human EPA mismatch! Triggering replan...")
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
    #  emoACT — INVIO PERCEZIONE FACCIALE                                 #
    # ------------------------------------------------------------------ #

    def _send_perception_to_emoact(self, emotion_label: str):

        emoact_label = MORPHCAST_TO_EMOACT.get(emotion_label, 'N')
        try:
            resp = requests.post(
                f"{EMOACT_IMPRESSION_URL}/navel_perception",
                json={
                    "emotion":   emoact_label,
                    "attention": "positive",  # utente guarda il robot
                    "proximity": 500          # ~50cm in mm
                },
                timeout=EMOACT_TIMEOUT
            )
            print(f"[emoACT] /navel_perception → emotion={emoact_label}, "
                  f"status={resp.status_code}")
        except Exception as e:
            rospy.logwarn(f"[emoACT] /navel_perception non raggiungibile: {e}")

    # ------------------------------------------------------------------ #
    #  emoACT — INVIO SENTENCE                                            #
    # ------------------------------------------------------------------ #

    def _send_sentence_to_emoact(self, sentence: str):

        try:
            resp = requests.post(
                f"{EMOACT_IMPRESSION_URL}/sentence_analysis",
                json={"sentence": sentence},
                timeout=EMOACT_TIMEOUT
            )
            print(f"[emoACT] /sentence_analysis → status {resp.status_code} | "
                  f"'{sentence[:60]}{'...' if len(sentence) > 60 else ''}'")
        except Exception as e:
            rospy.logwarn(f"[emoACT] /sentence_analysis non raggiungibile: {e}")

    # ------------------------------------------------------------------ #
    #  emoACT — NOTIFICA AZIONE ROBOT                                     #
    # ------------------------------------------------------------------ #

    def _notify_emoact_robot_action(self, action_name: str):

        mapping = ACTION_TO_EMOACT_BEHAVIOUR.get(action_name)
        if mapping is None:
            rospy.loginfo(f"[emoACT] '{action_name}' non mappata, skip.")
            return

        category, behaviour_key = mapping

        if behaviour_key in ('conclude_quiz'):
            rospy.loginfo(f"[emoACT] '{behaviour_key}' senza EPA, skip.")
            return

        is_self = (category == 'self_regulation')
        try:
            resp = requests.post(
                f"{EMOACT_IMPRESSION_URL}/robot_action",
                json={"action": behaviour_key, "self": is_self},
                timeout=EMOACT_TIMEOUT
            )
            print(f"[emoACT] /robot_action → '{behaviour_key}' "
                  f"(self={is_self}), status={resp.status_code}")
        except Exception as e:
            rospy.logwarn(f"[emoACT] /robot_action non raggiungibile: {e}")


    def _reset_emoact_flag(self):
        try:
            requests.get(
                f"{EMOACT_EMOTION_GEN_URL}/emotional_state",
                timeout=EMOACT_TIMEOUT
            )
            print("[emoACT] Flag new_emo resettato (lettura a vuoto).")
        except Exception as e:
            rospy.logwarn(f"[emoACT] Reset flag fallito: {e}")

    # ------------------------------------------------------------------ #
    #  emoACT — POLLING EMOZIONE ROBOT                                    #
    # ------------------------------------------------------------------ #

    def _poll_robot_emotion(self):

        for attempt in range(1, EMOACT_POLL_ATTEMPTS + 1):
            try:
                resp = requests.get(
                    f"{EMOACT_EMOTION_GEN_URL}/emotional_state",
                    timeout=EMOACT_TIMEOUT
                )
                data = resp.json()
                label = data.get("emotion_label", "N")
                epa   = data.get("emotion", [0.0, 0.0, 0.0])
                new   = data.get("new_emotion", False)
                print(f"[emoACT] Poll {attempt}/{EMOACT_POLL_ATTEMPTS} → "
                      f"new={new}, label={label}, EPA={[round(v, 2) for v in epa]}")
                if new:
                    return label, epa
            except Exception as e:
                rospy.logwarn(f"[emoACT] /emotional_state tentativo {attempt} fallito: {e}")
            time.sleep(EMOACT_POLL_DELAY)

        rospy.logwarn("[emoACT] Timeout polling — nessuna nuova emozione robot.")
        return None, None

    # ------------------------------------------------------------------ #
    #  AGGIORNAMENTO COEFFICIENTI                                          #
    # ------------------------------------------------------------------ #

    def _update_coefficients_based_on_last(self):
        for action_name, base_val in self.BASE_COEFFICIENTS.items():
            self._update_function(action_name + '_coeff', base_val)
            print(f"   Reset {action_name}_coeff = {base_val}")

        if self.last_action not in self.BASE_COEFFICIENTS:
            print(f"   [Coefficients] '{self.last_action}' non è azione di gioco, skip penalità.")
            return

        for suffix in ('_easy', '_medium', '_hard'):
            if self.last_action.endswith(suffix):
                category = self.last_action[:-len(suffix)]
                break
        else:
            return

        for diff in ('easy', 'medium', 'hard'):
            coeff_name = f"{category}_{diff}_coeff"
            penalized  = self.BASE_COEFFICIENTS[f"{category}_{diff}"] * self.CATEGORY_PENALTY
            self._update_function(coeff_name, penalized)
            print(f"⚠ Category penalty: {coeff_name} → {penalized}")

    # ------------------------------------------------------------------ #
    #  REPLAN                                                              #
    # ------------------------------------------------------------------ #

    def execute_replan_thread(self, current_goals):
        try:
            rospy.sleep(1.0)

            n_easy      = self.get_function_value('n_easy')
            n_medium    = self.get_function_value('n_medium')
            n_hard      = self.get_function_value('n_hard')
            n_questions = self.get_function_value('n_questions')
            print(f"[Replan] Saved counters: easy={n_easy}, medium={n_medium}, "
                  f"hard={n_hard}, questions={n_questions}")

            self._update_coefficients_based_on_last()
            self._update_predicate(KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
                                   'emotion_checked', [])
            self._restore_goals(current_goals)

            self._update_function('n_easy',      n_easy)
            self._update_function('n_medium',    n_medium)
            self._update_function('n_hard',      n_hard)
            self._update_function('n_questions', n_questions)
            print(f"✓ Restored counters.")

            print("\n=== STARTING REPLAN SEQUENCE ===")
            self.generate_problem()
            rospy.sleep(0.5)
            self._patch_problem_metric()
            self.plan()
            rospy.sleep(0.5)
            self.parse_plan()
            rospy.sleep(0.5)
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
        self._update_predicate(KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
                               'emotion_checked', [])
        props = self.get_propositions('')
        print(f">>> propositions: {[a.attribute_name for a in props.attributes]}")

    def _patch_problem_metric(self):
        import rospkg, re
        rospack = rospkg.RosPack()
        problem_path = rospack.get_path('thesis_qt') + '/pddl/problem_try.pddl'
        with open(problem_path, 'r') as f:
            content = f.read()
        if '(:metric minimize (total-cost))' in content:
            return
        content = re.sub(r'\(:metric[^)]*\)', '', content)
        content = content.rstrip().rstrip(')')
        content += '\n(:metric minimize (total-cost))\n)\n'
        with open(problem_path, 'w') as f:
            f.write(content)
        print("✓ Metric patched.")

    def _restore_goals(self, goals):
        for goal in self.get_goals('').attributes:
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
        except rospy.ServiceException as e:
            rospy.logerr(f"KB update failed for '{predicate_name}': {e}")

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
            rospy.loginfo(f"KB: '{function_name}' = {value}")
        except rospy.ServiceException as e:
            rospy.logerr(f"KB update failed for '{function_name}': {e}")

    def get_function_value(self, function_name):
        try:
            res = self.get_functions(function_name)
            for attr in res.attributes:
                if attr.attribute_name == function_name:
                    return attr.function_value
        except rospy.ServiceException as e:
            rospy.logerr(f"Failed to get '{function_name}': {e}")
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