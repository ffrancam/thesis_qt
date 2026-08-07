#!/usr/bin/env python3
import rospy
import threading
import asyncio
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from conversation import QTChatBot


SPARK_CURIOSITY_SYSTEM_PROMPT = """Sei QT, un robot amico dei bambini.
Devi raccontare UNA sola curiosità breve, divertente e sorprendente, adatta a bambini.
La curiosità deve essere un fatto reale e interessante sul mondo naturale, gli animali, lo spazio o la scienza.
Non fare domande, il bambino non deve risponderti.
Rispondi SOLO con la curiosità, senza introduzioni o commenti aggiuntivi.
Rispondi in italiano."""


class SparkCuriosityAction:

    def __init__(self):
        rospy.init_node('spark_curiosity_action_node')
        print("Spark Curiosity Action Node started!")

        self.bot = QTChatBot()
        self._original_prompt = None

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

        print("Spark Curiosity Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'spark_curiosity':
            return

        print(f"\n=== Executing Action {msg.action_id} ({msg.name}) ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        threading.Thread(
            target=self._spark_curiosity_logic,
            args=(msg.action_id,),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #

    def _spark_curiosity_logic(self, action_id):
        self._set_custom_prompt()
        try:
            self.execute()
        finally:
            self._restore_prompt()
        self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
        print(f"✓ Action {action_id} completed!\n")
        self.apply_effects()

    # ------------------------------------------------------------------ #

    def _set_custom_prompt(self):
        try:
            self._original_prompt = self.bot.aimodel.prompts[0]["content"]
            self.bot.aimodel.prompts[0]["content"] = SPARK_CURIOSITY_SYSTEM_PROMPT
            print("✓ System prompt sostituito per spark_curiosity")
        except (AttributeError, IndexError, KeyError) as e:
            rospy.logwarn(f"Non riesco a sovrascrivere il system prompt: {e}")

    def _restore_prompt(self):
        try:
            if self._original_prompt is not None:
                self.bot.aimodel.prompts[0]["content"] = self._original_prompt
                print("✓ System prompt ripristinato")
        except (AttributeError, IndexError, KeyError) as e:
            rospy.logwarn(f"Non riesco a ripristinare il system prompt: {e}")

    # ------------------------------------------------------------------ #

    def execute(self):
        try:
            # Fase 1: annuncio con curiosità
            self.bot.qt.ts.sync([
                (0, lambda: self.bot.qt.emotionShow('QT/excited')),
                (0, lambda: self.bot.qt.gesturePlay('QT/emotions/excited', 1.0)),
            ])
            self.bot.qt.talkText("Aspetta, ti voglio raccontare una cosa fantastica!")
            #rospy.sleep(0.5)

            # Fase 2: genera la curiosità
            curiosity = self._generate_curiosity()
            print(f"QT (curiosità): {curiosity}")

            # Fase 3: racconta la curiosità
            self.bot.qt.talkText(curiosity)

            # Fase 4: reazione finale
            #rospy.sleep(0.5)
            self.bot.qt.ts.sync([
                (0, lambda: self.bot.qt.emotionShow('QT/showing_smile')),
                (0, lambda: self.bot.qt.gesturePlay('QT/clapping', 1.0)),
            ])
            self.bot.qt.talkText("Il mondo è pieno di cose meravigliose!")
            self.bot.qt.talkText("Adesso possiamo continuare a giocare insieme!")

            print("Spark curiosity terminato.")

        except Exception as e:
            rospy.logerr(f"Spark curiosity action failed: {e}")

    # ------------------------------------------------------------------ #

    def _generate_curiosity(self):
        result = {"curiosity": None}

        def _generate():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result["curiosity"] = self.bot.aimodel.generate(
                    "Dimmi una curiosità sorprendente adatta a un bambino."
                )
            finally:
                loop.close()

        gen_thread = threading.Thread(target=_generate, daemon=True)
        gen_thread.start()
        self.bot.think()
        gen_thread.join()

        return result["curiosity"] or (
            "Lo sapevi che le api comunicano tra loro ballando? "
            "Quando trovano un fiore, tornano all'alveare e fanno una danza speciale "
            "per indicare alle altre api dove si trova! Incredibile!"
        )

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
        SparkCuriosityAction()
    except rospy.ROSInterruptException:
        pass