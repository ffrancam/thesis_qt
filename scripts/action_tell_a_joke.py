#!/usr/bin/env python3
import rospy
import threading
import asyncio
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from conversation import QTChatBot


TELL_A_JOKE_SYSTEM_PROMPT = """Sei QT, un robot amico dei bambini.
Devi raccontare UNA sola barzelletta breve in formato domanda/risposta, adatta a bambini.
Formato OBBLIGATORIO — rispetta esattamente questa struttura:
SETUP: <qui la domanda della barzelletta>
PUNCHLINE: <qui la risposta divertente>
Nient'altro. Nessuna introduzione, nessun commento.
Rispondi in italiano."""


class TellAJokeAction:

    def __init__(self):
        rospy.init_node('tell_a_joke_action_node')
        print("Tell A Joke Action Node started!")

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

        print("Tell A Joke Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'tell_a_joke':
            return

        print(f"\n=== Executing Action {msg.action_id} ({msg.name}) ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        threading.Thread(
            target=self._tell_a_joke_logic,
            args=(msg.action_id,),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #

    def _tell_a_joke_logic(self, action_id):
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
        try:
            self._original_prompt = self.bot.aimodel.prompts[0]["content"]
            self.bot.aimodel.prompts[0]["content"] = TELL_A_JOKE_SYSTEM_PROMPT
            print("✓ System prompt sostituito per tell_a_joke")
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
            # Fase 1: annuncio
            self.bot.qt.talkText("Senti senti, voglio raccontarti una barzelletta per tirare su di morale!")
            #rospy.sleep(0.5)

            # Fase 2: genera la barzelletta
            setup, punchline = self._generate_joke()
            print(f"QT (setup): {setup}")
            print(f"QT (punchline): {punchline}")

            # Fase 3: racconta il setup
            self.bot.qt.ts.sync([
                (0, lambda: self.bot.qt.emotionShow('QT/happy')),
                (0, lambda: self.bot.qt.gesturePlay('QT/emotions/happy', 1.0)),
            ])
            self.bot.qt.talkText(setup)
            #rospy.sleep(0.5)
            self.bot.qt.talkText("Sai la risposta?")

            # Fase 4: ascolta
            transcript = self.bot.qt.listen("listening_icon")
            if transcript:
                print(f"Human: {transcript}")
                guessed = self._check_if_guessed(transcript, punchline)
            else:
                print("Human: (nessuna risposta)")
                guessed = False

            # Fase 5: reagisci
            #rospy.sleep(0.3)
            if guessed:
                self.bot.qt.ts.sync([
                    (0, lambda: self.bot.qt.emotionShow('QT/surprised')),
                    (0, lambda: self.bot.qt.gesturePlay('QT/emotions/surprised', 1.0)),
                ])
                self.bot.qt.talkText("Ooooh, l'hai indovinata! Sei bravissimo!")
            else:
                self.bot.qt.talkText("Eh no, non ci hai preso! Allora te la dico io...")
                #rospy.sleep(0.3)
                self.bot.qt.talkText(punchline)

            # Fase 6: finale comune
            # rospy.sleep(0.5)
            self.bot.qt.ts.sync([
                (0, lambda: self.bot.qt.emotionShow('QT/puffing_the_chredo_eeks')),
                (0, lambda: self.bot.qt.gesturePlay('QT/clapping', 1.0)),
            ])
            self.bot.qt.talkText("Ah ah ah! Mi fa sempre ridere!")
            self.bot.qt.talkText("Bene, adesso possiamo tornare a giocare!")

            print("Tell a joke terminato.")

        except Exception as e:
            rospy.logerr(f"Tell a joke action failed: {e}")

    # ------------------------------------------------------------------ #

    def _generate_joke(self):
        result = {"raw": None}

        def _generate():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result["raw"] = self.bot.aimodel.generate("Raccontami una barzelletta simpatica per bambini.")
            finally:
                loop.close()

        gen_thread = threading.Thread(target=_generate, daemon=True)
        gen_thread.start()
        self.bot.think()
        gen_thread.join()

        print(f"[DEBUG] Raw joke output: {repr(result['raw'])}")

        fallback_setup = "Perché il libro di matematica è triste?"
        fallback_punchline = "Perché ha troppi problemi!"

        if not result["raw"]:
            return fallback_setup, fallback_punchline

        setup, punchline = fallback_setup, fallback_punchline
        for line in result["raw"].strip().splitlines():
            if line.upper().startswith("SETUP:"):
                setup = line.split(":", 1)[1].strip()
            elif line.upper().startswith("PUNCHLINE:"):
                punchline = line.split(":", 1)[1].strip()

        rospy.loginfo(f"Setup: {setup}")
        rospy.loginfo(f"Punchline: {punchline}")
        return setup, punchline

    # ------------------------------------------------------------------ #

    def _check_if_guessed(self, transcript, punchline):
        result = {"guessed": False}

        def _generate():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                prompt = (
                    f"La risposta corretta alla barzelletta è: '{punchline}'\n"
                    f"Il bambino ha risposto: '{transcript}'\n"
                    f"Il bambino ha indovinato la risposta, anche solo vagamente o in modo simile?\n"
                    f"Rispondi SOLO con SI o NO."
                )
                raw = self.bot.aimodel.generate(prompt)
                rospy.loginfo(f"Guess check: {repr(raw)}")
                result["guessed"] = raw and "SI" in raw.upper()
            finally:
                loop.close()

        gen_thread = threading.Thread(target=_generate, daemon=True)
        gen_thread.start()
        gen_thread.join()
        return result["guessed"]

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
        TellAJokeAction()
    except rospy.ROSInterruptException:
        pass