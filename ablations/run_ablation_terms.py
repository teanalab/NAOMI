# Runs no_pattern / no_dist / no_prior as one-step counterfactual vs logged baseline.

# ablations/run_ablation_terms.py
from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import defaultdict

from ablations.data_loader import load_turns_from_transcript_dir
from ablations.offline_scorer import top1, Weights


def renorm(w_pat: float, w_dist: float, w_prior: float) -> Weights:
    return Weights(w_pat, w_dist, w_prior).normalized()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--transcript_dir",
        required=True,
        help="Directory containing per-session transcript-code JSON files",
    )
    ap.add_argument(
        "--variant",
        required=True,
        choices=["no_pattern", "no_dist", "no_prior"],
    )
    ap.add_argument("--w_pat", type=float, required=True)
    ap.add_argument("--w_dist", type=float, required=True)
    ap.add_argument("--w_prior", type=float, required=True)
    ap.add_argument(
        "--out",
        default=None,
        help="Output JSON (default: outputs/ablation_<variant>.json)",
    )
    args = ap.parse_args()

    turns = load_turns_from_transcript_dir(transcript_dir=args.transcript_dir)

    # Baseline production-faithful weights
    w0 = Weights(args.w_pat, args.w_dist, args.w_prior).normalized()

    # Ablated weights
    if args.variant == "no_pattern":
        wa = renorm(0.0, w0.w_dist, w0.w_prior)
    elif args.variant == "no_dist":
        wa = renorm(w0.w_pat, 0.0, w0.w_prior)
    else:  # no_prior
        wa = renorm(w0.w_pat, w0.w_dist, 0.0)

    out_path = Path(args.out or f"ablations/outputs/ablation_{args.variant}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    changed = 0
    baseline_match_logged = 0
    per_stage = defaultdict(lambda: {"n": 0, "changed": 0, "baseline_match_logged": 0})


    for t in turns:
        baseline_pred = top1(
            stage=t.stage,
            code_hist_all=t.code_hist_all,
            code_hist_stage=t.code_hist_stage,
            weights=w0,
            apply_blacklist=True,
        )

        ablated_pred = top1(
            stage=t.stage,
            code_hist_all=t.code_hist_all,
            code_hist_stage=t.code_hist_stage,
            weights=wa,
            apply_blacklist=True,
        )
        # rows = []
        is_changed = (ablated_pred.code != baseline_pred.code)
        base_matches_logged = (baseline_pred.code == t.logged_code)

        changed += int(is_changed)
        baseline_match_logged += int(base_matches_logged)

        per_stage[t.stage]["n"] += 1
        per_stage[t.stage]["changed"] += int(is_changed)
        per_stage[t.stage]["baseline_match_logged"] += int(base_matches_logged)

        # rows.append({
        #     "session_id": t.session_id,
        #     "turn_id": t.turn_id,
        #     "idx_in_session": t.idx_in_session,
        #     "stage": t.stage,
        #     "logged_code": t.logged_code,
        #     "baseline_code": baseline_pred.code,
        #     "ablated_code": ablated_pred.code,
        #     "changed_vs_baseline": is_changed,
        #     "baseline_matches_logged": base_matches_logged,
        #     "baseline_score": baseline_pred.score.__dict__,
        #     "ablated_score": ablated_pred.score.__dict__,
        # })

    total = len(turns)

    summary = {
        "variant": args.variant,
        "total_turns": total,
        "decision_change_rate": (changed / total) if total else 0.0,
        "baseline_replay_accuracy_vs_logged": (baseline_match_logged / total) if total else 0.0,
        "weights_baseline": w0.__dict__,
        "weights_ablated": wa.__dict__,
        "per_stage": {
            s: {
                "n": v["n"],
                "changed": v["changed"],
                "decision_change_rate": (v["changed"] / v["n"]) if v["n"] else 0.0,
                "baseline_replay_accuracy_vs_logged": (
                    v["baseline_match_logged"] / v["n"]
                ) if v["n"] else 0.0,
            }
            for s, v in sorted(per_stage.items())
        },
    }

    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"summary": summary}, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()