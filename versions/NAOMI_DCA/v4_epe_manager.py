import logging
from datetime import datetime

# Dependencies
from .v4_session_manager import SessionManager
from .v4_helper_agent import HelperAgent
from .v4_logging import log_event

# Utilities (now importing our new, precise helpers)
from .epe_helpers import (
    epe_permission_line, epe_decline_line, epe_append_elicit,
    sanitize_prompt_leakage, extract_epe_intent, strip_leading_code_tag
)
from utils.postprocessing import remove_semantic_repetition

class EPEManager:
    """Manages all logic for the Elicit-Provide-Elicit pattern."""

    def __init__(self, logger: logging.Logger, session_manager: SessionManager, helper_agent: HelperAgent):
        self.logger = logger
        self.session_manager = session_manager
        self.helper_agent = helper_agent

    def resolve_pending(self, session_key: str, stage: str, client_code: str, user_reply: str):
        """Handles the user's 'yes/no' reply using supervisor-approved wording."""
        session_data = self.session_manager.get_session(session_key)
        pending = session_data["memory"].pop("epe", {}) # Use pop to clear the EPE state
        intent = pending.get("intent", "GINFO+")
        
        log_event(self.logger, session_id=session_key, stage=stage, event="epe_resolving_intent", payload={"intent": intent})


        # This call now only returns 'yes' or 'no'. The 'maybe' path is gone.
        verdict = self.helper_agent.classify_yes_no(session_key, user_reply)
        
        if verdict == "yes":
            # Provide the stored info and append the required follow-up.
            log_event(self.logger, session_id=session_key, stage=stage, event="epe_verdict_yes", payload={"path": "provide"})
            provide_text = sanitize_prompt_leakage(pending.get("queued_provide", "...I lost my train of thought."))
            final_elicit = epe_append_elicit()
            response_text = f"{provide_text} {final_elicit}"
            therapist_code = intent

            # --- NEW LOGIC: Set the 'Do Not Disturb' flag ---
            # This tells the orchestrator that the next turn is a protected EPE follow-up.
            session_data["memory"]["epe_follow_up_active"] = True
            log_event(self.logger, session_id=session_key, stage=stage, event="epe_follow_up_activated")
            # --- END OF NEW LOGIC ---
        elif verdict == "no":
            log_event(self.logger, session_id=session_key, stage=stage, event="epe_verdict_no", payload={"path": "decline"})
            # Use the specific decline message.
            response_text = epe_decline_line()
            therapist_code = "EPE"

        # --- "TWO BOOKS" LOGIC (Preserved) ---
        # The Official Transcript gets the REAL code for accuracy.
        self.session_manager.add_to_history(session_key, stage, "ai", response_text)
        self.session_manager.push_to_rc(session_key, "assistant", response_text)
        # The Stage Pacing Counter gets a PLACEHOLDER so it doesn't affect transitions.
        self.session_manager.commit_codes(session_key, stage, client_code, "EPE_TURN")
        
        return {"response": response_text, "code": therapist_code, "stage": stage, "client_code": client_code}

    def vet_and_finalize(self, session_key: str, stage: str, client_code: str, therapist_code: str, response_text: str):
        """Cleans, vets for accidental advice, and saves the final response."""
        session_data = self.session_manager.get_session(session_key)
        final_response = response_text
        final_therapist_code = therapist_code

        # --- NEW LOGIC: Clear any old follow-up flags ---
        # A normal turn or the start of a new EPE cycle should always clear the flag.
        if "epe_follow_up_active" in session_data["memory"]:
            session_data["memory"].pop("epe_follow_up_active")
            log_event(self.logger, session_id=session_key, stage=stage, event="epe_follow_up_cleared")
        # --- END OF NEW LOGIC ---

        # EPE Safety Net: Check for spontaneous advice.
        intent = extract_epe_intent(final_response)
        if intent:
            log_event(self.logger, session_id=session_key, stage=stage, event="epe_safety_net_triggered", payload={"intent": intent})
            # DO NOT STRIP THE CODE 
            provide_body = final_response
            session_data["memory"]["epe"] = {
                "intent": intent, "asked_at": datetime.now().isoformat(),
                "queued_provide": provide_body,
            }
            # This now uses the correct, supervisor-approved wording.
            final_response = epe_permission_line(intent)
            final_therapist_code = "EPE"
            # This turn initiated the EPE, so we DO count its code.
            self.session_manager.commit_codes(session_key, stage, client_code, final_therapist_code)
        else:
            final_response = sanitize_prompt_leakage(final_response)
            # This is a normal turn, so we log its code as usual.
            self.session_manager.commit_codes(session_key, stage, client_code, final_therapist_code)
            
        final_response = remove_semantic_repetition(final_response)

        # Commit to transcript and RC
        self.session_manager.push_to_rc(session_key, "assistant", final_response)
        self.session_manager.add_to_history(session_key, stage, "ai", final_response)

        return {
            "response": final_response, "code": final_therapist_code,
            "stage": stage, "client_code": client_code,
        }
