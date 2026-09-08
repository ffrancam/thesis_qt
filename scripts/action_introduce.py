#!/usr/bin/env python3
import threading
import rospy
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_dispatch_msgs.srv import DispatchService
from rosplan_knowledge_msgs.srv import (
    KnowledgeUpdateService, KnowledgeUpdateServiceRequest,
    GetAttributeService
)
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from std_srvs.srv import Empty

from conversation import QTChatBot


REFUSED_GAME_SYSTEM_PROMPT = (
    "Sei QT, un robot amichevole che parla in italiano con un bambino che non vuole giocare. "
    "Hai già salutato e non devi salutare di nuovo. "
    "Il tuo obiettivo è fare una breve conversazione naturale per conoscere meglio il bambino "
    "e creare un rapporto positivo prima di riproporre il gioco. "
    "\n\n"
    "REGOLE IMPORTANTI:"
    "\n- Ascolta attentamente ciò che dice il bambino."
    "\n- Rispondi PRIMA a ciò che ha detto: mostra interesse, commenta, riconosci o fai un breve collegamento."
    "\n- Non ignorare mai il contenuto della risposta del bambino."
    "\n- Fai al massimo UNA domanda per risposta."
    "\n- La domanda deve essere collegata, quando possibile, a ciò che il bambino ha appena detto."
    "\n- Non fare domande casuali non collegate alla conversazione."
    "\n- Se il bambino dà una risposta breve o generica, puoi fare una domanda semplice per conoscerlo meglio."
    "\n- Non menzionare il gioco durante questi turni."
    "\n- Rispondi in massimo 2 frasi."
    "\n- Usa un tono caldo, curioso e naturale."
)


class IntroduceAction:

    NUM_TURNS = 3  

    def __init__(self):
        rospy.init_node('introduce_action_node')
        print("Introduce Action Node started!")

        self.bot = QTChatBot()  # ← istanza condivisa per la conversazione libera

        rospy.Subscriber('/rosplan_plan_dispatcher/action_dispatch',
                         ActionDispatch, self.action_callback)

        self.feedback_pub = rospy.Publisher('/rosplan_plan_dispatcher/action_feedback',
                                            ActionFeedback, queue_size=10)

        services = [
            '/rosplan_knowledge_base/update',
            '/rosplan_knowledge_base/state/goals',
        ]
        for s in services:
            rospy.wait_for_service(s)

        self.update_kb  = rospy.ServiceProxy('/rosplan_knowledge_base/update', KnowledgeUpdateService)
        self.get_goals  = rospy.ServiceProxy('/rosplan_knowledge_base/state/goals', GetAttributeService)

        print("Introduce Action Interface ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #

    def action_callback(self, msg):
        if msg.name != 'introduce_game':
            return

        print(f"\n=== Executing Action {msg.action_id} ===")
        self.send_feedback(msg.action_id, ActionFeedback.ACTION_ENABLED)

        threading.Thread(
            target=self._introduce_logic,
            args=(msg.action_id,),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #

    def _introduce_logic(self, action_id):
        success, user_said_no = self.execute()

        if not success:
            self.send_feedback(action_id, ActionFeedback.ACTION_FAILED)
            print(f"✗ Action {action_id} failed!\n")
            return

        if user_said_no:
            self._handle_refusal()  

        self.apply_effects(user_said_no=user_said_no)
        self.send_feedback(action_id, ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE)
        print(f"✓ Action {action_id} completed!\n")

    # ------------------------------------------------------------------ #

    def execute(self):
        try:
            self.bot.qt.ts.sync([
                (0, lambda: self.bot.qt.emotionShow('QT/happy')),
                (0, lambda: self.bot.qt.talkText("Ti va di giocare a un gioco insieme?"))
            ])

            answer = None
            for _ in range(2):
                transcript = self.bot.qt.listen("listening_icon")
                answer = self.bot.qt.check_yes_no(transcript)
                if answer is not None:
                    break
                self.bot.qt.talkText("Non ho capito, puoi rispondere sì o no?")

            if answer == 1:
                self.bot.qt.ts.sync([
                    (0, lambda: self.bot.qt.emotionShow('QT/happy')),
                    (0, lambda: self.bot.qt.talkText(
                        "Perfetto! Ti farò delle domande e tu dovrai rispondere. Iniziamo!"
                    ))
                ])
                return True, False  # success, user_said_no=False
            else:
                # self.bot.qt.ts.sync([
                #     (0, lambda: self.bot.qt.emotionShow('QT/sad')),
                #     (0, lambda: self.bot.qt.talkText(
                #         "Va bene, non fa niente. Chiacchieriamo un po' allora! Cosa mi racconti di bello oggi?"
                #     ))
                # ])
                self.bot.qt.talkText("Va bene, non fa niente. Chiacchieriamo un po' allora! Cosa mi racconti di bello oggi?")
                return True, True  # success=True (eseguita), user_said_no=True

        except rospy.ServiceException as e:
            rospy.logerr(f"Service call failed: {e}")
            return False, False

    # ------------------------------------------------------------------ #

    def _handle_refusal(self):
        original_prompt = None
        try:
            original_prompt = self.bot.aimodel.prompts[0]["content"]
            self.bot.aimodel.prompts[0]["content"] = REFUSED_GAME_SYSTEM_PROMPT
            self.bot.aimodel.prompts = [self.bot.aimodel.prompts[0]]

            for turn in range(1, self.NUM_TURNS + 1):
                is_last = (turn == self.NUM_TURNS)
                print(f"Refusal conversation — turno {turn}/{self.NUM_TURNS}")

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
                        "Concludi con entusiasmo dicendo che ora che vi siete conosciuti un po' "
                        "è il momento di iniziare a giocare insieme. Dovrà solo rispondere a delle domande.]"
                    )
                    response = self.bot.aimodel.generate(closing_transcript)
                else:
                    response = self.bot.aimodel.generate(transcript)

                if response:
                    self.bot.speak(response)

        except Exception as e:
            rospy.logerr(f"_handle_refusal failed: {e}")
        finally:
            if original_prompt is not None:
                try:
                    self.bot.aimodel.prompts[0]["content"] = original_prompt
                    self.bot.aimodel.prompts = [self.bot.aimodel.prompts[0]]
                    print("✓ System prompt ripristinato")
                except Exception as e:
                    rospy.logwarn(f"Non riesco a ripristinare il system prompt: {e}")

    # ------------------------------------------------------------------ #

    def apply_effects(self, user_said_no=False):
        self._update_predicate(
            KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE,
            'quiz_introduced', []
        )
        self._update_predicate(
            KnowledgeUpdateServiceRequest.REMOVE_KNOWLEDGE,
            'emotion_checked', []
        )

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

    def send_feedback(self, action_id, status):
        feedback = ActionFeedback()
        feedback.action_id = action_id
        feedback.status = status
        self.feedback_pub.publish(feedback)


if __name__ == '__main__':
    try:
        IntroduceAction()
    except rospy.ROSInterruptException:
        pass