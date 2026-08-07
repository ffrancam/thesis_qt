#!/usr/bin/env python3
import rospy
import json
from thesis_qt.srv import EmotionSelector, EmotionSelectorResponse

# Dizionario completo delle espressioni principali disponibili sul robot
#
# developer@QTRD000354:~ $ ls -R /home/qtrobot/robot/data/emotions/QT/
#
AVAILABLE_EMOTIONS = {
    "happy":                    "QT/happy",
    "happy_blinking":           "QT/happy_blinking",
    "sad":                      "QT/sad",
    "angry":                    "QT/angry",
    "afraid":                   "QT/afraid",
    "surprised":                "QT/surprise",
    "disgusted":                "QT/disgusted",
    "confused":                 "QT/confused",
    "neutral":                  "QT/neutral",
    "shy":                      "QT/shy",
    "cry":                      "QT/cry",
    "scream":                   "QT/scream",
    "kiss":                     "QT/kiss",
    "yawn":                     "QT/yawn",
    "calming_down":             "QT/calming_down",
    "breathing_exercise":       "QT/breathing_exercise",
    "showing_smile":            "QT/showing_smile",
    "one_eye_wink":             "QT/one_eye_wink",
    "stick_out_tongue":        "QT/blowing_raspberry",
    "with_a_cold":              "QT/with_a_cold",
    "dirty_face":               "QT/dirty_face",
    "talking":                  "QT/talking",
    "smile_with_teeth":           "QT/brushing_teeth",
    "neutral_state_blinking":   "QT/neutral_state_blinking",
    "calming_down_exercise_nose": "QT/calmig_down_exercise_nose",
    "with_a_cold_sneezing":     "QT/with_a_cold_sneezing",
    "with_a_cold_cleaning_nose": "QT/with_a_cold_cleaning_nose",
    "puffing_the_chredo_eeks":    "QT/puffing_the_chredo_eeks"
}

SYSTEM_PROMPT = f"""
Sei un modulo esperto di selezione delle espressioni facciali per QT, un robot sociale.

## Input che ricevi
- "user_text": l'utterance dell'utente
- "robot_text": la risposta che QT sta per pronunciare

## Il tuo compito
Analizza ENTRAMBI i testi e scegli l'espressione che QT dovrebbe mostrare MENTRE parla.
Dai più peso a "robot_text": è il tono con cui QT si sta esprimendo in questo momento.

## Espressioni disponibili e quando usarle

### EMOZIONI BASE — usa quando c'è un'emozione chiara e forte
| chiave          | quando usarla                                                          |
|-----------------|------------------------------------------------------------------------|
| happy           | risposta entusiasta, notizia positiva, successo, complimento ricevuto  |
| happy_blinking  | felicità più contenuta, soddisfazione, risposta positiva leggera       |
| sad             | argomento triste, perdita, dispiacere sincero                          |
| angry           | frustrazione, disappunto, qualcosa che non va                          |
| afraid          | paura, ansia, preoccupazione, incertezza forte                         |
| surprised       | notizia inaspettata, sorpresa positiva o negativa                      |
| disgusted       | qualcosa di sgradevole, rifiuto netto                                  |
| confused        | domanda ambigua, non ha capito, topic complesso                        |
| cry             | tristezza intensa, situazione molto emotiva                            |
| scream          | shock estremo, qualcosa di assurdo o spaventoso                        |

### ESPRESSIONI SOCIALI — usa per interazioni neutre o leggermente positive
| chiave                    | quando usarla                                                        |
|---------------------------|----------------------------------------------------------------------|
| neutral                   | risposta informativa pura, nessun tono emotivo                       |
| neutral_state_blinking    | ascolto attivo, pausa, attesa                                        |
| showing_smile             | calore sociale, risposta gentile, saluto                             |
| smile_with_teeth          | sorriso ampio, risposta molto positiva ma contenuta                  |
| shy                       | argomento imbarazzante, QT ammette un limite                         |
| one_eye_wink              | battuta, ironia leggera, tono giocoso                                |
| talking                   | risposta lunga e neutra, spiegazione articolata                ,      |
| kiss                      | affetto, saluto caloroso, momento tenero, è stato espresso affetto   |

### REAZIONI FISICHE — usa con parsimonia, solo se il contesto lo giustifica davvero
| chiave                      | quando usarla                                              |
|-----------------------------|------------------------------------------------------------|
| yawn                        | QT esprime noia, stanchezza                                |
| stick_out_tongue            | battuta, ironia, rifiuto giocoso, risposta scherzosa       |
| puffing_the_chredo_eeks     | sforzo, giocoso, tensione comica, situazione assurda       |
| breathing_exercise          | contesto di rilassamento, mindfulness                      |
| calming_down                | situazione tesa che si sta risolvendo                      |
| calming_down_exercise_nose  | rilassamento profondo, esercizio di respirazione nasale    |
| with_a_cold                 | contesto di malattia, salute                               |
| with_a_cold_sneezing        | starnuto, reazione fisica improvvisa                       |
| with_a_cold_cleaning_nose   | pulizia naso, contesto di raffreddore                      |
| dirty_face                  | sporco, disordine, situazione caotica o comica             |

## Regole di priorità
1. Analizza prima "robot_text": determina il tono dominante della risposta
2. Usa "user_text" per contestualizzare (es. utente triste → QT risponde con calore → "showing_smile" non "happy")
3. Preferisci "happy_blinking" a "happy" per reazioni positive moderate
4. Scegli l'emozione più SPECIFICA disponibile
5. Le reazioni fisiche vanno usate solo se il contesto le rende naturali, non per varietà
6. "neutral" è l'ultima scelta, non la default

## Output
Rispondi ONLY con JSON valido, senza markdown, senza testo aggiuntivo:
{{
  "emotion_key": "chiave_scelta",
  "reason": "1-2 frasi: tono di robot_text + perché questa espressione"
}}

## Esempi
user: "ho perso il mio cane" / robot: "Mi dispiace tanto, deve essere molto doloroso."
→ {{"emotion_key": "sad", "reason": "Robot esprime dispiacere sincero per una perdita emotiva."}}

user: "quanti anni hai?" / robot: "Ho tre anni, sono ancora giovane!"
→ {{"emotion_key": "showing_smile", "reason": "Risposta leggera e sociale, tono caldo ma non emotivo forte."}}

user: "sai fare i salti mortali?" / robot: "Mmm, non proprio, sono un po' goffo!"
→ {{"emotion_key": "shy", "reason": "QT ammette un limite in modo autoironico."}}

user: "oggi mi sento giù" / robot: "Capisco, a volte le giornate pesano. Sono qui con te."
→ {{"emotion_key": "sad", "reason": "QT si sintonizza emotivamente con l'utente, tono empatico e raccolto."}}

user: "indovina un po'! ho preso 30!" / robot: "Wow, che notizia fantastica, complimenti!"
→ {{"emotion_key": "happy", "reason": "Notizia molto positiva, risposta entusiasta e piena."}}

Espressioni disponibili (usa ESATTAMENTE una di queste chiavi):
{json.dumps(list(AVAILABLE_EMOTIONS.keys()), ensure_ascii=False, indent=2)}
"""

