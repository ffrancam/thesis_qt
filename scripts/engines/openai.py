import time
import rospy
import requests


class OpenAI:
    def __init__(self):
        # 1. Prendi la chiave API dai parametri ROS (dal file YAML)
        self.api_key = rospy.get_param("/offline_conversation/openai/api_key", "")

        if not self.api_key or self.api_key == "":
            rospy.logerr("ERRORE CRITICO: API Key di OpenAI mancante! Controlla il file YAML.")

        # 2. Prendi gli altri parametri dal YAML
        self.model        = rospy.get_param("/offline_conversation/openai/model",          "gpt-4o-mini")
        self.memory_size  = rospy.get_param("/offline_conversation/openai/memory_size",    10)
        self.system_prompt = rospy.get_param(
            "/offline_conversation/openai/prompt",
            "Sei un robot amichevole che parla in italiano. Rispondi in modo conciso e naturale."
        )
        # Base URL opzionale: utile per Azure OpenAI o proxy compatibili
        self.api_base = rospy.get_param(
            "/offline_conversation/openai/api_base",
            "https://api.openai.com/v1"
        ).rstrip("/")

        # 3. Inizializza la memoria con il prompt di sistema
        self.prompts = [{"role": "system", "content": self.system_prompt}]

    # ------------------------------------------------------------------
    # Gestione memoria (identica a Groq)
    # ------------------------------------------------------------------
    def create_prompt(self, user_prompt):
        self.prompts.append({"role": "user", "content": user_prompt})

        # Mantieni il system prompt (indice 0) e scorri la finestra
        if self.memory_size > 0 and len(self.prompts) > (self.memory_size * 2 + 1):
            self.prompts.pop(1)  # Rimuove vecchia domanda utente
            self.prompts.pop(1)  # Rimuove vecchia risposta robot

        return self.prompts

    # ------------------------------------------------------------------
    # Chiamata API
    # ------------------------------------------------------------------
    def generate(self, message, sentence_callback=None):
        max_retries = 3

        for attempt in range(max_retries):
            try:
                url = f"{self.api_base}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type":  "application/json",
                }
                payload = {
                    "model":       self.model,
                    "messages":    self.create_prompt(message),
                    "temperature": rospy.get_param("/offline_conversation/openai/temperature",      0.5),
                    "max_tokens":  rospy.get_param("/offline_conversation/openai/max_token_length", 300),
                }

                # Parametri opzionali (ignorati se non presenti nel YAML)
                freq_pen = rospy.get_param("/offline_conversation/openai/frequency_penalty", None)
                pres_pen = rospy.get_param("/offline_conversation/openai/presence_penalty",  None)
                if freq_pen is not None:
                    payload["frequency_penalty"] = freq_pen
                if pres_pen is not None:
                    payload["presence_penalty"]  = pres_pen

                response = requests.post(url, headers=headers, json=payload, timeout=30)

                if response.status_code != 200:
                    rospy.logerr(f"ERRORE API OPENAI (Codice {response.status_code}):\n{response.text}")
                    response.raise_for_status()

                data     = response.json()
                text_all = data["choices"][0]["message"]["content"]

                # Aggiungi la risposta alla memoria
                self.prompts.append({"role": "assistant", "content": text_all})

                # Divisione in frasi (identica a Groq)
                max_sentence   = rospy.get_param("/offline_conversation/openai/max_sentence", 2)
                sentence_count = 0
                buff           = text_all

                while buff:
                    sentence, buff = self.extract_sentence(buff)
                    if sentence and sentence_callback:
                        sentence_callback(sentence)
                        sentence_count += 1
                        if max_sentence > 0 and sentence_count >= max_sentence:
                            break
                    elif not sentence:
                        if buff and sentence_callback:
                            sentence_callback(buff)
                        break

                return text_all

            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    rospy.logwarn("Rate limit OpenAI raggiunto, attendo 5 secondi...")
                    time.sleep(5)
                else:
                    rospy.logerr(f"Errore HTTP OpenAI: {e}")
                    self.prompts.pop()  # Rimuove l'ultima domanda che ha fallito
                    return None
            except requests.exceptions.Timeout:
                rospy.logwarn(f"Timeout OpenAI (tentativo {attempt + 1}/{max_retries})...")
                time.sleep(2)
            except Exception as e:
                rospy.logerr(f"Errore generico OpenAI: {e}")
                if self.prompts and self.prompts[-1]["role"] == "user":
                    self.prompts.pop()
                return None

        rospy.logerr("Troppi tentativi falliti con OpenAI.")
        return None

    # ------------------------------------------------------------------
    # Estrazione frase (identica a Groq)
    # ------------------------------------------------------------------
    def extract_sentence(self, buff):
        delimiters = ".!?;\n"
        index      = None
        for char in buff:
            if char in delimiters:
                index = buff.index(char)
                break
        if index is None:
            return None, buff
        extracted  = buff[:index + 1].strip().replace("*", "").replace("/", " ")
        remaining  = buff[index + 1:].strip().replace("*", "").replace("/", " ")
        return extracted, remaining