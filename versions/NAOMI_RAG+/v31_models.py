import re
from datetime import datetime
import zoneinfo

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_ollama import OllamaLLM

from prompts import (
    NAOMI_FT_PROMPT,
    NAOMI_RAG_PLUS_REVISOR_PROMPT,
)
from rag import (
    build_embeddings,
    get_mi_retrievers,
    retrieve_results,
    format_context,
    format_retrieval,
    format_chat_history,
)

store = {}
INTRODUCTORY_MESSAGE = "Hello! My name is NAOMI and I am a virtual counselor..."


def get_chat_transcript(raw_history, separator="\n"):
    """
    Format raw chat history into a readable transcript.
    """
    transcript_lines = []
    for msg in raw_history:
        role = msg.get("role", "Unknown")
        content = msg.get("content", "")
        transcript_lines.append(f"{role}: {content}")
    return separator.join(transcript_lines)


def get_session_history(session_id: str, initial_history=None):
    """
    Create or fetch in-memory history for a session.
    """
    if session_id not in store:
        history = InMemoryChatMessageHistory()

        if initial_history:
            for message in initial_history:
                role = message.get("role")
                content = message.get("content", "")

                if role == "user":
                    history.add_user_message(content)
                elif role == "assistant":
                    history.add_ai_message(content)

        store[session_id] = history

    return store[session_id]


def build_raw_history(history, current_query):
    """
    Convert LangChain history into the role/content format used by retrieval and prompting.
    """
    raw_history = []

    for msg in history.messages:
        role = "Patient" if msg.type == "human" else "Counselor"
        raw_history.append({"role": role, "content": msg.content})

    raw_history.append({"role": "Patient", "content": current_query})
    return raw_history


def get_rag_context(raw_history):
    """
    Retrieve therapist examples using the recent conversation window.
    """
    embeddings = build_embeddings()
    retrievers = get_mi_retrievers(embeddings)

    # Retrieval uses the recent 5-turn conversation window
    rag_query = format_chat_history(raw_history, n=5)
    results = retrieve_results(rag_query, retrievers, embeddings, k=1)

    context_text = format_context(results)
    results_text = format_retrieval(results)

    return context_text, results_text


# Same underlying model for both stages
BASE_MODEL = OllamaLLM(model="yermakhan/mi-llama-v7")


def generate_draft_response(query, raw_history):
    """
    First stage of NAOMI-RAG+:
    generate a draft response using the same underlying model as NAOMI-FT,
    but with the NAOMI-FT prompt.
    """
    formatted_chat_history = format_chat_history(raw_history, n=10)

    draft_prompt = NAOMI_FT_PROMPT.format(
        chat_history=formatted_chat_history,
        question=query,
    )

    draft_response = BASE_MODEL.invoke(draft_prompt)
    return draft_response, draft_prompt


def clean_revisor_output(text):
    """
    Clean the revisor output while preserving normal response content.
    """
    cleaned = text.strip()

    cleaned = re.sub(
        r"^\s*(RR|RR:|REVISED RESPONSE|REVISED RESPONSE:)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = cleaned.strip().strip('"').strip("'").strip()
    return cleaned


def call_v31(query, session_key, initial_history=None):
    """
    NAOMI-RAG+:
    1) generate a draft with the same underlying model as NAOMI-FT
    2) retrieve relevant therapist examples
    3) revise the draft using the same underlying model again with a different prompt
    """
    print("in call_v31")

    session_id = session_key
    history = get_session_history(session_id, initial_history)

    # Build history including current user turn
    raw_history = build_raw_history(history, query)

    # Step 1: generate draft with NAOMI-FT prompt
    draft_response, draft_prompt = generate_draft_response(query, raw_history)

    # Step 2: retrieve MI therapist examples
    context_text, results_text = get_rag_context(raw_history)

    # Step 3: revise the draft with the same model, different prompt
    formatted_chat_history = format_chat_history(raw_history, n=10)

    revisor_prompt = NAOMI_RAG_PLUS_REVISOR_PROMPT.format(
        therapist_responses=context_text,
        ai_response=draft_response,
        chat_history=formatted_chat_history,
    )

    revised_response = BASE_MODEL.invoke(revisor_prompt)
    revised_response = clean_revisor_output(revised_response)

    # Persist final turn
    history.add_user_message(query)
    history.add_ai_message(revised_response)

    # Debug log
    # with open("debug_rag_plus_output.txt", "a", encoding="utf-8") as f:
    #     eastern_time = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    #     timestamp = eastern_time.strftime("%Y-%m-%d %I:%M:%S %p %Z")

    #     f.write(f"\n===== LOG ENTRY: {timestamp} =====\n")

    #     f.write("DRAFT PROMPT:\n")
    #     f.write(draft_prompt)

    #     f.write("\n\nDRAFT RESPONSE:\n")
    #     f.write(draft_response)

    #     f.write("\n\nREVISOR PROMPT:\n")
    #     f.write(revisor_prompt)

    #     f.write("\n\nFINAL REVISED RESPONSE:\n")
    #     f.write(revised_response)

    #     f.write("\n\n--- RAG CONTEXT TEXT ---\n")
    #     f.write(context_text)

    #     f.write("\n\n--- RETRIEVAL RESULTS ---\n")
    #     f.write(results_text)

    #     f.write("\n===========================\n\n")

    return {
        "response": revised_response,
        "draft_response": draft_response,
        "results": results_text,
    }