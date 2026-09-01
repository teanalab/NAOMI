# transcript_logger.py
from __future__ import annotations

import os
import glob

from utils.time_utils import get_current_eastern, get_eastern_prefix

V4_TRANSCRIPT_DIR = os.environ.get("V4_TRANSCRIPT_DIR", "./data/v4_transcripts")
TEST_TRANSCRIPT_DIR = os.environ.get("TEST_TRANSCRIPT_DIR", "./data/test_transcripts")

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _get_transcript_filename(user_id: str) -> str:
    """
    Creates a new, human-readable filename for a user session.
    Logs to a different directory if the user_id starts with "TEST".
    """
    # --- CHANGE: Select directory based on user_id ---
    if user_id.startswith("TEST"):
        target_dir = TEST_TRANSCRIPT_DIR
    else:
        target_dir = V4_TRANSCRIPT_DIR
    
    _ensure_dir(target_dir)
    
    eastern_time_obj, _ = get_current_eastern()
    date_prefix = eastern_time_obj.strftime('%b%d') # e.g., "Sep25"
    
    return os.path.join(target_dir, f"{date_prefix}_{user_id}.txt")


def log_transcript(user_id: str, role: str, text: str) -> str:
    """
    Logs a single entry to a user's transcript file.
    """
    filename = _get_transcript_filename(user_id)
    is_new_file = not os.path.exists(filename)
    
    eastern_time_obj, _ = get_current_eastern()
    line_timestamp = eastern_time_obj.strftime('%H:%M:%S')


    role_map = {"USER": "Patient", "AI": "Counselor"}
    mapped_role = role_map.get(role, role)

    if is_new_file:
        header_time = eastern_time_obj.strftime('%B %d, %Y %I:%M %p')
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"(V4) Conversation started on: {header_time} (EST)\n\n")
            f.write(f"[{line_timestamp}] Counselor: Nice to meet you, user_id: {user_id}. What do you think about your weight?\n")
            f.write("\n")

    with open(filename, "a", encoding="utf-8") as f:
        if mapped_role == "Patient" and not is_new_file:
            f.write("\n")

        f.write(f"[{line_timestamp}] {mapped_role}: {text}\n")

    return os.path.abspath(filename)
