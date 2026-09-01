# ablations/offline_scorer.py
from __future__ import annotations

from dataclasses import dataclass

from ablations.abl_types import ScoreBreakdown, Top1Result, TopKResult, RoleCodeHistory
from ablations import adapters


@dataclass(frozen=True)
class Weights:
    w_pat: float
    w_dist: float
    w_prior: float

    def normalized(self) -> "Weights":
        s = self.w_pat + self.w_dist + self.w_prior
        if s <= 0:
            return Weights(0.0, 0.0, 0.0)
        return Weights(self.w_pat / s, self.w_dist / s, self.w_prior / s)


def deterministic_rank(
    *,
    stage: str,
    code_hist_all: RoleCodeHistory,
    code_hist_stage: RoleCodeHistory,
    weights: Weights,
    apply_blacklist: bool = True,
    topk: int = 1,
) -> TopKResult:
    """
    Deterministically rank candidate therapist codes.

    Production-faithful scoring:
        total = w_pat * pattern + w_dist * dist + w_prior * prior + stage_boost

    Important:
    - Production uses stage-local history for pattern, distribution, and GRU prior.
    - Candidate ties are effectively broken by original candidate order, because
      production sorts by total score only and Python sort is stable.
    """
    weights = weights.normalized()

    candidates = adapters.get_candidates(stage, apply_blacklist=apply_blacklist)
    if not candidates:
        raise ValueError(f"No candidates available for stage={stage} (apply_blacklist={apply_blacklist}).")

    target_dist = adapters.get_target_dist(stage)

    # Production uses stage-local history for sequence model input.
    priors = adapters.prior_probs(code_hist_stage)

    scored = []
    for idx, code in enumerate(candidates):
        # Production uses stage-local history for pattern matching.
        pat = adapters.pattern_indicator(code, code_hist_stage, stage)

        # Production uses stage-local history for stage distribution alignment.
        dist = adapters.dist_alignment_score(code_hist_stage, code, target_dist)

        prior = float(priors.get(code, 0.0))
        boost = adapters.get_stage_boost(stage, code)

        total = (
            weights.w_pat * pat
            + weights.w_dist * dist
            + weights.w_prior * prior
            + boost
        )

        scored.append((
            idx,
            code,
            ScoreBreakdown(
                pattern_score=pat,
                dist_score=dist,
                prior_prob=prior,
                stage_boost=boost,
                total_score=total,
            )
        ))

    # Match production more closely:
    # sort by total score only; stable sort preserves earlier candidate order on ties.
    scored.sort(key=lambda x: x[2].total_score, reverse=True)

    k = max(1, int(topk))
    return TopKResult(items=[(code, sc) for _, code, sc in scored[:k]])


def top1(
    *,
    stage: str,
    code_hist_all: RoleCodeHistory,
    code_hist_stage: RoleCodeHistory,
    weights: Weights,
    apply_blacklist: bool = True,
) -> Top1Result:
    tk = deterministic_rank(
        stage=stage,
        code_hist_all=code_hist_all,
        code_hist_stage=code_hist_stage,
        weights=weights,
        apply_blacklist=apply_blacklist,
        topk=1,
    )
    code, sc = tk.items[0]
    return Top1Result(code=code, score=sc)