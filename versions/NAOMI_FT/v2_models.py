from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from prompts import NAOMI_FT_PROMPT

store = {}
INTRODUCTORY_MESSAGE = (
    "Hello! My name is NAOMI and I am a virtual counselor..."
)


def get_session_history(session_id: str, initial_history=None):
    """
    Create or fetch in-memory history for a session.
    Mirrors the structure used in other NAOMI version model files.
    """
    if session_id not in store:
        history = InMemoryChatMessageHistory()

        if initial_history:
            for message in initial_history:
                role = message.get("role")
                content = message.get("content", "")

                if role in {"user", "Patient"}:
                    history.add_user_message(content)
                elif role in {"assistant", "Counselor"}:
                    history.add_ai_message(content)

        store[session_id] = history

    return store[session_id]


# Prompt template with explicit history placeholder
prompt = ChatPromptTemplate.from_messages(
    [
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)


# Fine-tuned NAOMI-FT model with paper-aligned system prompt
V2_MODEL = ChatOllama(
    model="yermakhan/mi-llama-v7",
    system=NAOMI_FT_PROMPT,
)


# Combine prompt + model
runnable = prompt | V2_MODEL


# Add message-history handling
runnable_with_history = RunnableWithMessageHistory(
    runnable,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)


def call_v2(query, session_key, initial_history=None):
    """
    NAOMI-FT:
    - uses the fine-tuned model
    - conditions on prior conversation history
    - uses the NAOMI_FT_PROMPT system prompt
    """
    print("in call_v2")

    session_id = session_key
    get_session_history(session_id, initial_history)

    response = runnable_with_history.invoke(
        {"input": query},
        config={"configurable": {"session_id": session_id}},
    )

    response_text = response.content
    return {"response": response_text}