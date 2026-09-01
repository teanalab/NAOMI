# v4_logging.py
import logging
import json
import os  # IMPORT os
from typing import Dict, Any, Optional

from utils.time_utils import format_eastern_from_timestamp

# ADDED: Define the log directory
DEFAULT_LOG_DIR = "logs"

# ---------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------
class SystemPromptFilter(logging.Filter):
    def __init__(self, is_system_log: bool):
        super().__init__()
        self.is_system_log = is_system_log

    def filter(self, record: logging.LogRecord) -> bool:
        has_system_flag = getattr(record, 'is_system_prompt', False)
        return has_system_flag if self.is_system_log else not has_system_flag

# ---------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------
class CustomLogFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return format_eastern_from_timestamp(record.created, datefmt)
    
    def format(self, record: logging.LogRecord) -> str:    
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "session_id": getattr(record, 'session_id', 'N/A'),
            "stage": getattr(record, 'stage', 'N/A'),
            "event": getattr(record, 'event', 'N/A'),
            "payload": getattr(record, 'payload', {})
        }
        payload_str = json.dumps(log_data["payload"])
        return (
            f"{log_data['timestamp']} | {log_data['level']:<8} | "
            f"{log_data['session_id']} | {log_data['stage']} | "
            f"{log_data['event']} | {payload_str}"
        )

# A simple formatter for the plain-text system messages log.
class PlainTextFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("%(message)s")

# ADDED: Helper function to create the directory if it doesn't exist
def _ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def get_logger(name: str = "v4") -> logging.Logger:
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        logger.propagate = False

        # ADDED: Ensure the log directory exists before creating handlers
        _ensure_dir(DEFAULT_LOG_DIR)

        # --- Handler 1: Main Log File (for regular events) ---
        main_log_path = os.path.join(DEFAULT_LOG_DIR, "v4.log")
        main_fh = logging.FileHandler(main_log_path, encoding="utf-8")
        main_fh.setLevel(logging.DEBUG)
        main_fh.setFormatter(CustomLogFormatter(datefmt="%Y-%m-%d %H:%M:%S"))
        main_fh.addFilter(SystemPromptFilter(is_system_log=False))
        logger.addHandler(main_fh)

        # --- Handler 2: System Prompts File ---
        system_log_path = os.path.join(DEFAULT_LOG_DIR, "system_messages.log")
        system_fh = logging.FileHandler(system_log_path, encoding="utf-8")
        system_fh.setLevel(logging.DEBUG)
        system_fh.setFormatter(PlainTextFormatter())
        system_fh.addFilter(SystemPromptFilter(is_system_log=True))
        logger.addHandler(system_fh)

    return logger

def log_event(
    logger: logging.Logger,
    session_id: str,
    stage: str,
    event: str,
    payload: Optional[Dict[str, Any]] = None,
    level: int = logging.DEBUG,
    is_system_prompt: bool = False,
    system_prompt_content: Optional[str] = None
):
    if is_system_prompt:
        extra_data = {'is_system_prompt': True}
        message = system_prompt_content or ""
        logger.log(level, message, extra=extra_data)
    else:
        extra_data = {
            'session_id': session_id,
            'stage': stage,
            'event': event,
            'payload': payload or {},
            'is_system_prompt': False
        }
        message = ""
        logger.log(level, message, extra=extra_data)