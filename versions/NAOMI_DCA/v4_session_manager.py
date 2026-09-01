import logging
from datetime import datetime
from typing import Dict, Any, List

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory

from constants import STAGE_NAMES
from .v4_logging import log_event

def default_memory() -> Dict[str, Any]:
    return {
        "stable": [], "cumulative_sum": "", "stage_summaries": {},
        "rc": [], "epe": None,
    }

class SessionManager:
    """Manages all session data and history for the application."""
    def __init__(self, logger: logging.Logger):
        self._store: Dict[str, Dict[str, Any]] = {}
        self.logger = logger

    def get_session(self, session_id: str, initial_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retrieves a session, or creates and seeds a new one if it doesn't exist."""
        is_new = session_id not in self._store
        if is_new:
            self._store[session_id] = self._create_base_session(session_id)
            if initial_history:
                self._seed_history(session_id, initial_history)
        return self._store[session_id]

    def _create_base_session(self, session_id: str) -> Dict[str, Any]:
        """Creates a new, empty session object with default values."""
        log_event(self.logger, session_id=session_id, stage="ENGAGING", event="session_created")
        return {
            "stage": "ENGAGING",
            "start_time": datetime.now(),
            "stage_codes": {stage: [] for stage in STAGE_NAMES},
            "memory": default_memory(),
            "history": {
                "full": InMemoryChatMessageHistory(),
                "stages": {stage: InMemoryChatMessageHistory() for stage in STAGE_NAMES},
            }
        }

    def _seed_history(self, session_id: str, initial_history: List[Dict[str, Any]]):
        """Populates a new session with an existing transcript."""
        log_event(
            self.logger, session_id=session_id, stage="ENGAGING",
            event="seeding_initial_history", payload={"num_messages": len(initial_history)}
        )
        for message in initial_history:
            role = message.get('role')
            content = (message.get('content') or "").strip()
            if not content or not role:
                continue
            
            # The role from history might be 'assistant', which we map to 'ai'
            ai_role = "ai" if role == "assistant" else role
            
            # Add to both the official transcript and the rolling context for the first turn
            self.add_to_history(session_id, "ENGAGING", ai_role, content)
            self.push_to_rc(session_id, ai_role, content)

    def add_to_history(self, session_id: str, stage: str, role: str, message: str):
        """Adds a message to both the full and stage-specific transcripts."""
        hist = self.get_session(session_id)["history"]
        if role == "user":
            hist["full"].add_user_message(message)
            hist["stages"][stage].add_user_message(message)
        elif role == "ai":
            hist["full"].add_ai_message(message)
            hist["stages"][stage].add_ai_message(message)

    def get_transcript(self, session_id: str, stage: str = None) -> str:
        """Generates a formatted transcript from history."""
        history_data = self.get_session(session_id)["history"]
        messages = history_data["stages"].get(stage, InMemoryChatMessageHistory()).messages if stage else history_data["full"].messages
        
        lines = [f"Patient: {msg.content.strip()}" if isinstance(msg, HumanMessage) else f"Counselor: {msg.content.strip()}" for msg in messages]
        transcript = "\n\n".join(lines)
        
        # log_event(
        #     self.logger, session_id=session_id, stage=stage or "ALL", 
        #     event="transcript_generated", payload={"chars": len(transcript)}
        # )
        return transcript

    def update_stage(self, session_id: str, old_stage: str, new_stage: str):
        """Updates the stage and resets the rolling context (RC)."""
        session = self.get_session(session_id)
        session["stage"] = new_stage
        session["memory"]["rc"] = []
        log_event(
            self.logger, session_id=session_id, stage=new_stage, 
            event="stage_switched", payload={"from": old_stage, "to": new_stage}
        )

    def push_to_rc(self, session_id: str, role: str, content: str):
        """Appends a message to the session's rolling context."""
        session = self.get_session(session_id)
        session["memory"]["rc"].append({"role": role, "content": content.strip()})
        log_event(
            self.logger, session_id=session_id, stage=session['stage'], 
            event="rc_pushed", payload={"role": role, "rc_len": len(session["memory"]["rc"])}
        )

    def commit_codes(self, session_id: str, stage: str, client_code: str, therapist_code: str):
        """Adds the client and therapist codes to the stage history."""
        session = self.get_session(session_id)
        session["stage_codes"][stage].append(("C", client_code))
        session["stage_codes"][stage].append(("T", therapist_code))

