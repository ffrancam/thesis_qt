#!/usr/bin/env python3
import random
import rospy

from nltk.tokenize import sent_tokenize, word_tokenize

from qt_robot_interface.srv import *
from qt_api import QTRobot
from engines.openai import OpenAI

from thesis_qt.srv import SentimentAnalyzer
from thesis_qt.srv import EmotionSelector
from thesis_qt.srv import GestureSelector

# Mappa label → EPA (identica a SentimentService)
EMOTION_EPA = {
    "happy":    [3.44,  2.93,  0.92],
    "fear":     [-2.37, -1.04, -0.71],
    "angry":    [-1.77,  0.57,  1.8],
    "sad":      [-2.29, -1.44, -2.04],
    "surprise": [0.5,   2.5,   3.19],
    "disgust":  [-2.27,  0.22,  0.43],
    "neutral":  [0.58,   0.75,  0.56],
    "bored":    [-1.85, -0.86, -2.01],
}


def epa_to_emotion(epa):
    """Trova l'emozione più vicina all'EPA ricevuto per distanza euclidea."""
    best_emotion = "neutral"
    best_dist = float("inf")
    for emotion, ref in EMOTION_EPA.items():
        dist = sum((a - b) ** 2 for a, b in zip(epa, ref))
        if dist < best_dist:
            best_dist = dist
            best_emotion = emotion
    return best_emotion


