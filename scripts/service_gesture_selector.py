#!/usr/bin/env python3
import rospy
import json
from thesis_qt.srv import GestureSelector, GestureSelectorResponse

AVAILABLE_GESTURES = {
    # GESTURES PRINCIPALI
    "neutral":              "QT/neutral",
    "happy":                "QT/happy",
    "sad":                  "QT/sad",
    "angry":                "QT/angry",
    "surprise":             "QT/surprise",
    "bye":                  "QT/bye",
    "bye_bye":              "QT/bye-bye",
    "hi":                   "QT/hi",
    "clapping":             "QT/clapping",
    "send_kiss":            "QT/send_kiss",
    "kiss":                 "QT/kiss",
    "monkey":               "QT/monkey",
    "show_face":            "QT/Show-face",
    "show_qt":              "QT/show_QT",
    "show_tablet":          "QT/show_tablet",
    "show_left":            "QT/show_left",
    "show_right":           "QT/show_right",
    "point_front":          "QT/point_front",
    "one_arm_up":           "QT/one-arm-up",
    "up_left":              "QT/up_left",
    "up_right":             "QT/up_right",
    "swipe_left":           "QT/swipe_left",
    "swipe_right":          "QT/swipe_right",
    "hand_front_hold":      "QT/hand-front-hold",
    "peekaboo":             "QT/peekaboo",
    "peekaboo_back":        "QT/peekaboo-back",
    "touch_head":           "QT/touch-head",
    "touch_head_back":      "QT/touch-head-back",
    "bored":                "QT/bored",
    "challenge":            "QT/challenge",
    "stretching":           "QT/stretching",
    "yawn":                 "QT/yawn",
    "sneezing":             "QT/sneezing",
    "drink":                "QT/drink",
    "train":                "QT/train",
    "breathing_exercise":   "QT/breathing_exercise",
    "personal_distance":    "QT/personal-distance",
    # EMOTIONS GESTURES (movimenti corporei abbinati a emozioni)
    "emotion_afraid":       "QT/emotions/afraid",
    "emotion_angry":        "QT/emotions/angry",
    "emotion_calm":         "QT/emotions/calm",
    "emotion_disgusted":    "QT/emotions/disgusted",
    "emotion_happy":        "QT/emotions/happy",
    "emotion_hooray":       "QT/emotions/hoora",
    "emotion_sad":          "QT/emotions/sad",
    "emotion_shy":          "QT/emotions/shy",
    "emotion_surprised":    "QT/emotions/surprised",
    # PRETEND PLAY
    "pretend_beep":         "QT/Pretend-play/Beep",
    "pretend_beeping":      "QT/Pretend-play/Beeping",
    "pretend_drive":        "QT/Pretend-play/Drive",
    "pretend_driving":      "QT/Pretend-play/Driving",
    "pretend_fly":          "QT/Pretend-play/Fly",
    "pretend_phone_call":   "QT/Pretend-play/Phone_call",
}

