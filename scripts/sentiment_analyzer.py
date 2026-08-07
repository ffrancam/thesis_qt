#!/usr/bin/env python3
import rospy
from thesis_qt.srv import SentimentAnalyzer, SentimentAnalyzerResponse
from engines.openai import OpenAI

EMOTION_MAP = {
    "H":  [3.44,  2.93,  0.92],
    "F":  [-2.37, -1.04, -0.71],
    "A":  [-1.77,  0.57,  1.8],
    "SA": [-2.29, -1.44, -2.04],
    "SU": [0.5,   2.5,   3.19],
    "D":  [-2.27,  0.22,  0.43],
    "N":  [0.58,   0.75,  0.56],
    "B":  [-1.85, -0.86, -2.01]
}

class SentimentService:
    def __init__(self):
        rospy.init_node('sentiment_analyzer_service')
        self.aimodel = OpenAI()
        rospy.Service(
            '/sentiment_analyzer',
            SentimentAnalyzer,
            self.handle_request
        )
        print("✓ Sentiment Analyzer Service ready!")
        rospy.spin()

    def handle_request(self, req):
        transcript = req.user_res
        print(f"[SentimentService] Analyzing: '{transcript}'")

        prompt = (
            f"Classifica il sentiment di questa frase detta da un bambino durante un quiz: '{transcript}'.\n"
            f"Scegli UNA SOLA lettera tra: H, F, A, SA, SU, D, N\n"
            f"Dove:\n"
            f"- H  = Felice (Happy)\n"
            f"- F  = Spaventato (Fear)\n"
            f"- A  = Arrabbiato (Angry)\n"
            f"- SA = Triste (Sad)\n"
            f"- SU = Sorpreso (Surprise)\n"
            f"- D  = Disgustato (Disgust)\n"
            f"- N  = Neutro (Neutral)\n"
            f"- B  = Annoiato (Bored)\n"
            f"Rispondi SOLO con la lettera o coppia di lettere, nient'altro."
        )

        result = []
        self.aimodel.generate(prompt, lambda txt: result.append(txt))
        response = ''.join(result).strip().upper()
        print(f"[SentimentService] Raw response: '{response}'")

        # SA e SU prima per evitare match parziali con S
        emotion = None
        for key in ["SA", "SU", "H", "F", "A", "D", "N", "B"]:
            if key in response:
                emotion = key
                break

        if emotion is None:
            print(f"[SentimentService] Unknown emotion '{response}', defaulting to N")
            emotion = "N"

        epa = EMOTION_MAP[emotion]
        print(f"[SentimentService] Emotion={emotion}, EPA={epa}")
        return SentimentAnalyzerResponse(success=True, epa=epa)


if __name__ == '__main__':
    try:
        SentimentService()
    except rospy.ROSInterruptException:
        pass