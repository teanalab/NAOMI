from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


RoleCodeHistory = Tuple[Tuple[str, str], ...]
# Example:
# (("T", "AF"), ("C", "CHT+"), ("T", "RCHT+"))


@dataclass(frozen=True)
class Turn:
    session_id: str
    turn_id: str                 # stable id, e.g. f"{session_id}:{idx}"
    idx_in_session: int
    stage: str
    logged_code: str             # therapist code actually selected in logs
    code_hist_all: RoleCodeHistory     # prior mixed history across all stages
    code_hist_stage: RoleCodeHistory   # prior mixed history within current stage


@dataclass(frozen=True)
class ScoreBreakdown:
    pattern_score: float
    dist_score: float
    prior_prob: float
    stage_boost: float
    total_score: float


@dataclass(frozen=True)
class Top1Result:
    code: str
    score: ScoreBreakdown


@dataclass(frozen=True)
class TopKResult:
    items: List[Tuple[str, ScoreBreakdown]]  # sorted desc