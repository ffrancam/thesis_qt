#!/usr/bin/env python3
import rospy
import threading
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from conversation import QTChatBot


BREAK_CONVERSATION_SYSTEM_PROMPT = (
    "Sei QT, un robot amichevole che parla in italiano con un bambino durante una pausa dal gioco fatta pechè lui è arrabbiato. "
    "Hai già annunciato la pausa e non devi ripeterlo. "
    "Il tuo obiettivo è fare una breve conversazione naturale e rilassata per far riposare il bambino "
    "e mantenere un rapporto positivo prima di riprendere il gioco. "
    "\n\n"
    "REGOLE IMPORTANTI:"
    "\n- Ascolta attentamente ciò che dice il bambino."
    "\n- Rispondi PRIMA a ciò che ha detto: mostra interesse, commenta, riconosci o fai un breve collegamento."
    "\n- Non ignorare mai il contenuto della risposta del bambino."
    "\n- Fai al massimo UNA domanda per risposta."
    "\n- La domanda deve essere collegata, quando possibile, a ciò che il bambino ha appena detto."
    "\n- Non fare domande casuali non collegate alla conversazione."
    "\n- Se il bambino dà una risposta breve o generica, puoi fare una domanda semplice e leggera."
    "\n- Non menzionare il gioco durante questi turni."
    "\n- Rispondi in massimo 2 frasi."
    "\n- Usa un tono caldo, rilassato e naturale."
)


class TakeABreakAction:

    NUM_TURNS = 3

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
            self._break_conversation()
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
            "Sai cosa? Facciamo una piccola pausa! Cosa stai combinando di bello ultimamente?"
        )
        print("Annuncio pausa terminato.")

    # ------------------------------------------------------------------ #

    def _break_conversation(self):
        original_prompt = None
        try:
            original_prompt = self.bot.aimodel.prompts[0]["content"]
            self.bot.aimodel.prompts[0]["content"] = BREAK_CONVERSATION_SYSTEM_PROMPT
            self.bot.aimodel.prompts = [self.bot.aimodel.prompts[0]]

            for turn in range(1, self.NUM_TURNS + 1):
                is_last = (turn == self.NUM_TURNS)
                print(f"Break conversation — turno {turn}/{self.NUM_TURNS}")

                transcript = None
                while not transcript:
                    transcript = self.bot.qt.listen("listening_icon")
                    if not transcript:
                        self.bot.bored()

                print(f"Human (turno {turn}): {transcript}")

                if is_last:
                    closing_transcript = (
                        transcript +
                        " [Rispondi senza fare domande. "
                        "Concludi con entusiasmo dicendo che la pausa è finita "
                        "e che è ora di tornare a giocare insieme.]"
                    )
                    response = self.bot.aimodel.generate(closing_transcript)
                else:
                    response = self.bot.aimodel.generate(transcript)

                if response:
                    self.bot.speak(response)

        except Exception as e:
            rospy.logerr(f"_break_conversation failed: {e}")
        finally:
            if original_prompt is not None:
                try:
                    self.bot.aimodel.prompts[0]["content"] = original_prompt
                    self.bot.aimodel.prompts = [self.bot.aimodel.prompts[0]]
                    print("✓ System prompt ripristinato")
                except Exception as e:
                    rospy.logwarn(f"Non riesco a ripristinare il system prompt: {e}")

    # ------------------------------------------------------------------ #

    def apply_effects(self):

        self._update_predicate(REMOVE_KNOWLEDGE, 'emotion_checked', [])
        
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