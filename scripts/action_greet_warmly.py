#!/usr/bin/env python3
import rospy
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from qt_api import QTRobot

class GreetWarmlyAction:
    def __init__(self):
        rospy.init_node('greet_warmly_action_node')
        print("Greet Warmly Action Node started!")

        self.feedback_pub = rospy.Publisher('/rosplan_plan_dispatcher/action_feedback',
                                            ActionFeedback, queue_size=10)

        rospy.wait_for_service('/rosplan_knowledge_base/update')
        self.update_kb = rospy.ServiceProxy('/rosplan_knowledge_base/update',
                                            KnowledgeUpdateService)
        self.qt = QTRobot()

        rospy.Subscriber('/rosplan_plan_dispatcher/action_dispatch',
                         ActionDispatch, self.action_callback)
                         
        print("Greet Warmly Action Interface ready!")
        rospy.spin()

    def action_callback(self, msg):
        if msg.name != 'greet_warmly':
            return

        params = {kv.key: kv.value for kv in msg.parameters}
        print(f"\n=== Executing Action {msg.action_id} ===")

        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        success = self.execute()

        if success:
            self.apply_effects()  # <--- AGGIORNA KB
            self.send_feedback(msg.action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
            print(f"✓ Action {msg.action_id} completed!\n")
        else:
            self.send_feedback(msg.action_id, ActionFeedback.ACTION_FAILED)
            print(f"✗ Action {msg.action_id} failed!\n")

    def apply_effects(self):
        """Applica gli effetti dell'azione greet_warmly alla Knowledge Base"""

        # --- PREDICATI ---

        # (interaction_started)  -> ADD
        self._update_predicate(
            KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
            'interaction_started', []
        )

        self._update_predicate(
            KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
            'emotion_checked', []
        )

        # (not (emotion_checked)) -> REMOVE
        # self._update_predicate(
        #     KnowledgeUpdateServiceRequest.REMOVE_KNOWLEDGE,
        #     'emotion_checked', []
        # )

        # --- FLUENTI NUMERICI ---
        # numeric_effects = {
        #     'robot_e':    3.44,
        #     'robot_p':    2.93,
        #     'robot_a':    0.92,
        #     'robot_e_sq': 11.8336,
        #     'robot_p_sq': 8.5849,
        #     'robot_a_sq': 0.8464,
        # }

        # for fluent_name, value in numeric_effects.items():
        #     self._update_function(fluent_name, [], value)

    def _update_predicate(self, update_type, predicate_name, parameters):
        """Aggiunge o rimuove un predicato dalla KB"""
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
        """Aggiorna un fluente numerico nella KB"""
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

    def execute(self):
        try:
            results = self.qt.ts.sync([
                (0, lambda: self.qt.emotionShow('QT/happy')),
                (0, lambda: self.qt.gesturePlay('QT/hi', 0)),
                (0, lambda: self.qt.talkText("Ciao, sono QT! Felice di conoscerti!"))
            ])
            return True
        except rospy.ServiceException as e:
            rospy.logerr(f"Service call failed: {e}")
            return False

    def send_feedback(self, action_id, status):
        feedback = ActionFeedback()
        feedback.action_id = action_id
        feedback.status = status
        self.feedback_pub.publish(feedback)


if __name__ == '__main__':
    try:
        GreetWarmlyAction()
    except rospy.ROSInterruptException:
        pass