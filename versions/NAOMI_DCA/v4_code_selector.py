import numpy as np
from constants import (
    STAGE_CHAINS, HCP_CODES, STAGE_DISTRIBUTIONS, CODE_TO_GROUP, MIIN_CODES,
    STAGE_SPECIFIC_BLOCKLIST, STAGE_CODE_BOOSTS
)
from .v4_code_scorer import score_candidate, get_empirical_dist  
from .gru_module.gru_infer import get_code_probabilities

# ===================== Helpers =====================
def ensure_tuple_history(history):
    """Normalize history to [(role, code), ...]."""
    out = []
    for item in history:
        if isinstance(item, tuple) and len(item) == 2:
            out.append(item)
        elif isinstance(item, dict) and "code" in item:
            out.append((item.get("role", "T"), item["code"]))
        elif isinstance(item, str):
            out.append(("T", item))
    return out

# ===================== Chain Matcher =====================
def _code_left_matches(pattern_code, actual_code):
    """
    Check if an actual code from history matches a pattern code,
    supporting wildcards and group names.
    """
    if pattern_code == "*" or pattern_code == actual_code:
        return True
    grp = CODE_TO_GROUP.get(actual_code)
    return grp == pattern_code

def is_valid_chain_followup(code, history, stage):
    """
    Check if a candidate code is the expected follow-up to a recent
    sequence of turns that matches a defined pattern.
    """
    chains = STAGE_CHAINS.get(stage, [])
    n_hist = len(history)

    for pattern, expected_code in chains:
        if n_hist < len(pattern):
            continue
        recent = history[-len(pattern):]

        if all(_code_left_matches(p_code, h_code) and p_role == h_role 
               for (p_role, p_code), (h_role, h_code) in zip(pattern, recent)):
            if expected_code == code:
                return True
    return False


# ===================== Main Selection Logic =====================
def select_next_code(session_data):
    """
    Scores all valid candidates and selects the next therapist code.
    """
    stage   = session_data["stage"]
    history = ensure_tuple_history(session_data["stage_codes"][stage])

    # Get the blocklist for the current stage.
    stage_blocklist = STAGE_SPECIFIC_BLOCKLIST.get(stage, [])
    
    # Filter out MIIN codes AND stage-specific forbidden codes.
    candidates = [
        code for code in HCP_CODES
        if code not in MIIN_CODES and code not in stage_blocklist
    ]

    # Get next-code probabilities from the sequence model.
    raw = get_code_probabilities(history) or {}
    s = sum(max(0.0, float(p)) for p in raw.values())
    seq_probs = {k: (max(0.0, float(v)) / s if s > 0 else 0.0) for k, v in raw.items()}

    # Get the boost values for the current stage.
    stage_boosts = STAGE_CODE_BOOSTS.get(stage, {})

    scored = []
    for code in candidates:
        # The _would_overfill_group check has been removed.
        # if _would_overfill_group(code, history, stage):
        #     continue

        pattern_match = is_valid_chain_followup(code, history, stage)
        boost = stage_boosts.get(code, 0.0)

        total_score = score_candidate(
            code=code,
            history=history,
            stage=stage,
            model_prob=seq_probs.get(code, 0.0),
            pattern_match=pattern_match,
            boost_value=boost
        )
        scored.append((code, float(total_score)))

    # Fallback logic to prevent crashing if all candidates are filtered out.
    if not scored or all(s <= 0 for _, s in scored):
        print("[SELECTOR] All candidates were filtered or had zero score. Using fallback logic.")
        scored = [(code, 1.0) for code in candidates]

    scored.sort(key=lambda x: x[1], reverse=True)
    
    chosen_code = scored[0][0] if scored else None
    
    # --- ADDED: Print statement for debugging the final choice ---
    print(f"Therapist chosen code: {chosen_code}")
    
    return chosen_code

