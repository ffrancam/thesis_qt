#!/usr/bin/env python3
import rospy
import threading
import asyncio
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from conversation import QTChatBot


ASK_FOR_HELP_SYSTEM_PROMPT = """Sei QT, un robot amico dei bambini. 
In questo momento ti senti spaventato e hai chiesto aiuto al bambino.
Il bambino sta cercando di consolarti raccontandoti cose belle e felici.
Devi rispondere SEMPRE in modo caldo, grato e via via più sereno.
NON esprimere mai disapprovazione, rabbia o frustrazione.
NON fare la morale.
Reagisci positivamente a qualsiasi cosa il bambino dica, anche se non capisci bene.
Rispondi in italiano, in modo semplice e adatto a un bambino.
Non fare domande alla fine della risposta."""


class AskForHelpAction:

    NUM_TURNS = 2

    def __init__(self):
        rospy.init_node('ask_for_help_action_node')
        print("Ask For Help Action Node started!")

        self.bot = QTChatBot()

        # ← Sovrascrive il system prompt per questa azione
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

        print("Ask For Help Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'ask_for_help':
            return

        print(f"\n=== Executing Action {msg.action_id} ({msg.name}) ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        threading.Thread(
            target=self._ask_for_help_logic,
            args=(msg.action_id,),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #

    def _ask_for_help_logic(self, action_id):
        self._set_custom_prompt()
        try:
            self.execute()
            self.apply_effects()
        finally:
            self._restore_prompt()
        self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
        print(f"✓ Action {action_id} completed!\n")

    # ------------------------------------------------------------------ #

    def _set_custom_prompt(self):
        """Sostituisce il system prompt del bot con uno specifico per questa azione."""
        try:
            self._original_prompt = self.bot.aimodel.prompts[0]["content"]
            self.bot.aimodel.prompts[0]["content"] = ASK_FOR_HELP_SYSTEM_PROMPT
            print("✓ System prompt sostituito per ask_for_help")
        except (AttributeError, IndexError, KeyError) as e:
            rospy.logwarn(f"Non riesco a sovrascrivere il system prompt: {e}")

    def _restore_prompt(self):
        """Ripristina il system prompt originale."""
        try:
            if self._original_prompt is not None:
                self.bot.aimodel.prompts[0]["content"] = self._original_prompt
                print("✓ System prompt ripristinato")
        except (AttributeError, IndexError, KeyError) as e:
            rospy.logwarn(f"Non riesco a ripristinare il system prompt: {e}")

    # ------------------------------------------------------------------ #

    def execute(self):
        try:
            # Fase 1: il robot mostra paura e chiede aiuto
            # self.bot.qt.ts.sync([
            #     (0, lambda: self.bot.qt.emotionShow('QT/afraid')),
            #     (0, lambda: self.bot.qt.gesturePlay('QT/emotions/afraid', 1.0)),
            # ])
            self.bot.speak(
                "Oh no... mi sento un po' spaventato e non so cosa fare! "
                "Ho bisogno del tuo aiuto! "
                "Puoi raccontarmi qualcosa di bello che ti rende felice? "
                "Così mi fai sentire meglio!"
            )

            #rospy.sleep(1.0)

            # Fase 2: turni di ascolto
            for turn in range(1, self.NUM_TURNS + 1):
                is_last = (turn == self.NUM_TURNS)
                print(f"In attesa del turno {turn}/{self.NUM_TURNS}...")

                transcript = None
                while not transcript:
                    transcript = self.bot.qt.listen("listening_icon")
                    if not transcript:
                        self.bot.qt.ts.sync([
                            (0, lambda: self.bot.qt.emotionShow('QT/afraid')),
                            (0, lambda: self.bot.qt.gesturePlay('QT/emotions/afraid', 1.0)),
                        ])
                        self.bot.speak("Non ti sento bene... puoi ripetere? Ho ancora paura!")

                print(f"Human (Turno {turn}): {transcript}")

                # Sentiment solo per log, non triggera gesture automatiche
                if self.bot.sentiment_enabled:
                    epa = self.bot.get_sentiment(transcript)
                    print(f"Sentiment rilevato (ignorato per gesture): {epa}")

                # Genera risposta in thread separato per evitare conflitti event loop
                self._respond_to_child_safe(transcript, is_last)

            print("Ask for help terminato.")

        except Exception as e:
            rospy.logerr(f"Ask for help action failed: {e}")

    # ------------------------------------------------------------------ #

    def _respond_to_child_safe(self, transcript, is_last):
        result = {"response": None}

        def _generate():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if is_last:
                    closing_transcript = (
                        transcript +
                        " [Rispondi senza fare domande alla fine. "
                        "Ringrazia il bambino calorosamente e digli che ora stai meglio.]"
                    )
                    result["response"] = self.bot.aimodel.generate(closing_transcript)
                    if result["response"]:
                        result["response"] = self._strip_final_question(result["response"])
                else:
                    result["response"] = self.bot.aimodel.generate(transcript)
            finally:
                loop.close()

        gen_thread = threading.Thread(target=_generate, daemon=True)
        gen_thread.start()

        self.bot.think()
        gen_thread.join()

        print(f"QT (risposta): {result['response']}")  # ← stampa aggiunta

        if is_last:
            self.bot.qt.ts.sync([
                (0, lambda: self.bot.qt.emotionShow('QT/happy')),
                (0, lambda: self.bot.qt.gesturePlay('QT/clapping', 1.0)),
            ])
            if result["response"]:
                self.bot.qt.talkText(result["response"])
            rospy.sleep(0.5)
            self.bot.qt.talkText(
                "Grazie a te mi sono sentito subito meglio! "
                "Sei stato bravissimo! Ora possiamo tornare a giocare!"
            )
            self.bot.qt.ts.sync([
                (0, lambda: self.bot.qt.emotionShow('QT/showing_smile')),
                (0, lambda: self.bot.qt.gesturePlay('QT/emotions/happy', 1.0)),
            ])
        else:  # ← else correttamente allineato con if is_last
            self.bot.qt.ts.sync([
                (0, lambda: self.bot.qt.emotionShow('QT/shy')),
                (0, lambda: self.bot.qt.gesturePlay('QT/emotions/shy', 1.0)),
            ])
            if result["response"]:
                self.bot.qt.talkText(result["response"])
            rospy.sleep(0.3)
            self.bot.qt.talkText("Che bello... continua pure, parlami di qualcos altro che ti rende felice!")

    # ------------------------------------------------------------------ #

    def _strip_final_question(self, text):
        from nltk.tokenize import sent_tokenize
        sentences = sent_tokenize(text)
        if sentences and sentences[-1].strip().endswith('?'):
            sentences = sentences[:-1]
        return ' '.join(sentences) if sentences else text

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
        AskForHelpAction()
    except rospy.ROSInterruptException:
        pass