SYSTEM_PROMPT = f"""
Sei un modulo esperto di selezione delle gesture corporee per QT, un robot sociale.

## Input che ricevi
- "user_text": l'utterance dell'utente
- "robot_text": la risposta che QT sta per pronunciare
- "selected_emotion": l'espressione facciale già scelta per questo turno
- "previous_gesture": la gesture usata nel turno precedente (da NON ripetere MAI)

## Il tuo compito
Scegli la gesture che QT dovrebbe eseguire MENTRE pronuncia la risposta.
La gesture deve essere COERENTE con "selected_emotion" e rafforzare il messaggio di "robot_text".

## Gesture disponibili e quando usarle

### GESTURES NEUTRE / CONVERSAZIONALI
| chiave             | quando usarla                                                        |
|--------------------|----------------------------------------------------------------------|
| neutral            | risposta generica, nessun gesto particolare richiesto                |
| show_face          | QT si presenta, attira l'attenzione su se stesso                     |
| show_qt            | QT mostra se stesso con orgoglio                                     |
| show_tablet        | QT indica qualcosa da guardare, informazione visiva                  |
| point_front        | QT indica qualcosa di fronte, direzione, oggetto specifico           |
| show_left          | QT indica a sinistra                                                 |
| show_right         | QT indica a destra                                                   |
| hand_front_hold    | QT chiede attenzione, pausa, "aspetta"                               |
| personal_distance  | argomento di spazio personale, distanza                              |

### GESTURES SOCIALI / SALUTO
| chiave      | quando usarla                                            |
|-------------|----------------------------------------------------------|
| hi          | saluto iniziale, prima interazione                       |
| bye         | congedo formale                                          |
| bye_bye     | congedo più caloroso o giocoso                           |
| send_kiss   | affetto, saluto molto caloroso, è stato espresso affetto |
| kiss        | momento tenero, affettuoso, è stato espresso affetto     |
| clapping    | applauso, congratulazioni, risultato positivo            |
| one_arm_up  | vittoria, entusiasmo, celebrazione                       |
| up_left     | entusiasmo, esultanza                                    |
| up_right    | entusiasmo, esultanza                                    |

### GESTURES EMOTIVE (movimenti corporei abbinati a emozioni)
Usare SOLO se "selected_emotion" corrisponde — rafforzano l'emozione facciale
| chiave              | selected_emotion corrispondente                        |
|---------------------|--------------------------------------------------------|
| emotion_happy       | happy, happy_blinking                                  |
| emotion_hooray      | happy (celebrazione intensa)                           |
| emotion_sad         | sad, cry                                               |
| emotion_angry       | angry                                                  |
| emotion_afraid      | afraid                                                 |
| emotion_disgusted   | disgusted                                              |
| emotion_surprised   | surprised                                              |
| emotion_shy         | shy                                                    |
| emotion_calm        | calming_down, neutral                                  |

### GESTURES GIOCOSE / ESPRESSIVE
| chiave         | quando usarla                                                    |
|----------------|------------------------------------------------------------------|
| monkey         | risposta molto giocosa, buffa, energia alta                      |
| peekaboo       | gioco, sorpresa giocosa, interazione con bambini                 |
| peekaboo_back  | variante di peekaboo                                             |
| challenge      | sfida, proposta, "dai proviamo"                                  |
| swipe_left     | rifiuto, scartare un'idea                                        |
| swipe_right    | approvazione, accettare un'idea                                  |

### GESTURES FISICHE / COMPORTAMENTALI — solo se il contesto lo giustifica
| chiave              | quando usarla                                             |
|---------------------|-----------------------------------------------------------|
| stretching          | stanchezza, pausa, momento di relax                       |
| yawn                | noia, stanchezza (tono ironico)                           |
| sneezing            | contesto malattia, raffreddore                            |
| drink               | sete, pausa, contesto informale                           |
| touch_head          | QT si tocca la testa, ci sta pensando                     |
| touch_head_back     | variante touch_head                                       |
| bored               | noia esplicita (usare con parsimonia)                     |
| breathing_exercise  | rilassamento, mindfulness                                 |
| train               | contesto di esercizio, allenamento                        |

### PRETEND PLAY — solo in contesti di gioco di ruolo espliciti
| chiave             | quando usarla                              |
|--------------------|--------------------------------------------|
| pretend_phone_call | gioco del telefono                         |
| pretend_drive      | gioco della macchina                       |
| pretend_driving    | variante pretend_drive                     |
| pretend_fly        | gioco del volare                           |
| pretend_beep       | robot che fa suoni, gioco tecnologico      |
| pretend_beeping    | variante pretend_beep                      |

## Regole di priorità
1. NON usare sempre la stessa gesture per la stessa emotion.
2. Scegli la gesture più specifica in base a user_text.
3. Evita ripetizione consecutiva della stessa gesture.
4. Le gesture fisiche e pretend play solo se il contenuto le giustifica esplicitamente
5. "neutral" è l'ultima scelta, non la default
6. NON scegliere gesture energiche (clapping, one_arm_up, monkey) se selected_emotion è sad/afraid/cry
7. DEVI evitare assolutamente di scegliere la "previous_gesture". Se si adatta bene, trovane un'altra simile.

## Output
Rispondi ONLY con JSON valido, senza markdown, senza testo aggiuntivo:
{{
  "gesture_key": "chiave_scelta",
  "reason": "1-2 frasi: perché questa gesture è coerente con emozione e robot_text"
}}

## Esempi
emotion: "sad" / user: "ho perso il mio cane" / robot: "Mi dispiace tanto."
→ {{"gesture_key": "emotion_sad", "reason": "Emozione sad → gesture corporea sad rinforza il dispiacere sincero."}}

emotion: "happy" / user: "ho preso 30!" / robot: "Wow, che notizia fantastica!"
→ {{"gesture_key": "emotion_hooray", "reason": "Emozione happy intensa → hooray celebra il risultato con tutto il corpo."}}

emotion: "confused" / user: "come funziona il buco nero?" / robot: "È una domanda complessa..."
→ {{"gesture_key": "touch_head", "reason": "QT ci sta pensando, il gesto di toccarsi la testa rinforza la riflessione."}}

emotion: "showing_smile" / user: "ciao!" / robot: "Ciao, come stai oggi?"
→ {{"gesture_key": "hi", "reason": "Saluto iniziale, gesture hi è il complemento naturale del sorriso sociale."}}

emotion: "neutral" / user: "quante zampe ha un ragno?" / robot: "Un ragno ha otto zampe."
→ {{"gesture_key": "point_front", "reason": "Risposta informativa diretta, point_front dà enfasi alla risposta."}}

Gesture disponibili (usa ESATTAMENTE una di queste chiavi):
{json.dumps(list(AVAILABLE_GESTURES.keys()), ensure_ascii=False, indent=2)}
"""


