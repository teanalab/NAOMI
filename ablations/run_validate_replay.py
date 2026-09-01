# ablations/run_validate_replay.py
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from ablations.data_loader import load_turns_from_transcript_dir
from ablations.offline_scorer import top1, Weights


def _session_stats_dict(n: int, m: int) -> dict:
    matches = n - m
    return {
        "n": n,
        "matches": matches,
        "mismatches": m,
        "replay_accuracy": (matches / n) if n else 0.0,
        "mismatch_rate": (m / n) if n else 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--transcript_dir",
        required=True,
        help="Directory containing per-session transcript-code JSON files",
    )
    ap.add_argument("--w_pat", type=float, required=True)
    ap.add_argument("--w_dist", type=float, required=True)
    ap.add_argument("--w_prior", type=float, required=True)
    ap.add_argument("--out", default="outputs/validate_replay.json")
    ap.add_argument(
        "--max_mismatches",
        type=int,
        default=200,
        help="Maximum number of mismatch examples to save",
    )
    ap.add_argument(
        "--top_sessions_k",
        type=int,
        default=10,
        help="How many best/worst sessions to include in summary",
    )
    args = ap.parse_args()

    turns = load_turns_from_transcript_dir(transcript_dir=args.transcript_dir)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    weights = Weights(args.w_pat, args.w_dist, args.w_prior)

    mismatches = []
    per_stage = defaultdict(lambda: {"n": 0, "m": 0})
    per_session = defaultdict(lambda: {"n": 0, "m": 0})

    for t in turns:
        pred = top1(
            stage=t.stage,
            code_hist_all=t.code_hist_all,
            code_hist_stage=t.code_hist_stage,
            weights=weights,
            apply_blacklist=True,
        )

        per_stage[t.stage]["n"] += 1
        per_session[t.session_id]["n"] += 1

        if pred.code != t.logged_code:
            per_stage[t.stage]["m"] += 1
            per_session[t.session_id]["m"] += 1

            if len(mismatches) < args.max_mismatches:
                mismatches.append(
                    {
                        "session_id": t.session_id,
                        "turn_id": t.turn_id,
                        "idx_in_session": t.idx_in_session,
                        "stage": t.stage,
                        "logged_code": t.logged_code,
                        "offline_code": pred.code,
                        "offline_score": asdict(pred.score),
                        "hist_all_len": len(t.code_hist_all),
                        "hist_stage_len": len(t.code_hist_stage),
                    }
                )

    total_turns = len(turns)
    mismatch_count = sum(v["m"] for v in per_stage.values())
    match_count = total_turns - mismatch_count

    per_stage_summary = {
        stage: _session_stats_dict(stats["n"], stats["m"])
        for stage, stats in sorted(per_stage.items())
    }

    per_session_summary = {
        session_id: _session_stats_dict(stats["n"], stats["m"])
        for session_id, stats in sorted(per_session.items())
    }

    # Ranked views
    k = max(1, int(args.top_sessions_k))

    worst_sessions_by_mismatch_rate = sorted(
        (
            {"session_id": sid, **stats}
            for sid, stats in per_session_summary.items()
        ),
        key=lambda x: (x["mismatch_rate"], x["mismatches"], x["n"], x["session_id"]),
        reverse=True,
    )[:k]

    best_sessions_by_replay_accuracy = sorted(
        (
            {"session_id": sid, **stats}
            for sid, stats in per_session_summary.items()
        ),
        key=lambda x: (x["replay_accuracy"], x["matches"], x["n"], x["session_id"]),
        reverse=True,
    )[:k]

    worst_sessions_by_mismatch_count = sorted(
        (
            {"session_id": sid, **stats}
            for sid, stats in per_session_summary.items()
        ),
        key=lambda x: (x["mismatches"], x["mismatch_rate"], x["n"], x["session_id"]),
        reverse=True,
    )[:k]

    summary = {
        "total_turns": total_turns,
        "matches": match_count,
        "mismatches": mismatch_count,
        "replay_accuracy": (match_count / total_turns) if total_turns else 0.0,
        "mismatch_rate": (mismatch_count / total_turns) if total_turns else 0.0,
        "per_stage": per_stage_summary,
        "per_session": per_session_summary,
        "worst_sessions_by_mismatch_rate": worst_sessions_by_mismatch_rate,
        "best_sessions_by_replay_accuracy": best_sessions_by_replay_accuracy,
        "worst_sessions_by_mismatch_count": worst_sessions_by_mismatch_count,
        "weights": {
            "w_pat": args.w_pat,
            "w_dist": args.w_dist,
            "w_prior": args.w_prior,
        },
        "n_saved_mismatch_examples": len(mismatches),
    }

    payload = {
        "summary": summary,
        "mismatches": mismatches,
    }

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()