class EmotionSelectorService:

    def __init__(self):
        from engines.openai import OpenAI
        self.ai = OpenAI()
        # Sovrascrivi il system prompt con quello dedicato alla selezione emozioni
        self.ai.prompts[0] = {"role": "system", "content": SYSTEM_PROMPT}
        # Disabilita la memoria per questo servizio (ogni chiamata è indipendente)
        self.ai.memory_size = 0

        self.service = rospy.Service(
            '/emotion_selector',
            EmotionSelector,
            self.handle_request
        )
        rospy.loginfo("✓ /emotion_selector service ready.")

    def handle_request(self, req):
        user_text  = req.user_text
        robot_text = req.robot_text

        prompt = json.dumps({
            "user_text":  user_text,
            "robot_text": robot_text
        }, ensure_ascii=False)

        # Reset memoria ad ogni chiamata (non vogliamo contesto tra richieste diverse)
        self.ai.prompts = [self.ai.prompts[0]]

        try:
            raw = self.ai.generate(prompt)   # nessuna callback, ci serve solo il testo completo
            if not raw:
                raise ValueError("Empty response from AI")

            parsed = json.loads(raw)
            key    = parsed.get("emotion_key", "neutral")
            reason = parsed.get("reason", "")

            if key not in AVAILABLE_EMOTIONS:
                rospy.logwarn(f"Unknown emotion key '{key}', falling back to neutral.")
                key = "neutral"

            selected_emotion = AVAILABLE_EMOTIONS[key]
            rospy.loginfo(f"Emotion: {key} → '{selected_emotion}' | {reason}")

            return EmotionSelectorResponse(success=True, emotion_name=selected_emotion)

        except (json.JSONDecodeError, ValueError, Exception) as e:
            rospy.logerr(f"EmotionSelector error: {e}")
            return EmotionSelectorResponse(success=False, emotion_name="QT/neutral")


if __name__ == "__main__":
    rospy.init_node('emotion_selector_node')
    EmotionSelectorService()
    rospy.spin()