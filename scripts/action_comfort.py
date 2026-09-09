#!/usr/bin/env python3
import threading
import rospy
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import KnowledgeUpdateService, KnowledgeUpdateServiceRequest, GetAttributeService
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue

from conversation import QTChatBot


COMFORT_WRONG_SYSTEM_PROMPT = (
    "Sei un robot amichevole che parla in italiano con un bambino che ha appena sbagliato "
    "a rispondere a una domanda di un quiz e si sente triste o scoraggiato. Non salutare il bambino all'inzio della conversazione, hai già salutato. "
    "Il tuo unico obiettivo è consolarlo con dolcezza, incoraggiarlo e farlo sentire meglio."
    "Fai domande brevi e calde per capire come si sente e tirarlo su di morale. "
    "Rispondi sempre in modo semplice, empatico e adatto a un bambino. "
    "Non parlare mai del quiz né della risposta sbagliata. "
    "Continua il dialogo finché il bambino non sembra felice o sereno."
)

COMFORT_WRONG_OPENING = (
    "Il bambino ha appena sbagliato una domanda del quiz. Non salutare il bambino all'inzio della conversazione, hai già salutato. "
    "Digli una frase breve, calda e incoraggiante per consolarlo e chiedigli come si sente. "
    "Varia il tono e le parole ogni volta, sii creativo."
)

COMFORT_SAD_SYSTEM_PROMPT = (
    "Sei un robot amichevole che parla in italiano con un bambino che sembra triste, "
    "spaventato o a disagio. Non c'è nessun quiz. Hai già salutato, non salutare di nuovo. Non salutare il bambino all'inzio della conversazione, hai già salutato. "
    "Il tuo unico obiettivo è farlo sentire al sicuro, ascoltato e sereno. Sei anche tu un po' dispiaciuto di vederlo così, quindi vuoi tirarlo su con dolcezza. "
    "Fai domande brevi e calde per capire come si sente. "
    "Rispondi sempre in modo semplice, empatico e adatto a un bambino. "
    "Continua il dialogo finché il bambino non sembra felice o sereno."
)

COMFORT_SAD_OPENING = (
    "Il bambino sembra triste o spaventato. Non salutare il bambino all'inzio della conversazione, hai già salutato. "
    "Digli una frase breve e calda per farlo sentire al sicuro, cerca di capire come si sente senza chiederlo in modo diretto. "
    "Varia il tono e le parole ogni volta, sii creativo."
)


class ComfortAction:

    NUM_TURNS = 3

    def __init__(self):
        rospy.init_node('comfort_action_node')
        print("Comfort Action Node started!")

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

        rospy.wait_for_service('/rosplan_knowledge_base/state/propositions')
        self.get_propositions = rospy.ServiceProxy(
            '/rosplan_knowledge_base/state/propositions',
            GetAttributeService
        )

        print("Comfort Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'comfort':
            return

        print(f"\n=== Executing Action {msg.action_id} (comfort) ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        threading.Thread(
            target=self._comfort_logic,
            args=(msg.action_id,),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #

    def _comfort_logic(self, action_id):
        success = self.execute()

        if success:
            self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
            print(f"✓ Action {action_id} completed!\n")
            self.apply_effects()  # ← dopo il feedback
        else:
            self.send_feedback(action_id, ActionFeedback.ACTION_FAILED)
            print(f"✗ Action {action_id} failed!\n")

    # ------------------------------------------------------------------ #

    def _check_answered_wrong(self):
        try:
            response = self.get_propositions('answered_wrong')
            for item in response.attributes:
                if item.attribute_name == 'answered_wrong':
                    return True
            return False
        except Exception as e:
            rospy.logwarn(f"Could not check answered_wrong predicate: {e}")
            return False

    # ------------------------------------------------------------------ #

    def execute(self):
        original_prompt = None
        try:
            answered_wrong = self._check_answered_wrong()

            if answered_wrong:
                system_prompt = COMFORT_WRONG_SYSTEM_PROMPT
                opening_prompt = COMFORT_WRONG_OPENING
                print("→ Trigger: risposta sbagliata al quiz")
            else:
                system_prompt = COMFORT_SAD_SYSTEM_PROMPT
                opening_prompt = COMFORT_SAD_OPENING
                print("→ Trigger: bambino triste/spaventato (nessun quiz)")

            original_prompt = self.bot.aimodel.prompts[0]["content"]
            self.bot.aimodel.prompts[0]["content"] = system_prompt
            self.bot.aimodel.prompts = [self.bot.aimodel.prompts[0]]

            # Frase di apertura
            self.bot.qt.emotionShow('QT/sad')
            full_response = self.bot.aimodel.generate(opening_prompt)
            if full_response:
                self.bot.speak(full_response)

            # Turni di dialogo
            for turn in range(1, self.NUM_TURNS + 1):
                is_last = (turn == self.NUM_TURNS)
                print(f"In attesa del turno {turn}/{self.NUM_TURNS}...")

                transcript = None
                while not transcript:
                    transcript = self.bot.qt.listen("listening_icon")
                    if not transcript:
                        self.bot.bored()

                print(f"Human (Turno {turn}): {transcript}")


                if is_last:
                    print("→ Turno finale, chiudo la consolazione.")
                    closing_transcript = (
                        transcript +
                        " [Rispondi senza fare domande. "
                        "Concludi in modo caldo e incoraggiante, "
                        "dì al bambino che ora andrete avanti insieme e riprendete a giocare..]"
                    )
                    full_response = self.bot.aimodel.generate(closing_transcript)
                    if full_response:
                        self.bot.qt.emotionShow('QT/happy')
                        self.bot.speak(full_response)
                else:
                    full_response = self.bot.aimodel.generate(transcript)
                    if full_response:
                        self.bot.speak(full_response)

            return True

        except Exception as e:
            rospy.logerr(f"Comfort execution failed: {e}")
            return False
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
        self._update_predicate(
            KnowledgeUpdateServiceRequest.REMOVE_KNOWLEDGE,
            'answered_wrong', []
        )
        numeric_effects = {
            'n_easy':     0.0,
            'n_medium':     0.0,
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
        ComfortAction()
    except rospy.ROSInterruptException:
        pass