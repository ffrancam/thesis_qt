#!/usr/bin/env python3
import rospy
import threading
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from qt_api import QTRobot


class ResetToNeutralAction:

    def __init__(self):
        rospy.init_node('reset_to_neutral_action_node')
        print("Reset To Neutral Action Node started!")

        rospy.Subscriber('/rosplan_plan_dispatcher/action_dispatch',
                         ActionDispatch, self.action_callback)

        self.feedback_pub = rospy.Publisher('/rosplan_plan_dispatcher/action_feedback',
                                            ActionFeedback, queue_size=10)

        rospy.wait_for_service('/rosplan_knowledge_base/update')
        self.update_kb = rospy.ServiceProxy('/rosplan_knowledge_base/update',
                                            KnowledgeUpdateService)

        rospy.wait_for_service('/rosplan_knowledge_base/state/functions')
        self.get_functions = rospy.ServiceProxy('/rosplan_knowledge_base/state/functions',
                                                GetAttributeService)

        self.qt = QTRobot()

        print("Reset To Neutral Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'reset_to_neutral':
            return

        print(f"\n=== Executing Action {msg.action_id} ({msg.name}) ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        threading.Thread(
            target=self._reset_logic,
            args=(msg.action_id,),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #

    def _reset_logic(self, action_id):
        self.execute()
        self.apply_effects()
        self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
        print(f"✓ Action {action_id} completed!\n")

    # ------------------------------------------------------------------ #

    def execute(self):
        try:
            # Fase 1: riconosce lo stato negativo e vuole cambiarlo
            self.qt.ts.sync([
                (0, lambda: self.qt.emotionShow('QT/confused')),
                (0, lambda: self.qt.gesturePlay('QT/touch-head', 1.0)),
            ])
            self.qt.talkText("Hmm... aspetta un momento. Devo raccogliere i miei pensieri.")

            rospy.sleep(1.5)

            # Fase 2: si "scuote" e si riallinea — stretching come reset fisico
            self.qt.ts.sync([
                (0, lambda: self.qt.emotionShow('QT/neutral_state_blinking')),
                (0, lambda: self.qt.gesturePlay('QT/stretching', 1.0)),
            ])
            self.qt.talkText("Ok! Mi rimetto in carreggiata.")

            rospy.sleep(2.0)

            # Fase 3: torna sereno e pronto
            self.qt.ts.sync([
                (0, lambda: self.qt.emotionShow('QT/showing_smile')),
                (0, lambda: self.qt.gesturePlay('QT/emotions/calm', 1.0)),
            ])
            self.qt.talkText("Ecco fatto! Sono pronto a continuare. Andiamo!")

            rospy.sleep(1.0)

        except Exception as e:
            rospy.logerr(f"Reset to neutral action failed: {e}")

    # ------------------------------------------------------------------ #

    def apply_effects(self):
        # Rimuove emotion_checked
        self._update_predicate(
            KnowledgeUpdateServiceRequest.REMOVE_KNOWLEDGE,
            'emotion_checked', []
        )

        # Assegna i valori numerici neutri dal PDDL
        numeric_effects = {
            'robot_e':    0.58,
            'robot_p':    0.75,
            'robot_a':    0.56,
            'robot_e_sq': 0.3364,
            'robot_p_sq': 0.5625,
            'robot_a_sq': 0.3136,
        }
        for fluent_name, value in numeric_effects.items():
            self._update_function(fluent_name, [], value)

    # ------------------------------------------------------------------ #

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
            rospy.loginfo(f"KB: {action} predicate '{predicate_name}' {parameters}")
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
        ResetToNeutralAction()
    except rospy.ROSInterruptException:
        pass