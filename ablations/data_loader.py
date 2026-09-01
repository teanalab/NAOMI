# ablations/data_loader.py
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple
import json

from ablations.abl_types import Turn

DEFAULT_TRANSCRIPTS_DIR = "ablations/v4_transcripts_w_code"

ROLE_MAP = {
    "therapist": "T",
    "assistant": "T",
    "agent": "T",
    "naomi": "T",
    "hcp": "T",
    "t": "T",
    "client": "C",
    "user": "C",
    "patient": "C",
    "c": "C",
}


def load_json(path: str | Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _to_role(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s not in ROLE_MAP:
        raise ValueError(f"Unknown role/speaker: {raw!r}")
    return ROLE_MAP[s]


def _normalize_stage(stage: str) -> str:
    s = (stage or "").strip().lower()
    aliases = {
        "engaging": "ENGAGING",
        "focusing": "FOCUSING",
        "evoking": "EVOKING",
        "planning": "PLANNING",
    }
    if s in aliases:
        return aliases[s]
    if stage in {"ENGAGING", "FOCUSING", "EVOKING", "PLANNING"}:
        return stage
    raise ValueError(f"Unknown stage label: {stage!r}")


def load_turns_from_transcript_dir(
    *,
    transcript_dir: str | Path = DEFAULT_TRANSCRIPTS_DIR,
) -> List[Turn]:
    """
    Loads per-session JSON files from transcript_dir.

    Each file contains chronological mixed client/therapist code events.

    For each therapist event, create one Turn with:
      - logged_code      = therapist code at that event
      - code_hist_all    = all previous mixed (role, code) events in session
      - code_hist_stage  = all previous mixed (role, code) events in same stage

    Supports either:
      - "role": "T"/"C" or equivalent strings
      - "speaker": "therapist"/"client"/etc.
    """
    transcript_dir = Path(transcript_dir)
    if not transcript_dir.exists():
        raise FileNotFoundError(f"Transcript directory not found: {transcript_dir}")

    turns: List[Turn] = []

    json_files = sorted(
        p for p in transcript_dir.iterdir()
        if p.is_file() and p.suffix.lower() == ".json"
    )

    for path in json_files:
        events = load_json(path)
        if not events:
            continue

        events = sorted(
            events,
            key=lambda e: (
                e.get("event_index", float("inf")),
                e.get("timestamp", ""),
            )
        )

        mixed_hist_all: List[Tuple[str, str]] = []
        mixed_hist_stage: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

        idx_therapist = 0
        session_id_from_filename = path.stem

        for e in events:
            session_id = str(e.get("session_id", session_id_from_filename)).strip()

            code_raw = e.get("code")
            stage_raw = e.get("stage")

            role_or_speaker_raw = str(
                e.get("role", e.get("speaker", ""))
            ).strip()

            if not role_or_speaker_raw or code_raw is None or stage_raw is None:
                continue

            role = _to_role(role_or_speaker_raw)
            code = str(code_raw).strip()
            stage = _normalize_stage(str(stage_raw))

            if role == "T":
                turn_id = f"{session_id}:{idx_therapist}"

                turns.append(
                    Turn(
                        session_id=session_id,
                        turn_id=turn_id,
                        idx_in_session=idx_therapist,
                        stage=stage,
                        logged_code=code,
                        code_hist_all=tuple(mixed_hist_all),
                        code_hist_stage=tuple(mixed_hist_stage[stage]),
                    )
                )
                idx_therapist += 1

            event_tuple = (role, code)
            mixed_hist_all.append(event_tuple)
            mixed_hist_stage[stage].append(event_tuple)

    return turns