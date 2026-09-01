# v4_helper_agent.py
import logging
from langchain_ollama import OllamaLLM
import re
from .v4_prompts import CLIENT_CLASSIFICATION_PROMPT
from constants import USR_CODES
from .v4_logging import log_event

class HelperAgent:
    """A vanilla LLM agent for performing backend utility tasks like summarization and classification."""
    def __init__(self, logger: logging.Logger, model_name: str = "llama3.1:70b"):
        self.logger = logger
        self.llm = OllamaLLM(model=model_name)

    def is_user_question(self, user_input: str) -> bool:
        """
        Uses a simple, robust check to see if the user's last message is a question.
        """
        # A simple keyword and punctuation check is often more reliable for this
        # than a full LLM classification and avoids unnecessary API calls.
        text = user_input.strip()
        if not text:
            return False
        
        # Check for a question mark
        if text.endswith('?'):
            return True
        
        # Check for common question-starting words
        question_starters = [
            "who", "what", "when", "where", "why", "how",
            "can you", "could you", "would you", "do you", "is there"
        ]
        if any(text.lower().startswith(starter) for starter in question_starters):
            return True
            
        return False

    def predict_client_code(self, session_id: str, user_input: str) -> str:
        """Classifies the client's message using the agent's LLM."""
       
        prompt = CLIENT_CLASSIFICATION_PROMPT.format(message=user_input)
        response = self.llm.invoke(prompt)
        raw = response.strip().upper()

        code = "NONE" # Default value
        for c in USR_CODES:
            if c in raw:
                code = c
                break
        
        log_event(
            self.logger, session_id=session_id, stage="========",
            event="client_code_predicted", payload={"code": code}
        )
        return code

    def summarize_transcript(self, session_id: str, stage: str, transcript: str, prompt_template) -> str:
        """Uses the LLM for stage summaries."""
        log_event(
            self.logger, session_id=session_id, stage=stage,
            event="summarization_start"
        )
        prompt = prompt_template.format(transcript=transcript)
        response = self.llm.invoke(prompt)
        return response.strip()

    def classify_yes_no(self, session_id: str, user_text: str) -> str:
        """
        Classifies a user's reply as 'yes' or 'no' using a robust two-tiered approach.
        1. A fast regex check for common, unambiguous affirmations and negations.
        2. A fallback to an LLM for more nuanced replies.
        Defaults to 'yes' if the LLM is uncertain, to prevent conversational loops.
        """
        cleaned_text = user_text.strip().lower()

        # Tier 1: Regex for common patterns to provide a fast and reliable answer.
        yes_patterns = r'\b(yes|yeah|yep|yup|sure|ok|okay|sounds good|absolutely|definitely)\b'
        no_patterns = r'\b(no|nope|nah|not really|i don\'t think so)\b'

        if re.search(yes_patterns, cleaned_text, re.IGNORECASE):
            log_event(self.logger, session_id=session_id, stage="========", event="yes_no_classified_regex", payload={"verdict": "yes"})
            return "yes"
        if re.search(no_patterns, cleaned_text, re.IGNORECASE):
            log_event(self.logger, session_id=session_id, stage="========", event="yes_no_classified_regex", payload={"verdict": "no"})
            return "no"

        # Tier 2: Fallback to LLM for nuanced cases, forcing a YES/NO choice.
        prompt = f"""You are classifying a short user reply to a 'yes/no' question. Rules: - Reply with exactly ONE WORD: YES or NO. User reply: \"\"\"{user_text.strip()}\"\"\""""
        try:
            out = self.llm.invoke(prompt)
            tok = out.strip().split()[0].upper().strip(".,!?:;\"'`()[]")
            if tok in {"YES", "NO"}:
                verdict = tok.lower()
                log_event(self.logger, session_id=session_id, stage="========", event="yes_no_classified_llm", payload={"verdict": verdict})
                return verdict
        except Exception as e:
            log_event(self.logger, session_id=session_id, stage="========", event="yes_no_classification_failed", payload={"error": str(e)}, level=logging.WARNING)
        
        # Default to 'yes' if LLM classification fails or is ambiguous to prevent loops.
        log_event(self.logger, session_id=session_id, stage="========", event="yes_no_classification_defaulted", payload={"verdict": "yes"})
        return "no"


    # New transition logic!
    def should_transition_stage(self, session_id: str, stage: str, transcript: str) -> dict:
        """
        Uses the LLM to determine if the motivational interviewing goals of the 
        current stage have been met. Returns a dictionary with the decision and reason.
        """
        log_event(self.logger, session_id=session_id, stage=stage, event="llm_transition_eval_start")

        # NOTE: You will need to create these prompts in v4_prompts.py
        from .v4_prompts import ENG_TRANS_PROMPT, FOC_TRANS_PROMPT, EVO_TRANS_PROMPT, PLN_TRANS_PROMPT

        prompts = {
            "ENGAGING": ENG_TRANS_PROMPT,
            "FOCUSING": FOC_TRANS_PROMPT,
            "EVOKING": EVO_TRANS_PROMPT,
            "PLANNING": PLN_TRANS_PROMPT
        }

        prompt_template = prompts.get(stage)
        if not prompt_template:
            return {"transition": False, "reason": "No prompt template found for stage."}

        # Append a strict formatting rule to the prompt to enforce consistency
        format_instruction = (
            "\n\nEvaluate the transcript above. Provide your answer in EXACTLY this format:\n"
            "DECISION: [YES or NO]\n"
            "REASON: [A brief 1-sentence explanation of why the goals are/are not met]"
        )
        
        prompt = prompt_template.format(transcript=transcript) + format_instruction

        try:
            response = self.llm.invoke(prompt).strip()

            # Robust parsing of the text output
            is_transition = False
            reason = "Failed to parse a clear reason from the model."

            response_upper = response.upper()
            if "DECISION: YES" in response_upper:
                is_transition = True
            elif "YES" in response_upper[:15]: # Fallback if it slightly ignores formatting
                is_transition = True

            reason_split = response.split("REASON:")
            if len(reason_split) > 1:
                reason = reason_split[1].strip()
            else:
                reason = response.replace("\n", " ").strip()[:150] # Grab whatever it generated just in case

            log_event(self.logger, session_id=session_id, stage=stage, 
                      event="llm_transition_eval_done", payload={"decision": is_transition, "reason": reason})
            
            return {"transition": is_transition, "reason": reason}

        except Exception as e:
            log_event(self.logger, session_id=session_id, stage=stage, 
                      event="llm_transition_eval_error", payload={"error": str(e)}, level=logging.WARNING)
            return {"transition": False, "reason": f"System error: {str(e)}"}