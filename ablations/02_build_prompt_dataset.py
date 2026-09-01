#!/usr/bin/env python3
"""
build_prompt_dataset.py

Build an offline prompt-ablation dataset for NAOMI from enriched transcript/code JSONs.

Expected input:
    ablations/v4_transcripts_w_code_with_utterances/<session_id>.json

Each input JSON should be a list of event dicts, e.g.:
{
  "session_id": "253d2thc",
  "timestamp": "2025-11-01 10:33:27",
  "stage": "ENGAGING",
  "speaker": "therapist",
  "code": "RCHT+",
  "source_event": "therapist_model_invoke_start",
  "event_index": 12,
  "utterance": "...",
  "transcript_timestamp": "10:31:33",
  "alignment_status": "matched",
  ...
}

Output:
    ablations/prompt_dataset/prompt_dataset.jsonl
    ablations/prompt_dataset/by_stage/ENGAGING.jsonl
    ablations/prompt_dataset/by_stage/FOCUSING.jsonl
    ablations/prompt_dataset/by_stage/EVOKING.jsonl
    ablations/prompt_dataset/by_stage/PLANNING.jsonl
    ablations/prompt_dataset/build_stats.json

Each dataset example is one therapist target turn, with:
- explicit current stage
- expected therapist code
- gold therapist utterance
- prior full history
- prior stage-local history
- latest client message
- metadata for alignment/debugging

Notes:
- We do NOT require alignment_status == "matched".
- We only require the therapist target utterance itself to be non-empty.
- Client turns with missing utterance are skipped from history.
- Therapist turns with missing utterance are not used as targets.
- History is stored in a Naomi-friendly message format:
      {"role": "user", "content": "..."}      # client
      {"role": "assistant", "content": "..."} # therapist
- Also stored in an RC-style format if you want to mirror current v4 internals:
      {"role": "user", "content": "..."}
      {"role": "ai",   "content": "..."}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import Counter, defaultdict


# ----------------------------
# Config
# ----------------------------
ABLATIONS_DIR = Path(__file__).resolve().parent
INPUT_DIR = ABLATIONS_DIR / "DCA_transcripts"
OUTPUT_DIR = ABLATIONS_DIR / "prompt_dataset"
BY_STAGE_DIR = OUTPUT_DIR / "by_stage"

STAGES = ["ENGAGING", "FOCUSING", "EVOKING", "PLANNING"]


# ----------------------------
# Helpers
# ----------------------------
def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def clean_text(x: Optional[str]) -> Optional[str]:
    if x is None:
        return None
    x = str(x).strip()
    return x if x else None


def is_usable_utterance(x: Optional[str]) -> bool:
    return clean_text(x) is not None


def event_to_naomi_role(speaker: str) -> Optional[str]:
    if speaker == "client":
        return "user"
    if speaker == "therapist":
        return "assistant"
    return None


def event_to_rc_role(speaker: str) -> Optional[str]:
    if speaker == "client":
        return "user"
    if speaker == "therapist":
        return "ai"
    return None


def make_history_message(event: Dict[str, Any]) -> Optional[Dict[str, str]]:
    role = event_to_naomi_role(event.get("speaker"))
    utt = clean_text(event.get("utterance"))
    if role is None or utt is None:
        return None
    return {"role": role, "content": utt}


def make_rc_message(event: Dict[str, Any]) -> Optional[Dict[str, str]]:
    role = event_to_rc_role(event.get("speaker"))
    utt = clean_text(event.get("utterance"))
    if role is None or utt is None:
        return None
    return {"role": role, "content": utt}


def last_client_message(events: List[Dict[str, Any]]) -> Optional[str]:
    for ev in reversed(events):
        if ev.get("speaker") == "client" and is_usable_utterance(ev.get("utterance")):
            return clean_text(ev.get("utterance"))
    return None


def maybe_previous_stage(events: List[Dict[str, Any]], current_stage: str) -> Optional[str]:
    for ev in reversed(events):
        st = ev.get("stage")
        if st and st != current_stage:
            return st
    return None


def count_stage_turns(events: List[Dict[str, Any]], stage: str) -> int:
    return sum(1 for ev in events if ev.get("stage") == stage and ev.get("speaker") in {"client", "therapist"})


def build_example(
    session_id: str,
    events: List[Dict[str, Any]],
    target_idx: int,
) -> Optional[Dict[str, Any]]:
    """
    Build one example for a therapist target turn.

    Target = therapist event with non-empty utterance.
    Prior history = all usable utterances before target.
    Stage-local history = only usable utterances from current stage before target.
    """
    target = events[target_idx]

    if target.get("speaker") != "therapist":
        return None

    gold_utt = clean_text(target.get("utterance"))
    if gold_utt is None:
        return None

    current_stage = target.get("stage")
    expected_code = target.get("code")

    prior_events = events[:target_idx]
    prior_full_events = [ev for ev in prior_events if is_usable_utterance(ev.get("utterance"))]
    prior_stage_events = [
        ev for ev in prior_events
        if ev.get("stage") == current_stage and is_usable_utterance(ev.get("utterance"))
    ]

    full_history_messages = []
    full_history_rc = []
    for ev in prior_full_events:
        hm = make_history_message(ev)
        rm = make_rc_message(ev)
        if hm is not None:
            full_history_messages.append(hm)
        if rm is not None:
            full_history_rc.append(rm)

    stage_history_messages = []
    stage_history_rc = []
    for ev in prior_stage_events:
        hm = make_history_message(ev)
        rm = make_rc_message(ev)
        if hm is not None:
            stage_history_messages.append(hm)
        if rm is not None:
            stage_history_rc.append(rm)

    latest_client = last_client_message(prior_events)
    prev_stage = maybe_previous_stage(prior_events, current_stage)

    # Naomi-like prompt pieces
    # current production uses:
    #   - stage-specific policy based on current stage
    #   - rc = session_data["memory"]["rc"]
    #   - question = latest client message
    #
    # For offline prompt ablation, stage_history_rc is probably the closest
    # approximation of stage-local RC semantics.
    example_id = f"{session_id}__event_{target.get('event_index', target_idx)}"

    example = {
        "example_id": example_id,
        "session_id": session_id,

        # ===== Target metadata =====
        "target": {
            "speaker": "therapist",
            "stage": current_stage,
            "expected_therapist_code": expected_code,
            "gold_utterance": gold_utt,
            "timestamp": target.get("timestamp"),
            "transcript_timestamp": target.get("transcript_timestamp"),
            "event_index": target.get("event_index"),
            "source_event": target.get("source_event"),
            "alignment_status": target.get("alignment_status"),
            "alignment_debug": target.get("alignment_debug"),
        },

        # ===== Stage clarity =====
        "stage_info": {
            "current_stage": current_stage,
            "previous_stage_seen_in_history": prev_stage,
            "num_prior_turn_events_in_full_history": count_stage_turns(prior_events, current_stage=None) if False else len([
                ev for ev in prior_events if ev.get("speaker") in {"client", "therapist"}
            ]),
            "num_prior_turn_events_in_current_stage": len([
                ev for ev in prior_stage_events if ev.get("speaker") in {"client", "therapist"}
            ]),
            "stage_changed_since_last_event": (
                len(prior_events) > 0 and prior_events[-1].get("stage") != current_stage
            ),
        },

        # ===== Naomi-friendly histories =====
        "history": {
            # All prior usable utterances
            "full_messages": full_history_messages,

            # Only prior usable utterances from the current stage
            "stage_messages": stage_history_messages,

            # RC-style versions if you want to mirror current internal format
            "full_rc": full_history_rc,
            "stage_rc": stage_history_rc,

            # Most recent client utterance before target therapist turn
            "latest_client_message": latest_client,
        },

        # ===== Flat convenience fields =====
        "current_stage": current_stage,
        "expected_therapist_code": expected_code,
        "gold_utterance": gold_utt,
        "latest_client_message": latest_client,

        # ===== Debug / provenance =====
        "notes": {
            "intended_use": (
                "Offline prompt-ablation example for NAOMI. "
                "Use current_stage to select the stage policy. "
                "Use history.stage_rc (or stage_messages) as the most faithful stage-local context. "
                "Use expected_therapist_code as the fixed target code."
            ),
            "target_alignment_status_kept_even_if_not_matched": True,
            "missing_utterance_targets_removed": True,
        },
    }

    return example


def build_dataset_for_session(session_path: Path) -> List[Dict[str, Any]]:
    session_id = session_path.stem
    events = load_json(session_path)

    if not isinstance(events, list):
        raise ValueError(f"{session_path} does not contain a list of events.")

    examples: List[Dict[str, Any]] = []
    for i, ev in enumerate(events):
        if ev.get("speaker") != "therapist":
            continue
        ex = build_example(session_id=session_id, events=events, target_idx=i)
        if ex is not None:
            examples.append(ex)

    return examples


# ----------------------------
# Main
# ----------------------------
def main() -> None:
    ensure_dir(OUTPUT_DIR)
    ensure_dir(BY_STAGE_DIR)

    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Input dir not found: {INPUT_DIR}")

    session_files = sorted(INPUT_DIR.glob("*.json"))
    if not session_files:
        raise FileNotFoundError(f"No .json files found in: {INPUT_DIR}")

    all_examples: List[Dict[str, Any]] = []
    by_stage: Dict[str, List[Dict[str, Any]]] = {s: [] for s in STAGES}

    stats = {
        "input_dir": str(INPUT_DIR),
        "num_session_files": 0,
        "num_examples_total": 0,
        "examples_per_stage": {},
        "alignment_status_counts": {},
        "code_counts": {},
        "code_counts_by_stage": {},
        "sessions_with_zero_examples": [],
    }

    alignment_counter = Counter()
    code_counter = Counter()
    code_by_stage_counter = defaultdict(Counter)

    for session_path in session_files:
        session_examples = build_dataset_for_session(session_path)
        stats["num_session_files"] += 1

        if not session_examples:
            stats["sessions_with_zero_examples"].append(session_path.stem)
            continue

        for ex in session_examples:
            all_examples.append(ex)

            st = ex["current_stage"]
            if st in by_stage:
                by_stage[st].append(ex)
            else:
                # Keep unseen stages too, just in case
                by_stage.setdefault(st, []).append(ex)

            alignment_counter[ex["target"]["alignment_status"]] += 1
            code = ex["expected_therapist_code"]
            code_counter[code] += 1
            code_by_stage_counter[st][code] += 1

    stats["num_examples_total"] = len(all_examples)
    stats["examples_per_stage"] = {stage: len(rows) for stage, rows in by_stage.items()}
    stats["alignment_status_counts"] = dict(alignment_counter)
    stats["code_counts"] = dict(code_counter)
    stats["code_counts_by_stage"] = {
        stage: dict(counter) for stage, counter in code_by_stage_counter.items()
    }

    # Write outputs
    write_jsonl(OUTPUT_DIR / "prompt_dataset.jsonl", all_examples)

    for stage, rows in by_stage.items():
        write_jsonl(BY_STAGE_DIR / f"{stage}.jsonl", rows)

    write_json(OUTPUT_DIR / "build_stats.json", stats)

    print(f"[OK] Wrote {len(all_examples)} examples to {OUTPUT_DIR / 'prompt_dataset.jsonl'}")
    for stage, rows in by_stage.items():
        print(f"  - {stage}: {len(rows)}")
    print(f"[OK] Stats: {OUTPUT_DIR / 'build_stats.json'}")


if __name__ == "__main__":
    main()