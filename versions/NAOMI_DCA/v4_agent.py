import logging
from typing import List, Any

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from .v4_prompts import p1_e_no_defs, p2_f_no_defs, p3_e_no_defs, p4_p_no_defs
from .v4_logging import log_event
from constants import MI_CODE_DEFS

SYSTEM_HEADER = """
You are Dr. Naomi, a motivational interviewing therapist who helps people struggling with obesity.
- Always be empathetic, supportive, and autonomy-affirming.
- Do not argue, criticize, or give unsolicited medical advice.
- Do not overuse formulaic openers like "It sounds like..." or "It seems like...".
- Every response must begin with the MI code provided in the input .
- Avoid repeating questions. Build naturally on what the client just said.
- Keep the conversation supportive, client-centered, and exploratory.
"""

STAGE_POLICIES = {
    "ENGAGING": p1_e_no_defs, "FOCUSING": p2_f_no_defs,
    "EVOKING":  p3_e_no_defs, "PLANNING": p4_p_no_defs,
}

class TherapistAgent:
    """Handles the persona-driven response generation as Dr. Naomi."""
    def __init__(self, logger: logging.Logger, model_name: str = "yermakhan/naomi-dca"):
        self.logger = logger
        self.model = ChatOllama(
            model=model_name,
            temperature=0.7,
            repeat_penalty=1.2,
            top_k=40,
            top_p=0.95
        )

    def _build_system_message(self, session_id: str, session_data: dict) -> str:
        """Constructs the full system prompt for the Naomi persona."""
        mem = session_data["memory"]
        
        if mem["stable"]:
            stable_mem_str = "\n- ".join(mem['stable'])
            sm_block = f"Stable memory:\n- {stable_mem_str}\n\n"
        else:
            sm_block = ""
        stage_policy = STAGE_POLICIES[session_data["stage"]].strip()
        
        system = f"""{SYSTEM_HEADER}\n\n{sm_block}Current stage policy (VERY IMPORTANT):\n{stage_policy}\n\nImportant points to remember from earlier stages (if any):\n{mem.get("cumulative_sum", "(none yet)")}""".strip()
        
        # Log the full prompt to a separate file for easy debugging
        log_content = f"--- SYSTEM PROMPT for Session: {session_id} | Stage: {session_data['stage']} ---\n{system}\n"
        self.logger.info(log_content, extra={'is_system_prompt': True})
        
        return system

    def generate_response(self, session_id: str, session_data: dict, question: str, mi_code: str) -> str:
        """Generates a therapist response using the main persona-driven LLM."""
        system_prompt = self._build_system_message(session_id, session_data)
        
        print(f"Mi code suggested by helper agent: {mi_code}")
        stage = session_data["stage"]
        stage_defs = MI_CODE_DEFS.get(stage, {})
        suggested_def = stage_defs.get(mi_code, "(no definition found for this code in this stage)")
        print(f"Definition of the suggested MI code: {suggested_def}")
        final_prompt = ChatPromptTemplate.from_messages([
            ("system", "{system}"),
            MessagesPlaceholder(variable_name="rc"),
            ("human", """The client's latest message is: "{question}"

Your task: generate the next therapist response. Suggested MI code to include: [{mi_code}].
Definition of the suggested MI code: {suggested_def}             
If this code does not fit the context you can use another code that fits best. 
Do not ask followup questions unless the code starts with "Q", e.g. "QECHT+".
Follow the stage-specific policy in the system message. NEVER TALK IN THIRD PERSON. ADDRESS THE CLIENT DIRECTLY."""),
        ])
        
        rc_msgs = [HumanMessage(m["content"]) if m["role"] == "user" else AIMessage(m["content"]) for m in session_data["memory"]["rc"]]

        log_event(
            self.logger, session_id=session_id, stage=session_data['stage'], 
            event="therapist_model_invoke_start", 
            payload={"mi_code": mi_code, "rc_len": len(rc_msgs)}
        )

        chain = final_prompt | self.model
        out = chain.invoke({
            "system": system_prompt,
            "rc": rc_msgs,
            "question": question,
            "mi_code": mi_code,
            "suggested_def": suggested_def
        })
        return out.content.strip()

