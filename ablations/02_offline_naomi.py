#!/usr/bin/env python3
"""
02_offline_naomi.py

Run offline NAOMI generations for prompt-ablation experiments.

Input:
    ablations/prompt_dataset/prompt_dataset.jsonl

Output:
    ablations/prompt_dataset/offline_naomi_outputs.csv

Prompt variants:
    1) no_defs
       - no MI code definitions included
    2) all_defs
       - all stage-valid MI code definitions included
    3) selected_only
       - only the selected target code definition included

CSV columns include:
    - example_id
    - session_id
    - current_stage
    - target_code
    - target_code_definition
    - latest_client_message
    - stage_rc_json
    - stage_messages_json
    - full_messages_json
    - gold_utterance
    - response_no_defs
    - response_all_defs
    - response_selected_only
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage



from constants import MI_CODE_DEFS
from versions.NAOMI_DCA.v4_prompts import p1_e_no_defs, p2_f_no_defs, p3_e_no_defs, p4_p_no_defs


# --------------------------------------------------
# Paths / config
# --------------------------------------------------
ABLATIONS_DIR = Path(__file__).resolve().parent
DATASET_PATH = ABLATIONS_DIR / "prompt_dataset" / "prompt_dataset.jsonl"
OUTPUT_CSV = ABLATIONS_DIR / "prompt_dataset" / "offline_naomi_outputs.csv"

MODEL_NAME = "yermakhan/naomi-dca"
TEMPERATURE = 0.7
REPEAT_PENALTY = 1.2
TOP_K = 40
TOP_P = 0.95

# Optional limit for testing; set to None to run all
MAX_EXAMPLES: Optional[int] = None


# --------------------------------------------------
# Naomi prompt pieces
# --------------------------------------------------
SYSTEM_HEADER = """
You are Dr. Naomi, a motivational interviewing therapist who helps people struggling with obesity.
- Always be empathetic, supportive, and autonomy-affirming.
- Do not argue, criticize, or give unsolicited medical advice.
- Do not overuse formulaic openers like "It sounds like..." or "It seems like...".
- Every response must begin with the MI code provided in the input.
- Avoid repeating questions. Build naturally on what the client just said.
- Keep the conversation supportive, client-centered, and exploratory.
""".strip()

STAGE_POLICIES = {
    "ENGAGING": p1_e_no_defs,
    "FOCUSING": p2_f_no_defs,
    "EVOKING": p3_e_no_defs,
    "PLANNING": p4_p_no_defs,
}


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def to_langchain_messages(rc_messages: List[Dict[str, str]]) -> List[Any]:
    out: List[Any] = []
    for m in rc_messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue

        if role == "user":
            out.append(HumanMessage(content))
        elif role in {"assistant", "ai"}:
            out.append(AIMessage(content))
        else:
            # ignore unknown roles
            continue
    return out


def format_all_stage_defs(stage: str) -> str:
    defs = MI_CODE_DEFS.get(stage, {})
    if not defs:
        return "(no stage definitions found)"

    lines = []
    for code, definition in defs.items():
        lines.append(f"- [{code}] {definition}")
    return "\n".join(lines)


def format_selected_def(stage: str, code: str) -> str:
    return MI_CODE_DEFS.get(stage, {}).get(code, "(no definition found for this code in this stage)")


def build_system_prompt(stage: str, prompt_variant: str) -> str:
    stage_policy = STAGE_POLICIES.get(stage, "").strip()

    if prompt_variant == "no_defs":
        defs_block = ""
    elif prompt_variant == "all_defs":
        defs_block = f"MI code definitions for this stage:\n{format_all_stage_defs(stage)}"
    elif prompt_variant == "selected_only":
        # selected definition goes into human prompt for clarity/binding
        defs_block = "MI code definitions for this stage:\n(only the selected target code definition will be provided below)"
    else:
        raise ValueError(f"Unknown prompt_variant: {prompt_variant}")

    system = f"""
{SYSTEM_HEADER}

Current stage policy (VERY IMPORTANT):
{stage_policy}

{defs_block}

Important points to remember from earlier stages (if any):
(none for offline ablation)
""".strip()

    return system


def build_human_instruction(
    latest_client_message: str,
    target_code: str,
    target_definition: str,
    prompt_variant: str,
) -> str:
    if prompt_variant == "selected_only":
        definition_line = f"Definition of the target MI code: {target_definition}"
    elif prompt_variant == "all_defs":
        definition_line = (
            "Definitions for all valid stage codes are available in the system prompt. "
            f"The target MI code is: [{target_code}]."
        )
    elif prompt_variant == "no_defs":
        definition_line = f"The target MI code is: [{target_code}]."
    else:
        raise ValueError(f"Unknown prompt_variant: {prompt_variant}")

    return f"""The client's latest message is: "{latest_client_message}"

Your task: generate the next therapist response.
Target MI code to realize: [{target_code}]
{definition_line}