class GestureSelectorService:

    def __init__(self):
        from engines.openai import OpenAI
        self.ai = OpenAI()
        self.ai.prompts[0] = {"role": "system", "content": SYSTEM_PROMPT}
        self.ai.memory_size = 0

        self.last_gesture = "neutral"

        self.service = rospy.Service(
            '/gesture_selector',
            GestureSelector,
            self.handle_request
        )
        rospy.loginfo("✓ /gesture_selector service ready.")

    def handle_request(self, req):
        user_text        = req.user_text
        robot_text       = req.robot_text
        selected_emotion = req.selected_emotion

        prompt = json.dumps({
            "user_text":        user_text,
            "robot_text":       robot_text,
            "selected_emotion": selected_emotion,
            "previous_gesture": self.last_gesture
        }, ensure_ascii=False)

        self.ai.prompts = [self.ai.prompts[0]]

        try:
            raw = self.ai.generate(prompt)
            if not raw:
                raise ValueError("Empty response from AI")

            parsed = json.loads(raw)
            key    = parsed.get("gesture_key", "neutral")
            reason = parsed.get("reason", "")

            if key not in AVAILABLE_GESTURES:
                rospy.logwarn(f"Unknown gesture key '{key}', falling back to neutral.")
                key = "neutral"

            if key == self.last_gesture and key != "neutral":
                rospy.logwarn(f"L'AI ha ripetuto la gesture '{key}'. Forzo 'show_face' o 'neutral'.")
                # Se l'AI ignora il prompt e si ripete, la modifichiamo noi via codice
                key = "show_face" if self.last_gesture == "hi" else "neutral"
                reason = "Forzatura script Python per evitare ripetizione consecutiva."

            # Aggiorna la memoria con la nuova gesture scelta
            self.last_gesture = key

            selected_gesture = AVAILABLE_GESTURES[key]
            rospy.loginfo(f"Gesture: {key} → '{selected_gesture}' | {reason}")

            return GestureSelectorResponse(gesture_name=selected_gesture, success=True)

        except (json.JSONDecodeError, ValueError, Exception) as e:
            rospy.logerr(f"GestureSelector error: {e}")
            return GestureSelectorResponse(gesture_name="QT/neutral", success=False)


if __name__ == "__main__":
    rospy.init_node('gesture_selector_node')
    GestureSelectorService()
    rospy.spin()