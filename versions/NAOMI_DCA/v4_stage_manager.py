import logging
from typing import Tuple, Dict, Any

from .v4_helper_agent import HelperAgent
from .v4_session_manager import SessionManager
from .v4_logging import log_event

from .v4_prompts import (
    eng_sum_prompt, foc_classify_prompt, evo_sum_prompt, end_session_summary_prompt,STAGE_SUMMARY_PROMPT,
    glue_1_to_2_prompt, glue_2_to_3_prompt, glue_3_to_4_prompt
)
from constants import FOCUSING_INTRO_Q, PLANNING_INTRO_Q, ORDER, MAX_TURNS, MAX_CHARS, MIN_TURNS_BEFORE_LLM


class StageManager:
    """Handles the logic for transitioning between conversation stages."""
    def __init__(self, logger: logging.Logger, helper_agent: HelperAgent, session_manager: SessionManager):
        self.logger = logger
        self.helper_agent = helper_agent
        self.session_manager = session_manager

    def _parse_focus_area(self, response: str) -> str:
        r = response.lower()
        if "diet" in r: return "diet"
        if "exercise" in r or "physical activity" in r: return "exercise"
        return "other"
    

    def _next_stage(self, current_stage: str) -> str | None:
        if current_stage not in ORDER:
            return None
        idx = ORDER.index(current_stage)
        if idx >= len(ORDER) - 1:
            return None
        return ORDER[idx + 1]
    
    def check_for_transition(self, session_id: str, last_user_message: str) -> str | None:
        session_data = self.session_manager.get_session(session_id)
        stage = session_data["stage"]
        
        if stage == "END":
            return None

        next_stage = self._next_stage(stage)
        if not next_stage:
            return None

        num_turns = len(session_data["stage_codes"][stage]) // 2
        transcript = self.session_manager.get_transcript(session_id, stage)
        chars_in_stage = len(transcript)

        # --- DEBUG: Print current state ---
        print(f"[STAGE MGR] Checking transition for stage: {stage} | Turns: {num_turns} | Chars: {chars_in_stage}")

        # 1. Prolonged-stage override (Skip LLM if limits are hit)
        forced_due_to_length = False
        if stage in MAX_TURNS and num_turns >= MAX_TURNS[stage]:
            forced_due_to_length = True
        if stage in MAX_CHARS and chars_in_stage >= MAX_CHARS[stage]:
            forced_due_to_length = True

        # 2. Veto Logic
        is_epe_follow_up = session_data["memory"].get("epe_follow_up_active", False)
        if is_epe_follow_up:
            print("[STAGE MGR] Veto: EPE follow-up active.")
            log_event(self.logger, session_id=session_id, stage=stage,
                      event="stage_transition_delayed", payload={"reason": "EPE follow-up is active."})
            return None

        is_question = self.helper_agent.is_user_question(last_user_message)
        if is_question and not forced_due_to_length:
            print("[STAGE MGR] Veto: User asked a question.")
            log_event(self.logger, session_id=session_id, stage=stage,
                      event="stage_transition_delayed", payload={"reason": "User asked a question."})
            return None

        # 3. Early Exit (Don't ask LLM too early unless forced)
        if not forced_due_to_length and num_turns < MIN_TURNS_BEFORE_LLM.get(stage, 3):
            print(f"[STAGE MGR] Early Exit: Not enough turns ({num_turns}). Skipping LLM eval.")
            return None

        # 4. Determine if we should transition
        wants_transition = False
        reason = ""

        if forced_due_to_length:
            wants_transition = True
            reason = "Forced due to length/turn limits."
            print(f"[STAGE MGR] Evaluation: FORCED transition. Reason: {reason}")
        else:
            print("[STAGE MGR] Asking LLM for transition evaluation...")
            decision = self.helper_agent.should_transition_stage(
                session_id=session_id, 
                stage=stage, 
                transcript=transcript
            )
            wants_transition = decision.get("transition", False)
            reason = decision.get("reason", "No reason parsed.")
            # --- DEBUG: Print LLM decision ---
            print(f"[STAGE MGR] LLM Decision: Transition={wants_transition} | Reason={reason[:60]}...")

        # 5. Execute or Abort
        if not wants_transition:
            log_event(self.logger, session_id=session_id, stage=stage,
                      event="stage_transition_not_triggered",
                      payload={"turns": num_turns, "chars": chars_in_stage, "reason": reason})
            return None
        print(f"[STAGE MGR] >>> TRIGGERING TRANSITION TO: {next_stage} <<<")
        log_event(self.logger, session_id=session_id, stage=stage,
                  event="stage_transition_triggered",
                  payload={
                      "to": next_stage,
                      "forced": forced_due_to_length,
                      "turns": num_turns,
                      "chars": chars_in_stage,
                      "reason": reason
                  })
        return next_stage

    def handle_transition(self, session_id: str, new_stage: str) -> str:
        """
        Generates the transition message for the user.
        The orchestrator is now responsible for committing it to history.
        """
        session_data = self.session_manager.get_session(session_id)
        current_stage = session_data["stage"]
        mem = session_data["memory"]

        # This call still handles resetting the stage and RC.
        self.session_manager.update_stage(session_id, current_stage, new_stage)
    
        transition_msg, glue_summary = None, None
        
        if current_stage == "ENGAGING" and new_stage == "FOCUSING":
            transcript = self.session_manager.get_transcript(session_id, "ENGAGING")
            eng_message = self.helper_agent.summarize_transcript(session_id, "ENGAGING", transcript, eng_sum_prompt)
            glue_summary = self.helper_agent.summarize_transcript(session_id, "ENGAGING", transcript, glue_1_to_2_prompt)
            mem["stage_summaries"]["ENGAGING"] = eng_message
            transition_msg = f"{eng_message}\n\n{FOCUSING_INTRO_Q}"

        elif current_stage == "FOCUSING" and new_stage == "EVOKING":
            transcript = self.session_manager.get_transcript(session_id, "FOCUSING")
            full_transcript = self.session_manager.get_transcript(session_id)
            detected_focus_label = self.helper_agent.summarize_transcript(session_id, "FOCUSING", transcript, foc_classify_prompt)
            glue_summary = self.helper_agent.summarize_transcript(session_id, "ALL", full_transcript, glue_2_to_3_prompt)
            mem["stage_summaries"]["FOCUSING"] = detected_focus_label
            
            msg = "[SUM] You've identified a direction that feels meaningful to you."
            focus_area = self._parse_focus_area(detected_focus_label)
            
            if focus_area == "diet":
                intro = "[QECML+] Why do you want to start by focusing on your diet?"
            elif focus_area == "exercise":
                intro = "[QECML+] Why do you want to start by focusing on physical activity?"
            else:
                intro = "[QECML+] Why do you want to start here?"
            transition_msg = f"{msg} {intro}"

        elif current_stage == "EVOKING" and new_stage == "PLANNING":
            transcript = self.session_manager.get_transcript(session_id, "EVOKING")
            full_transcript = self.session_manager.get_transcript(session_id)
            evo_message = self.helper_agent.summarize_transcript(session_id, "EVOKING", transcript, evo_sum_prompt)
            glue_summary = self.helper_agent.summarize_transcript(session_id, "ALL", full_transcript, glue_3_to_4_prompt)
            mem["stage_summaries"]["EVOKING"] = evo_message
            transition_msg = f"{evo_message}\n\n{PLANNING_INTRO_Q}"

        elif new_stage == "END":
            full_transcript = self.session_manager.get_transcript(session_id)
            llm_generated_closing = self.helper_agent.summarize_transcript(
                session_id, 'ALL', full_transcript, end_session_summary_prompt
            )
            transition_msg = (
                f"[SUM] {llm_generated_closing}\n\n"
                f"Please let the research assistant know that our conversation has come to an end."
            )

        # --- COMMON SIDE-EFFECTS (SIMPLIFIED) ---
        if glue_summary:
            mem["cumulative_sum"] = glue_summary
        
        if transition_msg:
            return transition_msg
        else:
            log_event(
                self.logger, session_id=session_id, stage=new_stage,
                event="no_custom_transition_logic", level=logging.WARNING,
                payload={"from": current_stage, "to": new_stage}
            )
            return f"ERROR HANDLING STAGE TRANSITION - {new_stage.lower()} stage."

