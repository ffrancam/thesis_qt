#!/usr/bin/env python3
import re
import json
import rospy
from thesis_qt.srv import EvaluateResponse, EvaluateResponseResponse
from engines.openai import OpenAI

class ResponseEvaluatorService:
    def __init__(self):
        rospy.init_node('response_evaluator_node')
        self.aimodel = OpenAI()
        rospy.Service('/response_evaluator', EvaluateResponse, self.handle)
        print("✓ Response Evaluator Service ready!")
        rospy.spin()

    # ------------------------------------------------------------------ #
    def handle(self, req):
        print(f"\n=== EvaluateResponse ===")
        print(f"  question      : {req.question}")
        print(f"  correct_answer: {req.correct_answer}")
        print(f"  description   : {req.description}")
        print(f"  user_res      : {req.user_res}")
        print(f"  is_last_attempt: {req.is_last_attempt}")

        is_correct, correct_answer = self._check_with_ai(
            req.question, req.user_res, req.correct_answer, req.description
        )
        feedback = self._generate_feedback(
            req.question, correct_answer,
            req.user_res, is_correct, req.is_last_attempt
        )

        print(f"  → is_correct  : {is_correct}")
        print(f"  → feedback    : '{feedback}'")
        return EvaluateResponseResponse(is_correct=is_correct, robot_feedback=feedback)

    # ------------------------------------------------------------------ #
    def _check_with_ai(self, question, user_res, correct_answer, description=""):
        extra_context = (
            f" Contesto aggiuntivo: '{description}'." if description else ""
        )

        if not correct_answer:
            # Chiediamo all'AI di valutare E restituire la risposta corretta in JSON
            prompt = (
                f"Sei un valutatore scolastico. "
                f"Domanda: '{question}'.{extra_context} "
                f"Risposta dell'utente: '{user_res}'. "
                f"Rispondi ESCLUSIVAMENTE con un JSON valido, nessun testo prima o dopo. "
                f"Formato: {{\"correct\": \"SI\" o \"NO\", \"answer\": \"<risposta corretta breve>\"}}. "
                f"Considera corretta se semanticamente equivalente o simile per errori ASR."
            )
            result = []
            self.aimodel.generate(prompt, lambda txt: result.append(txt))
            raw = ''.join(result).strip()
            print(f"  [AI combined] → '{raw}'")

            try:
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                data = json.loads(match.group())
                correct_answer = data.get('answer', '')
                is_correct = data.get('correct', 'NO').upper() == 'SI'
            except Exception:
                correct_answer = ''
                is_correct = False
                rospy.logwarn(f"JSON parse failed on: '{raw}'")

            return is_correct, correct_answer

        # Caso con risposta attesa nota
        prompt = (
            f"Rispondi ESCLUSIVAMENTE con SI oppure NO (senza accento, senza punteggiatura). "
            f"Domanda: '{question}'. Risposta attesa: '{correct_answer}'.{extra_context} "
            f"Risposta dell'utente: '{user_res}'. "
            f"Considera corretta se semanticamente equivalente o foneticamente simile. "
            f"La risposta è accettabile?"
        )
        result = []
        self.aimodel.generate(prompt, lambda txt: result.append(txt))
        response = ''.join(result).strip().upper()
        print(f"  [AI check] → '{response}'")
        return 'SI' in response, correct_answer

    # ------------------------------------------------------------------ #
    def _generate_feedback(self, question, correct_answer, user_res,
                           is_correct, is_last_attempt):
        if is_correct:
            instruction = (
                f"Il bambino ha risposto correttamente '{user_res}' "
                f"alla domanda '{question}'. "
                f"Fai i complimenti in modo entusiasta e conferma la risposta. Se vuoi aggiungici una curiosità formativa correlato alla risposta."
            )
        elif is_last_attempt:
            instruction = (
                f"Il bambino ha risposto '{user_res}' "
                f"ma la risposta corretta era '{correct_answer}'. "
                f"Di' che non importa, rivela gentilmente la risposta corretta."
            )
        else:
            instruction = (
                f"Il bambino ha risposto '{user_res}' ma non è corretto. "
                f"Incoraggia a riprovare senza svelare la risposta '{correct_answer}'. Se vuoi aggiungi un indizio o suggerimento per aiutarlo a trovare la risposta corretta. Fai molta attenzione a non rivelare la risposta con l'indizio!"
            )

        prompt = (
            f"Sei QT, un robot educativo simpatico per bambini. "
            f"{instruction} "
            f"Rispondi in italiano con massimo 2 frasi brevi e incoraggianti. "
            f"Parla direttamente al bambino, senza prefissi o spiegazioni."
        )
        result = []
        self.aimodel.generate(prompt, lambda txt: result.append(txt))
        feedback = ''.join(result).strip()
        if not feedback:
            feedback = "Ottimo lavoro!" if is_correct else "Non è corretto, riprova!"
        return feedback


if __name__ == '__main__':
    try:
        ResponseEvaluatorService()
    except rospy.ROSInterruptException:
        pass