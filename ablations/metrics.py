# Core metrics for CCR, blacklist pressure, KL-to-target (robust).
# ablations/metrics.py
from __future__ import annotations
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

import math

EPS = 1e-9


def code_change_rate(baseline_codes: List[str], other_codes: List[str]) -> float:
    assert len(baseline_codes) == len(other_codes)
    if not baseline_codes:
        return 0.0
    changed = sum(1 for a, b in zip(baseline_codes, other_codes) if a != b)
    return changed / len(baseline_codes)


def grouped_codes_by_stage(stages: List[str], codes: List[str]) -> Dict[str, List[str]]:
    assert len(stages) == len(codes)
    out = defaultdict(list)
    for s, c in zip(stages, codes):
        out[s].append(c)
    return dict(out)


def empirical_dist(codes: List[str], support: List[str]) -> Dict[str, float]:
    """
    Smoothed empirical distribution over support.
    """
    n = len(codes)
    counts = Counter(codes)
    k = len(support)
    denom = n + EPS * k
    return {c: (counts.get(c, 0) + EPS) / denom for c in support}


def kl_divergence(p: Dict[str, float], q: Dict[str, float]) -> float:
    """
    KL(P || Q) with small epsilon guard already in p/q.
    """
    s = 0.0
    for k, pv in p.items():
        qv = q.get(k, EPS)
        s += pv * math.log(pv / qv)
    return float(s)


def stage_kl_to_target(
    stage_codes: Dict[str, List[str]],
    stage_targets: Dict[str, Dict[str, float]],
    support: List[str],
) -> Dict[str, float]:
    """
    Returns KL(E_stage || T_stage) per stage, with smoothing.
    """
    out = {}
    for stage, codes in stage_codes.items():
        if stage not in stage_targets:
            continue
        p = empirical_dist(codes, support=support)
        # ensure target has eps for all support
        t_raw = stage_targets[stage]
        t = {c: max(EPS, float(t_raw.get(c, 0.0))) for c in support}
        # renormalize target
        z = sum(t.values())
        t = {c: v / z for c, v in t.items()}
        out[stage] = kl_divergence(p, t)
    return out


def blacklist_pressure_rate(
    unconstrained_top1: List[str],
    stages: List[str],
    stage_blocklists: Dict[str, List[str]],
) -> float:
    assert len(unconstrained_top1) == len(stages)
    if not stages:
        return 0.0
    viol = 0
    for c, s in zip(unconstrained_top1, stages):
        if c in set(stage_blocklists.get(s, [])):
            viol += 1
    return viol / len(stages)


def pattern_hit_rate(pattern_hits: List[float]) -> float:
    """
    pattern_hits should be 0/1 per turn.
    """
    if not pattern_hits:
        return 0.0
    return sum(pattern_hits) / len(pattern_hits)