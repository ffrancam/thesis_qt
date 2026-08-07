#!/usr/bin/env python3
import rospy
import threading
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from conversation import QTChatBot


class TakeABreakAction:

    def __init__(self):
        rospy.init_node('take_a_break_action_node')
        print("Take A Break Action Node started!")

        self.bot = QTChatBot()

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

        print("Take A Break Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'take_a_break':
            return

        print(f"\n=== Executing Action {msg.action_id} ({msg.name}) ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        threading.Thread(
            target=self._take_a_break_logic,
            args=(msg.action_id,),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #

    def _take_a_break_logic(self, action_id):
        try:
            self.execute()
            self.apply_effects()
        except Exception as e:
            rospy.logerr(f"Take a break action failed: {e}")
        self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
        print(f"✓ Action {action_id} completed!\n")

    # ------------------------------------------------------------------ #

    def execute(self):
        self.bot.qt.ts.sync([
            (0, lambda: self.bot.qt.emotionShow('QT/tired')),
            (0, lambda: self.bot.qt.gesturePlay('QT/emotions/tired', 1.0)),
        ])
        self.bot.qt.talkText(
            "Sai cosa? Facciamo una piccola pausa!"
        )
        print("Take a break terminato.")

    # ------------------------------------------------------------------ #

    def apply_effects(self):
        self._update_predicate(
            KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
            'can_conversate', []
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
        TakeABreakAction()
    except rospy.ROSInterruptException:
        pass