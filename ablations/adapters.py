# ablations/adapters.py
from __future__ import annotations

from typing import Dict, List, Tuple

# ---- Project constants (root) ----
try:
    from constants import (
        HCP_CODES,
        MIIN_CODES,
        STAGE_SPECIFIC_BLOCKLIST,
        STAGE_CODE_BOOSTS,
        STAGE_DISTRIBUTIONS,
    )
except Exception as e:
    raise ImportError(
        "Failed to import required constants from constants.py at project root. "
        "Expected: HCP_CODES, MIIN_CODES, STAGE_SPECIFIC_BLOCKLIST, "
        "STAGE_CODE_BOOSTS, STAGE_DISTRIBUTIONS."
    ) from e


# ---- Local controller pattern rule + history helper ----
# Your pattern function is likely in v4_code_selector or a sibling module.
# We'll import it from versions/NAOMI_DCA and fall back gracefully if names differ.
try:
    from versions.NAOMI_DCA.v4_code_selector import is_valid_chain_followup  # type: ignore
except Exception as e:
    raise ImportError(
        "Failed to import is_valid_chain_followup from versions/NAOMI_DCA/v4_code_selector.py. "
        "If the function has a different name/location, update this import."
    ) from e


# ---- KL reduction score ----
# If you moved KL logic into v4_code_selector, point it here; otherwise keep v4_code_scorer.
# We'll try v4_code_selector first, then v4_code_scorer for backwards compatibility.
try:
    from versions.NAOMI_DCA.v4_code_scorer import kl_reduction_score  # type: ignore
except Exception:
    try:
        from v4_code_scorer import kl_reduction_score  # type: ignore
    except Exception as e:
        raise ImportError(
            "Failed to import kl_reduction_score. Tried:\n"
            "  - versions.NAOMI_DCA.v4_code_selector.kl_reduction_score\n"
            "  - v4_code_scorer.kl_reduction_score\n"
            "Update adapters.py to match your project."
        ) from e


# ---- GRU / prior ----
try:
    from versions.NAOMI_DCA.gru_module.gru_infer import get_code_probabilities  # type: ignore
except Exception as e:
    raise ImportError(
        "Failed to import versions.NAOMI_DCA.gru_module.gru_infer.get_code_probabilities. "
        "Update adapters.py if this is located elsewhere."
    ) from e

def get_candidates(stage: str, apply_blacklist: bool) -> List[str]:
    """
    Candidate set for selection:
    - HCP codes only
    - exclude MIIN codes
    - optionally exclude stage-specific blocklisted codes
    """
    block = set(STAGE_SPECIFIC_BLOCKLIST.get(stage, [])) if apply_blacklist else set()
    return [c for c in HCP_CODES if c not in MIIN_CODES and c not in block]


def get_stage_boost(stage: str, code: str) -> float:
    return float(STAGE_CODE_BOOSTS.get(stage, {}).get(code, 0.0))


def get_target_dist(stage: str) -> Dict[str, float]:
    """
    Stage target distribution T_p. Assumes STAGE_DISTRIBUTIONS[stage] is dict-like {code: prob}.
    """
    td = STAGE_DISTRIBUTIONS[stage]
    return dict(td)


def pattern_indicator(code: str, code_hist_all: Tuple[str, ...], stage: str) -> float:
    """Binary indicator for whether code completes an expert-curated pattern given history."""
    ok = is_valid_chain_followup(code, code_hist_all, stage)
    return 1.0 if ok else 0.0


def dist_alignment_score(
    code_hist_stage: Tuple[str, ...],
    code: str,
    target_dist: Dict[str, float],
) -> float:
    """
    Delegates to kl_reduction_score.
    Expected signature: kl_reduction_score(history_codes, candidate_code, target_dist_dict)
    """
    return float(kl_reduction_score(code_hist_stage, code, target_dist))


def prior_probs(code_hist_all: Tuple[str, ...]) -> Dict[str, float]:
    """
    Delegates to GRU inference.
    Expected signature: get_code_probabilities(history_codes) -> dict(code -> prob or score)
    Returns normalized nonnegative probabilities.
    """
    raw = get_code_probabilities(code_hist_all) or {}

    clean: Dict[str, float] = {}
    for k, v in raw.items():
        try:
            fv = float(v)
        except Exception:
            continue
        clean[str(k)] = max(0.0, fv)

    s = sum(clean.values())
    if s <= 0.0:
        return {}
    return {k: (v / s) for k, v in clean.items()}