# v4_code_scorer.py

import numpy as np
from scipy.special import rel_entr
from collections import Counter
from constants import STAGE_DISTRIBUTIONS, HCP_CODES, CODE_TO_GROUP

# ===== Weights (REVISED for clear priority) =====
W_CHAIN = 0.70   # Priority 1: Follow conversational rules
W_DIST  = 0.25   # Priority 2: Maintain stage-appropriate conversation mix
W_MODEL = 0.05   # Priority 3: Use ML model as a tie-breaker

def ensure_tuple_history(history):
    """
    Ensures that the history is a list of (role, code) tuples.
    """
    out = []
    for item in history:
        if isinstance(item, tuple) and len(item) == 2:
            out.append(item)
        elif isinstance(item, dict) and "code" in item:
            out.append((item.get("role", "T"), item["code"]))
        elif isinstance(item, str):
            out.append(("T", item))
    return out


# ---------- KL Divergence Helpers ----------
# NOTE on implementation: We use `scipy.special.rel_entr` to calculate the 
# Kullback-Leibler (KL) Divergence. This function is a direct, element-wise 
# implementation of the formula's core (p * log(p/q)) and works perfectly 
# with standard probability vectors.
def _ordered_keys(target_dist: dict):
    """Preserve the order used in STAGE_DISTRIBUTIONS[stage]."""
    return list(target_dist.keys())

def _kl_vec(p_vec, q_vec) -> float:
    p = np.array(p_vec, dtype=float) + 1e-8
    q = np.array(q_vec, dtype=float) + 1e-8
    return float(np.sum(rel_entr(p, q)))


# ---------- Empirical Distribution Helper ----------
def get_empirical_dist(history, target_dist):
    """
    Returns a numpy vector matching the order of target_dist's keys,
    representing the observed frequency of therapist code groups.
    """
    keys = _ordered_keys(target_dist)
    hist = ensure_tuple_history(history)

    counts = Counter()
    for role, code in hist:
        if role != "T":
            continue
        grp = CODE_TO_GROUP.get(code)
        if grp in target_dist:
            counts[grp] += 1

    total = sum(counts.values())
    if total == 0:
        return np.array([1.0 / len(keys)] * len(keys))

    return np.array([counts[k] / total for k in keys], dtype=float)


def kl_reduction_score(history, candidate_code: str, target_dist: dict, beta: float = 1.0) -> float:
    """
    Computes how much adding a `candidate_code` would reduce the KL divergence
    between the conversation's statistics and the ideal target distribution.
    """
    keys = _ordered_keys(target_dist)
    target_vec = np.array([target_dist[k] for k in keys], dtype=float)

    before = get_empirical_dist(history, target_dist)
    after  = get_empirical_dist(list(ensure_tuple_history(history)) + [("T", candidate_code)], target_dist)

    delta = _kl_vec(before, target_vec) - _kl_vec(after, target_vec)
    return 1.0 - np.exp(-beta * max(0.0, float(delta)))


# ---------- Master Scorer ----------
def score_candidate(code, history, stage, model_prob, pattern_match, boost_value):
    """
    Calculates a unified score for a candidate code, now including an additive boost.
    """
    if code not in HCP_CODES:
        raise ValueError(f"Invalid HCP code: {code}")

    target_dist = STAGE_DISTRIBUTIONS[stage]

    # 1. Normalize scores to be on a 0-1 scale
    pattern_score = 1.0 if pattern_match else 0.0
    kl_score = kl_reduction_score(history, code, target_dist)
    try:
        model_prob = max(0.0, min(1.0, float(model_prob)))
    except Exception:
        model_prob = 0.0

    # Calculate the weighted average base score
    base_score = (
        W_CHAIN * pattern_score +
        W_DIST  * kl_score +
        W_MODEL * model_prob
    )

    # Add the stage-specific boost to the final score
    total = base_score + boost_value

    # print(f"[SCORER] code={code:8} | pattern={pattern_score:.1f} | kl={kl_score:.3f} | "
    #       f"model={model_prob:.3f} | boost={boost_value:.3f} -> total={total:.3f}")

    return float(total)

