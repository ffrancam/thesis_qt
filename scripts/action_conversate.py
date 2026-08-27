#!/usr/bin/env python3
import rospy
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue

from conversation import QTChatBot


class ConversateAction:

    NUM_TURNS = 2  # ← cambia qui quanti scambi vuoi

    def __init__(self):
        rospy.init_node('conversate_action_node')
        print("Conversate Action Node started!")

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

        print("Conversate Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'conversate':
            return

        print(f"\n=== Executing Action {msg.action_id} ({msg.name}) ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)
        self.execute()
        self.apply_effects()
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
        print(f"✓ Action {msg.action_id} completed!\n")

    # ------------------------------------------------------------------ #

    def execute(self):
        try:
            self.bot.finish = False
            self.bot.speak("Chiacchieriamo un po'! Dimmi pure qualcosa.")

            for turn in range(1, self.NUM_TURNS + 1):
                is_last = (turn == self.NUM_TURNS)
                print(f"In attesa del turno {turn}/{self.NUM_TURNS}...")

                transcript = None
                while not transcript:
                    transcript = self.bot.qt.listen("listening_icon")
                    if not transcript:
                        self.bot.bored()

                print(f"Human (Turno {turn}): {transcript}")

                if self.bot.sentiment_enabled:
                    self.bot.show_sentiment(self.bot.get_sentiment(transcript))

                self.bot.qt.ts.sync([
                    (0,   lambda t=transcript, last=is_last: self._generate_and_close(t, last)),
                    (0.5, lambda: self.bot.think()),
                ])

            print("Conversazione terminata.")

        except Exception as e:
            rospy.logerr(f"Conversate action failed: {e}")

    # ------------------------------------------------------------------ #

    def _generate_and_close(self, transcript, is_last):
        if is_last:
            # original_prompt = self.bot.aimodel.prompts[0]["content"]
            # self.bot.aimodel.prompts[0]["content"] = (
            #     original_prompt + " Non terminare mai la risposta con una domanda."
            # )
            closing_transcript = transcript + " [Rispondi senza fare domande alla fine.]"
            full_response = self.bot.aimodel.generate(closing_transcript)
            if full_response:
                full_response = self._strip_final_question(full_response)
                self.bot.speak(full_response, user_text=transcript)
            print("→ Dico la frase di chiusura")
            self.bot.speak("È stato bello chiacchierare, ma adesso è il momento di tornare a giocare!")
        else:
            full_response = self.bot.aimodel.generate(transcript)
            if full_response:
                self.bot.speak(full_response, user_text=transcript)

    # ------------------------------------------------------------------ #
    def _strip_final_question(self, text):
        """Rimuove l'ultima frase se termina con '?'"""
        from nltk.tokenize import sent_tokenize
        sentences = sent_tokenize(text)
        if sentences and sentences[-1].strip().endswith('?'):
            sentences = sentences[:-1]
        return ' '.join(sentences) if sentences else text

    def apply_effects(self):
        
        self._update_predicate(
            KnowledgeUpdateServiceRequest.REMOVE_KNOWLEDGE,
            'can_conversate', []
        )


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

    def _update_predicate(self, update_type, predicate_name, parameters):
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
        ConversateAction()
    except rospy.ROSInterruptException:
        pass