import time
import json
import rospy
import requests

class Groq:
    def __init__(self):
        # 1. Prendi la chiave API direttamente dai parametri ROS (dal tuo file YAML)
        self.api_key = rospy.get_param("/offline_conversation/groq/api_key", "")
        
        # Se la chiave è vuota, stampa un errore visibile nel terminale ROS
        if not self.api_key or self.api_key == "":
            rospy.logerr("ERRORE CRITICO: API Key di Groq mancante! Controlla il file YAML.")

        # 2. Prendi gli altri parametri dal YAML
        self.model = rospy.get_param("/offline_conversation/groq/model", "llama-3.3-70b-versatile")
        self.memory_size = rospy.get_param("/offline_conversation/groq/memory_size", 10)
        self.system_prompt = rospy.get_param("/offline_conversation/groq/prompt", "Sei un robot amichevole che parla in italiano. Rispondi in modo conciso e naturale.")
        
        # 3. Inizializza la memoria con il prompt di sistema
        self.prompts = [{"role": "system", "content": self.system_prompt}]

    def create_prompt(self, user_prompt):
        # Aggiunge la nuova domanda dell'utente
        self.prompts.append({"role": "user", "content": user_prompt})
        
        # Gestione memoria: manteniamo il system prompt (indice 0) e cancelliamo le chat vecchie
        if self.memory_size > 0 and len(self.prompts) > (self.memory_size * 2 + 1):
            self.prompts.pop(1) # Rimuove vecchia domanda utente
            self.prompts.pop(1) # Rimuove vecchia risposta robot
            
        return self.prompts

    def generate(self, message, sentence_callback=None):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "messages": self.create_prompt(message),
                    "temperature": rospy.get_param("/offline_conversation/groq/temperature", 0.7),
                    # Prendo anche max_tokens dal YAML (se esiste, altrimenti default 4096)
                    "max_tokens": rospy.get_param("/offline_conversation/groq/max_token_length", 4096)
                }
                
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    rospy.logerr(f"ERRORE API GROQ (Codice {response.status_code}):\n{response.text}")
                    response.raise_for_status()
                    
                data = response.json()
                text_all = data["choices"][0]["message"]["content"]
                
                # Aggiungiamo la risposta alla memoria
                self.prompts.append({"role": "assistant", "content": text_all})

                # Logica di divisione in frasi per far parlare il robot pezzo per pezzo
                max_sentence = rospy.get_param("/offline_conversation/groq/max_sentence", 2)
                sentence_count = 0
                buff = text_all
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
                    rospy.logwarn("Hai parlato troppo in fretta, Groq ti chiede di attendere 2 secondi...")
                    time.sleep(2)
                else:
                    rospy.logerr(f"Errore HTTP: {e}")
                    self.prompts.pop() # Rimuove l'ultima domanda che ha fallito
                    return None
            except Exception as e:
                rospy.logerr(f"Errore generico: {e}")
                if self.prompts[-1]["role"] == "user":
                    self.prompts.pop()
                return None
                
        rospy.logerr("Troppi tentativi falliti con Groq.")
        return None

    def extract_sentence(self, buff):
        delimiters = ".!?;\n"
        index = None
        for char in buff:
            if char in delimiters:
                index = buff.index(char)
                break
        if index is None:
            return None, buff
        extracted = buff[:index+1].strip().replace('*', '').replace('/', ' ')
        remaining = buff[index+1:].strip().replace('*', '').replace('/', ' ')
        return extracted, remaining