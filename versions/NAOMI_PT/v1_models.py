# NAOMI-PT v1: Prompt-only baseline

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_ollama import OllamaLLM

from versions.NAOMI_PT.v1_constants import (
    V1_FEWSHOT_PROMPT_PREFIX,
    USER_HEADER,
    ASSISTANT_HEADER,
    END_OF_TURN_TOKEN,
)

SESSION_HISTORY_STORE = {}
INTRODUCTORY_MESSAGE = "Hello! My name is NAOMI and I am a virtual counselor..."


def get_session_history(session_id: str, initial_history=None):
    """
    Create or fetch in-memory history for a session.
    """
    if session_id not in SESSION_HISTORY_STORE:
        session_history = InMemoryChatMessageHistory()

        if initial_history:
            for message in initial_history:
                role = message.get("role")
                content = message.get("content", "")

                if role in {"user", "Patient"}:
                    session_history.add_user_message(content)
                elif role in {"assistant", "Counselor"}:
                    session_history.add_ai_message(content)

        SESSION_HISTORY_STORE[session_id] = session_history

    return SESSION_HISTORY_STORE[session_id]


def build_role_tagged_history(session_history, current_query):
    """
    Convert LangChain history into Patient/Counselor turn format
    and append the current patient turn.
    """
    turn_history = []

    for message in session_history.messages:
        role = "Patient" if message.type == "human" else "Counselor"
        turn_history.append({"role": role, "content": message.content})

    turn_history.append({"role": "Patient", "content": current_query})
    return turn_history


def trim_turn_history_for_context(prior_turns, prompt_prefix, max_context_words=4096):
    """
    Trim oldest completed turns so the prompt stays within budget.

    prior_turns should contain only previous conversation turns,
    not the current query.
    """
    if not prior_turns:
        return []

    prefix_word_count = len(prompt_prefix.split())
    available_word_budget = max_context_words - prefix_word_count

    if available_word_budget <= 0:
        return []

    trimmed_turns = list(prior_turns)

    def count_turn_words(turns):
        return sum(len(turn["content"].split()) for turn in turns)

    while trimmed_turns and count_turn_words(trimmed_turns) > available_word_budget:
        if len(trimmed_turns) >= 2:
            trimmed_turns = trimmed_turns[2:]
        else:
            trimmed_turns = trimmed_turns[1:]

    return trimmed_turns


def build_v1_prompt(turn_history, max_context_words=4096):
    """
    Build the native Llama 3 chat-formatted prompt for NAOMI-PT.

    This preserves the native Llama 3 token structure while combining:
    - the fixed system prompt
    - a fixed few-shot demonstration block
    - the current session history
    """
    if not turn_history:
        raise ValueError("turn_history must contain at least the current query.")

    current_patient_message = turn_history[-1]["content"]
    prior_turns = turn_history[:-1]

    trimmed_prior_turns = trim_turn_history_for_context(
        prior_turns,
        prompt_prefix=V1_FEWSHOT_PROMPT_PREFIX,
        max_context_words=max_context_words,
    )

    prompt_text = V1_FEWSHOT_PROMPT_PREFIX

    i = 0
    while i < len(trimmed_prior_turns):
        turn = trimmed_prior_turns[i]

        if turn["role"] != "Patient":
            i += 1
            continue

        patient_text = turn["content"]
        prompt_text += f"{patient_text}{END_OF_TURN_TOKEN}{ASSISTANT_HEADER}"

        if i + 1 < len(trimmed_prior_turns) and trimmed_prior_turns[i + 1]["role"] == "Counselor":
            counselor_text = trimmed_prior_turns[i + 1]["content"]
            prompt_text += f"{counselor_text}{END_OF_TURN_TOKEN}{USER_HEADER}"

        i += 2

    prompt_text += f"{current_patient_message}{END_OF_TURN_TOKEN}{ASSISTANT_HEADER}"
    return prompt_text


NAOMI_PT_MODEL = OllamaLLM(model="llama3.1:70b")


def call_v1(query, session_key, initial_history=None):
    """
    NAOMI-PT:
    - prompt-only baseline
    - uses fixed prompt instructions plus a fixed few-shot demonstration block
    - preserves native Llama 3 prompt tokens for conversation history
    - no retrieval, no fine-tuning, no revise step
    """
    print("in call_v1")

    session_history = get_session_history(session_key, initial_history)

    turn_history = build_role_tagged_history(session_history, query)
    prompt_text = build_v1_prompt(turn_history)

    response_text = NAOMI_PT_MODEL.invoke(prompt_text)

    session_history.add_user_message(query)
    session_history.add_ai_message(response_text)

    return {"response": response_text}