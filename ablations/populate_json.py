#!/usr/bin/env python3
"""
Add utterances from data/v4_transcripts/*_<id>.txt
to ablations/v4_transcripts_w_code/<id>.json

Alignment strategy:
- DO NOT use timestamps (they are out of sync).
- Align by speaker order.
- Skip hardcoded counselor opener (not present in JSON).
- Skip hardcoded stage-transition counselor questions (not present in JSON).
- Be tolerant to minor formatting differences.

Output:
- Writes enriched JSON to:
    ablations/v4_transcripts_w_code_with_utterances/<id>.json
- Also writes a small alignment report to:
    ablations/v4_transcripts_w_code_with_utterances/_alignment_report.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher


# =========================
# PATHS
# =========================
CODE_DIR = Path("ablations/v4_transcripts_w_code")
TRANSCRIPT_DIR = Path("data/v4_transcripts")
OUT_DIR = Path("ablations/v4_transcripts_w_code_with_utterances")


# =========================
# HARD-CODED EXTRA UTTERANCES
# =========================
FOCUSING_INTRO_Q = (
    "Which behavior would you like to start with? "
    "We could start with diet, physical activity, or another part of your lifestyle "
    "that you'd like to change."
)

EVOKING_INTRO_Q = "Why do you want to start here?"

PLANNING_INTRO_Q = (
    "What are some steps you would consider taking to help you achieve your goal? "
    "What actions seem within reach this time?"
)

HARDCODED_STAGE_INTROS = [
    FOCUSING_INTRO_Q,
    EVOKING_INTRO_Q,
    PLANNING_INTRO_Q,
]

# The opening prompt is dynamic because it includes user_id.
# We detect it by prefix/similarity rather than exact match.
OPENING_PREFIX = "Nice to meet you"


# =========================
# REGEXES
# =========================
TRANSCRIPT_LINE_RE = re.compile(
    r"^\[(?P<time>\d{2}:\d{2}:\d{2})\]\s+(?P<speaker>Counselor|Patient):\s*(?P<text>.*)$"
)

INLINE_CODE_PREFIX_RE = re.compile(r"^\[[A-Z0-9+\-]+\]\s*")


# =========================
# HELPERS
# =========================
def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_inline_code_prefix(text: str) -> str:
    # Removes a leading [CODE] if it exists
    return INLINE_CODE_PREFIX_RE.sub("", text).strip()


def normalize_text(text: str) -> str:
    text = strip_inline_code_prefix(text)
    text = normalize_whitespace(text)

    # Normalize curly apostrophes/quotes and dashes
    text = text.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return text.strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a).lower(), normalize_text(b).lower()).ratio()


def is_stage_intro(text: str, threshold: float = 0.90) -> bool:
    nt = normalize_text(text)
    for intro in HARDCODED_STAGE_INTROS:
        if similarity(nt, intro) >= threshold:
            return True
    return False


def is_opening_counselor_utterance(text: str, threshold: float = 0.65) -> bool:
    nt = normalize_text(text)
    if nt.startswith(OPENING_PREFIX):
        return True

    # fallback fuzzy match to handle punctuation variations
    canonical = "Nice to meet you, user_id: X. What do you think about your weight?"
    return similarity(nt, canonical) >= threshold


def transcript_speaker_to_json_speaker(s: str) -> str:
    if s == "Counselor":
        return "therapist"
    if s == "Patient":
        return "client"
    raise ValueError(f"Unknown transcript speaker: {s}")


def parse_transcript(transcript_path: Path) -> List[Dict[str, Any]]:
    """
    Parses transcript lines like:
    [18:28:17] Counselor: ...
    [18:28:17] Patient: ...
    """
    utterances: List[Dict[str, Any]] = []

    for raw_line in transcript_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        m = TRANSCRIPT_LINE_RE.match(line)
        if not m:
            continue

        speaker = transcript_speaker_to_json_speaker(m.group("speaker"))
        text = m.group("text").strip()
        utterances.append(
            {
                "timestamp": m.group("time"),
                "speaker": speaker,
                "utterance": text,
                "utterance_norm": normalize_text(text),
                "raw_line": raw_line,
            }
        )

    return utterances


def find_transcript_for_session(session_id: str) -> Optional[Path]:
    matches = sorted(TRANSCRIPT_DIR.glob(f"*_{session_id}.txt"))
    if not matches:
        return None
    if len(matches) > 1:
        # If duplicates exist, pick the latest lexicographically but warn in report.
        return matches[-1]
    return matches[0]


def should_skip_extra_therapist_line(
    transcript_item: Dict[str, Any],
    expected_json_speaker: str,
    transcript_index: int,
) -> Tuple[bool, str]:
    """
    Returns (skip?, reason)
    """
    speaker = transcript_item["speaker"]
    text = transcript_item["utterance"]

    # Only therapist extras are expected in your described setup
    if speaker != "therapist":
        return False, ""

    # Opening hardcoded counselor message
    if transcript_index == 0 and expected_json_speaker == "client" and is_opening_counselor_utterance(text):
        return True, "hardcoded_opening"

    # Stage-transition hardcoded counselor intro questions
    if expected_json_speaker == "client" and is_stage_intro(text):
        return True, "hardcoded_stage_intro"

    return False, ""


# =========================
# CORE ALIGNMENT
# =========================
def align_session(
    code_events: List[Dict[str, Any]],
    transcript_utts: List[Dict[str, Any]],
    session_id: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Greedy speaker-order alignment:
    - iterate through code events
    - consume transcript utterances in order
    - skip known extra therapist lines that are absent from JSON
    """
    aligned: List[Dict[str, Any]] = []
    skipped_transcript_lines: List[Dict[str, Any]] = []

    ti = 0
    n_t = len(transcript_utts)

    # Safety: copy records so we do not mutate originals
    code_events = [dict(ev) for ev in code_events]

    for ei, ev in enumerate(code_events):
        expected_speaker = ev.get("speaker")

        # Move transcript pointer until speaker matches, allowing specific skips
        while ti < n_t and transcript_utts[ti]["speaker"] != expected_speaker:
            skip, reason = should_skip_extra_therapist_line(
                transcript_item=transcript_utts[ti],
                expected_json_speaker=expected_speaker,
                transcript_index=ti,
            )
            if skip:
                skipped_transcript_lines.append(
                    {
                        "transcript_index": ti,
                        "speaker": transcript_utts[ti]["speaker"],
                        "timestamp": transcript_utts[ti]["timestamp"],
                        "utterance": transcript_utts[ti]["utterance"],
                        "reason": reason,
                    }
                )
                ti += 1
                continue

            # Unknown mismatch: record warning and break out
            break

        if ti >= n_t:
            ev["utterance"] = None
            ev["transcript_timestamp"] = None
            ev["alignment_status"] = "missing_transcript_utterance"
            aligned.append(ev)
            continue

        if transcript_utts[ti]["speaker"] != expected_speaker:
            # Could not reconcile mismatch
            ev["utterance"] = None
            ev["transcript_timestamp"] = None
            ev["alignment_status"] = "speaker_mismatch"
            ev["alignment_debug"] = {
                "expected_speaker": expected_speaker,
                "got_transcript_speaker": transcript_utts[ti]["speaker"],
                "got_transcript_utterance": transcript_utts[ti]["utterance"],
                "transcript_index": ti,
            }
            aligned.append(ev)
            continue

        # Matched by speaker order
        ev["utterance"] = transcript_utts[ti]["utterance"]
        ev["transcript_timestamp"] = transcript_utts[ti]["timestamp"]
        ev["alignment_status"] = "matched"
        ev["transcript_index"] = ti
        aligned.append(ev)
        ti += 1

    # Remaining transcript lines that were never consumed
    leftovers = []
    while ti < n_t:
        leftovers.append(
            {
                "transcript_index": ti,
                "speaker": transcript_utts[ti]["speaker"],
                "timestamp": transcript_utts[ti]["timestamp"],
                "utterance": transcript_utts[ti]["utterance"],
                "reason": "leftover_unconsumed",
            }
        )
        ti += 1

    report = {
        "session_id": session_id,
        "num_code_events": len(code_events),
        "num_transcript_utterances": len(transcript_utts),
        "num_matched": sum(1 for x in aligned if x.get("alignment_status") == "matched"),
        "num_missing_transcript_utterance": sum(
            1 for x in aligned if x.get("alignment_status") == "missing_transcript_utterance"
        ),
        "num_speaker_mismatch": sum(1 for x in aligned if x.get("alignment_status") == "speaker_mismatch"),
        "skipped_transcript_lines": skipped_transcript_lines,
        "leftover_transcript_lines": leftovers,
    }
    return aligned, report