class QTChatBot():

    def __init__(self):
        self.qt = QTRobot()

        self.sentiment_enabled = rospy.get_param("/offline_conversation/sentiment", True)
        self.error_feedback = "Mi dispiace, ho un problema tecnico. Riprova."
        self.finish = False
        self._last_response = None

        self.aimodel = OpenAI()
        self.aimodel.memory_size = 10

        # ── Sentiment ──────────────────────────────────────────────────────── #
        rospy.loginfo("Waiting for /sentiment_analyzer service...")
        try:
            rospy.wait_for_service('/sentiment_analyzer', timeout=3.0)
            self.sentiment_srv = rospy.ServiceProxy('/sentiment_analyzer', SentimentAnalyzer)
            rospy.loginfo("✓ Connected to /sentiment_analyzer service.")
        except rospy.ROSException:
            rospy.logwarn("Service /sentiment_analyzer not available right now.")
            self.sentiment_srv = None

        # ── Emotion selector ───────────────────────────────────────────────── #
        rospy.loginfo("Waiting for /emotion_selector service...")
        try:
            rospy.wait_for_service('/emotion_selector', timeout=3.0)
            self.emotion_selector_srv = rospy.ServiceProxy('/emotion_selector', EmotionSelector)
            rospy.loginfo("✓ Connected to /emotion_selector service.")
        except rospy.ROSException:
            rospy.logwarn("Service /emotion_selector not available right now.")
            self.emotion_selector_srv = None

        # ── Gesture selector ───────────────────────────────────────────────── #
        rospy.loginfo("Waiting for /gesture_selector service...")
        try:
            rospy.wait_for_service('/gesture_selector', timeout=3.0)
            self.gesture_selector_srv = rospy.ServiceProxy('/gesture_selector', GestureSelector)
            rospy.loginfo("✓ Connected to /gesture_selector service.")
        except rospy.ROSException:
            rospy.logwarn("Service /gesture_selector not available right now.")
            self.gesture_selector_srv = None

    # ------------------------------------------------------------------ #
    #  SPEECH                                                            #
    # ------------------------------------------------------------------ #

    def talk(self, text):
        print('QT talking:', text)
        self.qt.talkText(text)

    def speak(self, text, user_text=""):
        """Pronuncia il testo applicando emozione e gesture selezionate dai servizi."""
        sentences = sent_tokenize(text)
        closing_words = ["a presto", "arrivederci", "ci vediamo", "alla prossima", "addio"]

        # Emozione prima, gesture dopo (usa l'emozione scelta come input)
        selected_emotion = self._select_emotion(user_text, text)
        self._select_and_play_gesture(user_text, text, selected_emotion)

        for sentence in sentences:
            words = word_tokenize(sentence.lower())
            if any(w in closing_words for w in words):
                self.finish = True
            self.talk(sentence)

        self.qt.gesturePlay("QT/neutral", 1.0)

    # ------------------------------------------------------------------ #
    #  EMOTION & GESTURE SELECTION                                       #
    # ------------------------------------------------------------------ #

    def _select_emotion(self, user_text, robot_text):
        """
        Chiama /emotion_selector e pubblica l'espressione sul robot.
        Restituisce il nome dell'emozione selezionata (stringa QT/...).
        Fallback: QT/neutral.
        """
        fallback = "QT/neutral"

        if self.emotion_selector_srv is None:
            self.qt.emotion_pub.publish(fallback)
            return fallback

        try:
            resp = self.emotion_selector_srv(user_text=user_text, robot_text=robot_text)
            if resp.success and resp.emotion_name:
                emotion_name = resp.emotion_name
            else:
                rospy.logwarn("EmotionSelector returned success=False, using fallback.")
                emotion_name = fallback
        except rospy.ServiceException as e:
            rospy.logerr(f"EmotionSelector service call failed: {e}")
            emotion_name = fallback

        rospy.loginfo(f"Publishing emotion: {emotion_name}")
        self.qt.emotion_pub.publish(emotion_name)
        return emotion_name

    def _select_and_play_gesture(self, user_text, robot_text, selected_emotion):
        """
        Chiama /gesture_selector (dopo la scelta dell'emozione) e riproduce la gesture.
        Fallback: QT/neutral.
        """
        fallback = "QT/neutral"

        if self.gesture_selector_srv is None:
            self.qt.gesturePlay(fallback, 1.0)
            return

        try:
            resp = self.gesture_selector_srv(
                user_text=user_text,
                robot_text=robot_text,
                selected_emotion=selected_emotion,
            )
            if resp.success and resp.gesture_name:
                gesture_name = resp.gesture_name
            else:
                rospy.logwarn("GestureSelector returned success=False, using fallback.")
                gesture_name = fallback
        except rospy.ServiceException as e:
            rospy.logerr(f"GestureSelector service call failed: {e}")
            gesture_name = fallback

        rospy.loginfo(f"Playing gesture: {gesture_name}")
        self.qt.gesturePlay(gesture_name, 1.0)

    # ------------------------------------------------------------------ #
    #  THINKING / BOREDOM                                                  #
    # ------------------------------------------------------------------ #

    def think(self):
        if random.choice([0, 1]) == 0:
            self.qt.gesturePlay(random.choice(["QT/angry", "think_right"]), 1.0)
            self.qt.emotion_pub.publish("QT/confused")
        return True

    def bored(self):
        if random.choice([0, 1]) == 0:
            self.qt.gesturePlay("QT/angry", 1.0)
            self.talk(random.choice(["#THROAT01#", "#BREATH01#", "#THROAT02#"]))

    # ------------------------------------------------------------------ #
    #  SENTIMENT                                                           #
    # ------------------------------------------------------------------ #

    def get_sentiment(self, sentence):
        """Chiama il servizio e ritorna {'emotion': ..., 'epa': [...]}."""
        if self.sentiment_srv is None:
            return {'emotion': 'neutral', 'epa': EMOTION_EPA['neutral']}

        try:
            srv_response = self.sentiment_srv(user_res=sentence)
            if srv_response.success:
                epa = list(srv_response.epa)
                emotion = epa_to_emotion(epa)
                print(f"Sentiment EPA: {epa} → emotion: {emotion}")
                return {'emotion': emotion, 'epa': epa}
            else:
                print("Sentiment service returned success=False")
        except rospy.ServiceException as e:
            print(f"Service call failed: {e}")

        return {'emotion': 'neutral', 'epa': EMOTION_EPA['neutral']}

    def show_sentiment(self, sentiment, user_text=""):
        """
        Mostra una reazione empatica al sentiment dell'utente,
        usando emotion_selector e gesture_selector per coerenza.
        """
        emotion = sentiment['emotion']
        print(f"Detected user sentiment: {emotion}")

        # empathy_responses = {
        #     'happy':    "Yeah! Fantastico!",
        #     'angry':    "Capisco, deve essere frustrante.",
        #     'surprise': "Oh WOW! Incredibile!",
        #     'sad':      "Mi dispiace, sono qui con te.",
        #     'fear':     "Capisco, deve essere preoccupante.",
        #     'disgust':  "Capisco il tuo disappunto.",
        #     'neutral':  "Capisco.",
        # }
        # robot_text = empathy_responses.get(emotion, "Capisco.")

        # selected_emotion = self._select_emotion(user_text, robot_text)
        # self._select_and_play_gesture(user_text, robot_text, selected_emotion)
        # self.talk(robot_text)

    # ------------------------------------------------------------------ #
    #  UTILS                                                               #
    # ------------------------------------------------------------------ #

    def refine_sentence(self, text):
        if not text:
            raise TypeError
        tokenized = sent_tokenize(text)
        last = tokenized[-1].strip()
        if not (last.endswith('.') or last.endswith('!') or last.endswith('?')):
            tokenized.pop()
            return ' '.join(tokenized) if tokenized else text
        return text

    # ------------------------------------------------------------------ #
    #  MAIN LOOP                                                           #
    # ------------------------------------------------------------------ #

    def start(self):
        while not rospy.is_shutdown() and not self.finish:
            print('Listening...')

            transcript = self.qt.listen("listening_icon")
            if not transcript:
                self.bored()
                continue

            print('Human:', transcript)

            if self.qt.check_repeat_request(transcript):
                self.speak(self._last_response or self.error_feedback)
                continue

            if self.sentiment_enabled:
                self.show_sentiment(self.get_sentiment(transcript), user_text=transcript)

            words = word_tokenize(transcript.lower())
            if 'stop' in words:
                self.qt.gesturePlay("QT/bye", 1.0)
                self.talk("Va bene, ciao!")
                self.finish = True
                continue

            # --- MODIFICA QUI ---
            # Rimuoviamo la callback da aimodel.generate in modo che non "spezzetti" l'output.
            results = self.qt.ts.sync([
                (0, lambda t=transcript: self.aimodel.generate(t)),
                #(0.5, lambda: self.think()),
            ])

            # Ora 'results' conterrà l'intera risposta generata.
            for r in results:
                if isinstance(r, str) and r:
                    self._last_response = r
                    # Chiamiamo 'speak' UNA SOLA VOLTA con l'intera risposta
                    self.speak(r, user_text=transcript)
                    break

        print("conversation_node stopping.")
        self.finish = False


if __name__ == "__main__":
    rospy.init_node('conversation_node')
    rospy.loginfo("conversation_node started!")
    bot = QTChatBot()
    bot.start()
    rospy.spin()