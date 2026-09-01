from typing import List, Dict, Any # Import necessary types

# Import all the custom modules that make up the application
from .v4_session_manager import SessionManager
from .v4_agent import TherapistAgent
from .v4_helper_agent import HelperAgent
from .v4_stage_manager import StageManager
from .v4_logging import get_logger, log_event
from.v4_epe_manager import EPEManager
from .v4_safety import LlamaGuard3

# Import utilities and constants
from .v4_code_selector import select_next_code

ENABLE_SAFETY = True  # Change to False to disable all LlamaGuard3 checks

safety = LlamaGuard3() if ENABLE_SAFETY else None


# --- Global Instances ---
logger = get_logger()
session_manager = SessionManager(logger)
helper_agent = HelperAgent(logger)
therapist_agent = TherapistAgent(logger)
stage_manager = StageManager(logger, helper_agent, session_manager)
epe_manager = EPEManager(logger, session_manager, helper_agent)




# --- NEW, MORE EFFICIENT WARMUP FUNCTION ---
def warmup_v4():
    """
    A dedicated function to handle the warmup signal. It directly 'pings' the
    LLMs inside the agents to trigger model loading without running the full
    conversational logic.
    """
    try:
        log_event(logger, session_id="warmup", stage="WARMUP", event="warmup_started")
        # Ping the main therapist model to trigger its loading.
        therapist_agent.model.invoke("ping")
        # Ping the helper/summarizer model to trigger its loading.
        helper_agent.llm.invoke("ping")
        log_event(logger, session_id="warmup", stage="WARMUP", event="warmup_finished")
        print("Warmup pings sent. Agents should be ready.")
    except Exception as e:
        log_event(logger, "warmup", "WARMUP", "warmup_failed", {"error": str(e)})
        print(f"Error during warmup: {e}")
# --- END OF NEW FUNCTION ---



def call_v4(question: str, session_key: str, initial_history: List[Dict[str, Any]] = None):
    """
    The main entry point for the application. It orchestrates the entire
    response generation process for a single turn.
    """

    # --- 0. INPUT GUARDRAIL ---
    if ENABLE_SAFETY and safety:
        is_safe_input, in_category = safety.check(question)
        if not is_safe_input:
            return {
                "response": "I'm here to support your health goals, but I can't discuss that. How else can I help?",
                "code": f"BLOCK_IN_{in_category}",
                "stage": "SAFETY_STOP"
            }

    # --- 1. SETUP & INITIAL LOGGING ---
    # Pass initial_history to the session manager. It will be used only if the session is new.
    session_data = session_manager.get_session(session_key, initial_history=initial_history)
    current_stage = session_data["stage"]

    # --- Guardrail for sessions that have already ended ---
    if current_stage == "END":
        return {
            "response": "Our session has concluded. Please let the research assistant know that you are finished.",
            "code": "SESSION_ENDED",
            "stage": "END",
            "client_code": "N/A"
        }

    
    # Log the incoming user message
    session_manager.push_to_rc(session_key, "user", question)
    session_manager.add_to_history(session_key, current_stage, "user", question)

    # Predict the client code for this user message
    client_code = helper_agent.predict_client_code(session_key, question)

    # --- 2. PRIORITY 1: RESOLVE PENDING EPE ---
    if session_data["memory"].get("epe"):
        return epe_manager.resolve_pending(session_key, current_stage, client_code, question)

    # --- 3. PRIORITY 2: HANDLE STAGE TRANSITION ---
    new_stage = stage_manager.check_for_transition(session_key, question)
    if new_stage:
        transition_response = stage_manager.handle_transition(session_key, new_stage)
        old_stage = current_stage
        
        # --- SPECIAL HANDLING FOR THE "END" STATE ---
        if new_stage == "END":
            # The session is over. We commit the final turn's codes to the PREVIOUS stage.
            session_manager.commit_codes(session_key, old_stage, client_code, "SESSION_END")
            session_manager.add_to_history(session_key, old_stage, "ai", transition_response)
            session_manager.push_to_rc(session_key, "assistant", transition_response)
            
            # The stage in the final response payload should correctly be 'END'.
            return {"response": transition_response, "code": "SESSION_END", "stage": "END", "client_code": client_code}
       
        session_manager.commit_codes(session_key, new_stage, client_code, "TRANSITION")
        return {"response": transition_response, "code": "TRANSITION", "stage": new_stage, "client_code": client_code}

    # --- 4. PRIORITY 3: NORMAL RESPONSE GENERATION ---
    # The proactive EPE trigger has been removed. We now follow a single, unified path.
    
    # Step 4a: Always select the best code for the current situation.
    therapist_code = select_next_code(session_data)

    response_text = ""

    response_text = therapist_agent.generate_response(
        session_key, session_data, question, therapist_code
    )

    # --- 3. OUTPUT GUARDRAIL (Response Shield) ---
    # Only run the check if safety is explicitly enabled
    if ENABLE_SAFETY and safety:
        is_safe_out, out_cat = safety.check(question, response_text)
        
        # If the response is unsafe, immediately use the safe pivot (no retries)
        if not is_safe_out:
            logger.warning(f"Safety check failed (Category: {out_cat}). Using safe pivot.")
            print(f"Safety check failed (Category: {out_cat}). Using safe pivot.")
            response_text = "I want to make sure I'm giving you the best support. Let's focus back on your thoughts about lifestyle changes."
        
    # --- 6. FINALIZE AND RETURN ---
    # The `vet_and_finalize` function will now act as our REACTIVE EPE trigger.
    # It will inspect the `response_text` and initiate the EPE flow only if
    # the AI actually produced a GINFO+ or ADV+ response.
    return epe_manager.vet_and_finalize(
        session_key, current_stage, client_code, therapist_code, response_text
    )

