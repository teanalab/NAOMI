# epe_helpers.py
import re
import random

# --- NEW: Phrasing Variations for EPE ---
INFO_PERMISSION_LINES = [
    "I have some information that you may find helpful. Would you like to hear it?",
    "A thought just came to mind that might be useful. May I share it with you?",
    "Based on what you've said, I have some information that could be relevant. Would you be open to hearing it?"
]

ADVICE_PERMISSION_LINES = [
    "[QECML+] I have a suggestion that you may find helpful. Would you like to hear it?",
    "[QECML+] I have an idea that might help with that. Would you be open to hearing it?",
    "[QECML+] Based on what you just said, I have a suggestion. Would you like me to share it?"
]

APPEND_ELICIT_LINES = [
    "What do you think?",
    "How does that sound to you?",
    "What are your thoughts on that?",
    "Does that resonate with you at all?"
]

def epe_permission_line(intent: str) -> str:
    """
    Returns the specific, hardcoded question to ask for permission.
    """
    if intent == "ADV+":
        return random.choice(ADVICE_PERMISSION_LINES)
    else: # Default to GINFO+
        return random.choice(INFO_PERMISSION_LINES)

def epe_decline_line() -> str:
    """
    Returns the specific, hardcoded response when the user declines.
    """
    # The code for acknowledging refusal is a complex reflection
    return "Sure, I totally understand and respect your choice."

def epe_append_elicit() -> str:
    """
    Returns the short elicitation phrase to append after providing info/advice.
    """
    return random.choice(APPEND_ELICIT_LINES)


# --- detection ---#
EPE_TAG_RE = re.compile(r"\[(GINFO\+|ADV\+)\]")

def extract_epe_intent(text: str) -> str | None:
    m = EPE_TAG_RE.search(text)
    return m.group(1) if m else None  # 'GINFO+' | 'ADV+' | None

# Strip a single leading [CODE] tag; keep other MI codes if you like.
def strip_leading_code_tag(text: str) -> str:
    return re.sub(r"^\s*\[[A-Z\+\-]{3,6}\]\s*", "", text).strip()

def sanitize_prompt_leakage(text: str) -> str:
    # Remove unwanted leakage patterns
    bad = (
        "Here is the summary in the exact format:",
        "In the exact format:",
        "As requested, here is the",
    )
    for p in bad:
        text = text.replace(p, "")
    
    # Synonymous phrases for "it sounds like "
    replacements = [
        "it seems like ",
        "it looks like ",
        "it appears that ",
        "from what you're saying, ",
        "so it feels like ",
        "it sounds like ",  # keep original as an option
    ]
    
    def _replace(match):
        phrase = random.choice(replacements)
        # If original starts with uppercase "I", capitalize replacement
        if match.group(0)[0].isupper():
            return phrase[0].upper() + phrase[1:]
        return phrase
    
    # Replace all case-insensitive matches
    text = re.sub(r"\bit sounds like ", _replace, text, flags=re.IGNORECASE)
    
    return text.strip()