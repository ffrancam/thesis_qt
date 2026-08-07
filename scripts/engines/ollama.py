import json
import openai
import rospy

class Ollama:
    def __init__(self):
        openai.api_key = 'ollama'
        openai.api_base = rospy.get_param("/offline_conversation/ollama/api_base", 'http://localhost:11434/v1')
        self.prompts = []
        self.model = rospy.get_param("/offline_conversation/ollama/model", 'phi3')
        self.memory_size = rospy.get_param("/offline_conversation/ollama/memory_size", 0)
        self.max_token_length = rospy.get_param("/offline_conversation/ollama/max_token_length", 4096)
        self.system_prompt = rospy.get_param("/offline_conversation/ollama/prompt", "")

    def create_prompt(self, user_prompt):
        if len(user_prompt) > self.max_token_length:
            user_prompt = user_prompt[:self.max_token_length]
        if not self.prompts:
            self.prompts.append({"role": "system", "content": self.system_prompt})
        self.prompts.append({'role': 'user', 'content': user_prompt})
        if self.memory_size > 0 and len(self.prompts) > self.memory_size:
            self.prompts.pop(1)
        while len(json.dumps(self.prompts)) > self.max_token_length:
            self.prompts.pop(1)
        return self.prompts

    def generate(self, message, sentence_callback=None):
        try:
            completion = openai.ChatCompletion.create(
                model=self.model,
                messages=self.create_prompt(message),
                stream=True,
                temperature=rospy.get_param("/offline_conversation/ollama/temperature", 0.8),
                frequency_penalty=rospy.get_param("/offline_conversation/ollama/frequency_penalty", 0.6),
                presence_penalty=rospy.get_param("/offline_conversation/ollama/presence_penalty", 0.6)
            )

            max_sentence = rospy.get_param("/offline_conversation/ollama/max_sentence", 0)
            response = ""
            text_all = ""
            sentence_count = 0
            stopped = False
            for chunk in completion:
                delta = chunk["choices"][0]["delta"]
                content = delta.get('content')
                if content:
                    response += content
                    text_all += content
                sentence, response = self.extract_sentence(response)
                if sentence and sentence_callback:
                    sentence_callback(sentence)
                    sentence_count += 1
                    if max_sentence > 0 and sentence_count >= max_sentence:
                        stopped = True
                        break
            if not stopped and response and sentence_callback:
                sentence_callback(response)
            self.prompts.append({"role": "assistant", "content": text_all})
            return text_all
        except Exception as e:
            print(e)
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