# =========================
# MAIN
# =========================
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    reports: List[Dict[str, Any]] = []
    code_files = sorted(CODE_DIR.glob("*.json"))

    if not code_files:
        print(f"No JSON files found in {CODE_DIR}")
        return

    for code_path in code_files:
        session_id = code_path.stem
        transcript_path = find_transcript_for_session(session_id)

        if transcript_path is None:
            reports.append(
                {
                    "session_id": session_id,
                    "status": "missing_transcript_file",
                    "code_file": str(code_path),
                }
            )
            print(f"[WARN] No transcript file found for session {session_id}")
            continue

        try:
            code_events = json.loads(code_path.read_text(encoding="utf-8"))
            transcript_utts = parse_transcript(transcript_path)

            aligned, report = align_session(code_events, transcript_utts, session_id=session_id)
            report["status"] = "ok"
            report["code_file"] = str(code_path)
            report["transcript_file"] = str(transcript_path)
            reports.append(report)

            out_path = OUT_DIR / code_path.name
            out_path.write_text(json.dumps(aligned, indent=2, ensure_ascii=False), encoding="utf-8")

            print(
                f"[OK] {session_id}: matched={report['num_matched']} "
                f"mismatch={report['num_speaker_mismatch']} "
                f"missing={report['num_missing_transcript_utterance']} "
                f"skipped={len(report['skipped_transcript_lines'])} "
                f"leftover={len(report['leftover_transcript_lines'])}"
            )

        except Exception as e:
            reports.append(
                {
                    "session_id": session_id,
                    "status": "error",
                    "code_file": str(code_path),
                    "transcript_file": str(transcript_path),
                    "error": repr(e),
                }
            )
            print(f"[ERROR] {session_id}: {e}")

    report_path = OUT_DIR / "_alignment_report.json"
    report_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote alignment report to: {report_path}")


if __name__ == "__main__":
    main()