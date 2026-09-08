#!/usr/bin/env python3
import rospy
import threading
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from conversation import QTChatBot


class RaiseStakesAction:

    def __init__(self):
        rospy.init_node('raise_stakes_action_node')
        print("Raise Stakes Action Node started!")

        self.bot = QTChatBot()
        self._already_called = False  # flag: azione già eseguita in precedenza

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

        print("Raise Stakes Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'raise_stakes':
            return

        print(f"\n=== Executing Action {msg.action_id} ({msg.name}) ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        threading.Thread(
            target=self._raise_stakes_logic,
            args=(msg.action_id,),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #

    def _raise_stakes_logic(self, action_id):
        if self._already_called:
            print("⚠ raise_stakes già eseguita: termino il piano.")
            self._goodbye()
            self.send_feedback(action_id, ActionFeedback.ACTION_FAILED)
            print(f"✗ Action {action_id} failed (already called)!\n")
            return

        try:
            self.execute()
        except Exception as e:
            rospy.logerr(f"Raise stakes action failed: {e}")

        self._already_called = True
        self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
        print(f"✓ Action {action_id} completed!\n")
        self.apply_effects()

    # ------------------------------------------------------------------ #

    def execute(self):
        self.bot.qt.ts.sync([
            (0, lambda: self.bot.qt.emotionShow('QT/one_eye_wink')),
            (0, lambda: self.bot.qt.gesturePlay('QT/challenge', 1.0)),
        ])
        
        self.bot.qt.talkText(
            "Bene bene bene! Sei proprio bravo... "
            "allora è ora di alzare un po' la difficoltà!"
        )
        rospy.sleep(0.5)
        self.bot.qt.emotionShow('QT/brushing_teeth')
        self.bot.qt.talkText(
            "Preparati, le prossime domande saranno più difficili!"
        )
        print("Raise stakes terminato.")

    # ------------------------------------------------------------------ #

    def _goodbye(self):
        """Il robot ci rimane male e saluta quando il piano non può continuare."""
        self.bot.qt.ts.sync([
            (0, lambda: self.bot.qt.emotionShow('QT/sad')),
            (0, lambda: self.bot.qt.gesturePlay('QT/emotions/sad', 1.0)),
        ])
        self.bot.qt.talkText(
            "Oh... sembra che abbiamo già fatto tutto quello che potevamo insieme. "
            "Mi dispiace un po', mi stavo divertendo! "
            "Grazie per aver giocato con me. A presto!"
        )
        self.bot.qt.ts.sync([
            (0, lambda: self.bot.qt.emotionShow('QT/goodbye')),
            (0, lambda: self.bot.qt.gesturePlay('QT/bye', 1.0)),
        ])

    # ------------------------------------------------------------------ #

    def apply_effects(self):
        self._update_predicate(
            KnowledgeUpdateServiceRequest.REMOVE_KNOWLEDGE,
            'emotion_checked', []
        )
        numeric_effects = {
            'robot_e':    3.44,
            'robot_p':    2.93,
            'robot_a':    0.92,
            'robot_e_sq': 11.8336,
            'robot_p_sq': 8.5849,
            'robot_a_sq': 0.8464,
            'human_e':    3.44,
            'human_p':    2.93,
            'human_a':    0.92,
            'human_e_sq': 11.8336,
            'human_p_sq': 8.5849,
            'human_a_sq': 0.8464,
            'n_easy':     3.0,
            'n_hard':     3.0,
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
        RaiseStakesAction()
    except rospy.ROSInterruptException:
        pass