Important constraints:
- Realize the target MI code as faithfully and naturally as possible in this context.
- Do NOT switch to another MI code even if you think another code could also fit.
- Do not mention the code name or definition in your response.
- Do not ask a follow-up question unless the target code starts with "Q", e.g. "QECHT+".
- Follow the stage-specific policy in the system message.
- NEVER TALK IN THIRD PERSON. ADDRESS THE CLIENT DIRECTLY.
""".strip()


# --------------------------------------------------
# Offline Naomi
# --------------------------------------------------
class OfflineNaomi:
    def __init__(self, model_name: str = MODEL_NAME):
        self.logger = logging.getLogger("offline_naomi")
        self.model = ChatOllama(
            model=model_name,
            temperature=TEMPERATURE,
            repeat_penalty=REPEAT_PENALTY,
            top_k=TOP_K,
            top_p=TOP_P,
        )

    def generate(
        self,
        stage: str,
        stage_rc: List[Dict[str, str]],
        latest_client_message: str,
        target_code: str,
        prompt_variant: str,
    ) -> str:
        target_definition = format_selected_def(stage, target_code)
        system_prompt = build_system_prompt(stage, prompt_variant)
        human_prompt = build_human_instruction(
            latest_client_message=latest_client_message,
            target_code=target_code,
            target_definition=target_definition,
            prompt_variant=prompt_variant,
        )

        final_prompt = ChatPromptTemplate.from_messages([
            ("system", "{system}"),
            MessagesPlaceholder(variable_name="rc"),
            ("human", "{human_prompt}"),
        ])

        rc_msgs = to_langchain_messages(stage_rc)
        chain = final_prompt | self.model

        out = chain.invoke({
            "system": system_prompt,
            "rc": rc_msgs,
            "human_prompt": human_prompt,
        })
        return (out.content or "").strip()


# --------------------------------------------------
# CSV row builder
# --------------------------------------------------
def make_csv_row(example: Dict[str, Any], naomi: OfflineNaomi) -> Dict[str, Any]:
    stage = example["current_stage"]
    target_code = example["expected_therapist_code"]
    target_definition = format_selected_def(stage, target_code)

    latest_client_message = example.get("latest_client_message") or ""
    stage_rc = example["history"].get("stage_rc", [])
    stage_messages = example["history"].get("stage_messages", [])
    full_messages = example["history"].get("full_messages", [])
    gold_utterance = example.get("gold_utterance") or example["target"].get("gold_utterance") or ""

    response_no_defs = naomi.generate(
        stage=stage,
        stage_rc=stage_rc,
        latest_client_message=latest_client_message,
        target_code=target_code,
        prompt_variant="no_defs",
    )

    response_all_defs = naomi.generate(
        stage=stage,
        stage_rc=stage_rc,
        latest_client_message=latest_client_message,
        target_code=target_code,
        prompt_variant="all_defs",
    )

    response_selected_only = naomi.generate(
        stage=stage,
        stage_rc=stage_rc,
        latest_client_message=latest_client_message,
        target_code=target_code,
        prompt_variant="selected_only",
    )

    row = {
        "example_id": example.get("example_id"),
        "session_id": example.get("session_id"),
        "current_stage": stage,

        "target_code": target_code,
        "target_code_definition": target_definition,

        "latest_client_message": latest_client_message,
        "gold_utterance": gold_utterance,

        # Context snapshots for later analysis/debugging
        "stage_rc_json": json.dumps(stage_rc, ensure_ascii=False),
        "stage_messages_json": json.dumps(stage_messages, ensure_ascii=False),
        "full_messages_json": json.dumps(full_messages, ensure_ascii=False),

        # Optional metadata
        "target_alignment_status": example.get("target", {}).get("alignment_status"),
        "target_event_index": example.get("target", {}).get("event_index"),
        "target_source_event": example.get("target", {}).get("source_event"),

        # Naomi outputs
        "response_no_defs": response_no_defs,
        "response_all_defs": response_all_defs,
        "response_selected_only": response_selected_only,
    }
    return row


# --------------------------------------------------
# Main
# --------------------------------------------------
def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    rows = load_jsonl(DATASET_PATH)
    if MAX_EXAMPLES is not None:
        rows = rows[:MAX_EXAMPLES]

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    naomi = OfflineNaomi(model_name=MODEL_NAME)

    fieldnames = [
        "example_id",
        "session_id",
        "current_stage",
        "target_code",
        "target_code_definition",
        "latest_client_message",
        "gold_utterance",
        "stage_rc_json",
        "stage_messages_json",
        "full_messages_json",
        "target_alignment_status",
        "target_event_index",
        "target_source_event",
        "response_no_defs",
        "response_all_defs",
        "response_selected_only",
    ]

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        total = len(rows)
        for i, ex in enumerate(rows, start=1):
            try:
                csv_row = make_csv_row(ex, naomi)
                writer.writerow(csv_row)
                print(f"[{i}/{total}] OK  {ex.get('example_id')}  stage={ex.get('current_stage')}  code={ex.get('expected_therapist_code')}")
            except Exception as e:
                print(f"[{i}/{total}] ERR {ex.get('example_id')}: {e}")

    print(f"\n[OK] Wrote CSV to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()