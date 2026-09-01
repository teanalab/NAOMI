# ablations/best_weights.py
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple

from ablations.data_loader import load_turns_from_transcript_dir
from ablations.offline_scorer import top1, Weights
from ablations.metrics import grouped_codes_by_stage, stage_kl_to_target, code_change_rate
from ablations.adapters import STAGE_DISTRIBUTIONS, HCP_CODES, MIIN_CODES


SUPPORT = [c for c in HCP_CODES if c not in MIIN_CODES]


def iter_grid(step: float) -> List[Tuple[float, float, float]]:
    pts = []
    n = int(round(1.0 / step))
    values = [round(i * step, 10) for i in range(n + 1)]

    for w_pat in values:
        for w_dist in values:
            if w_pat + w_dist > 1.0 + 1e-12:
                continue
            w_prior = round(max(0.0, 1.0 - w_pat - w_dist), 10)
            pts.append((w_pat, w_dist, w_prior))

    return pts


def minmax_norm(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return (x - lo) / (hi - lo)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--transcript_dir",
        required=True,
        help="Directory containing per-session transcript-code JSON files",
    )
    ap.add_argument("--step", type=float, default=0.05)
    ap.add_argument(
        "--baseline_w_pat",
        type=float,
        default=0.70,
    )
    ap.add_argument(
        "--baseline_w_dist",
        type=float,
        default=0.25,
    )
    ap.add_argument(
        "--baseline_w_prior",
        type=float,
        default=0.05,
    )
    ap.add_argument(
        "--balance_alpha",
        type=float,
        default=0.5,
        help="Weight on normalized CCR in balanced score; 1-alpha is weight on normalized mean KL",
    )
    ap.add_argument("--out", default="ablations/outputs/weight_sweep.json")
    args = ap.parse_args()

    turns = load_turns_from_transcript_dir(transcript_dir=args.transcript_dir)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    baseline_w = Weights(
        args.baseline_w_pat,
        args.baseline_w_dist,
        args.baseline_w_prior,
    ).normalized()

    stages = [t.stage for t in turns]

    # Baseline replay predictions
    baseline_replay_codes = []
    for t in turns:
        pred = top1(
            stage=t.stage,
            code_hist_all=t.code_hist_all,
            code_hist_stage=t.code_hist_stage,
            weights=baseline_w,
            apply_blacklist=True,
        )
        baseline_replay_codes.append(pred.code)

    grid = iter_grid(args.step)

    results = []
    for (w_pat, w_dist, w_prior) in grid:
        w = Weights(w_pat, w_dist, w_prior).normalized()

        sweep_codes = []
        for t in turns:
            pred = top1(
                stage=t.stage,
                code_hist_all=t.code_hist_all,
                code_hist_stage=t.code_hist_stage,
                weights=w,
                apply_blacklist=True,
            )
            sweep_codes.append(pred.code)

        ccr = code_change_rate(baseline_replay_codes, sweep_codes)

        stage_codes = grouped_codes_by_stage(stages, sweep_codes)
        stage_targets = {k: dict(v) for k, v in STAGE_DISTRIBUTIONS.items()}
        kls = stage_kl_to_target(stage_codes, stage_targets, support=SUPPORT)
        mean_kl = sum(kls.values()) / len(kls) if kls else 0.0

        results.append({
            "weights": {
                "w_pat": w.w_pat,
                "w_dist": w.w_dist,
                "w_prior": w.w_prior,
            },
            "ccr_vs_baseline_replay": ccr,
            "kl_by_stage": kls,
            "mean_kl": mean_kl,
        })

    # Find "best" points
    best_by_kl = min(results, key=lambda r: r["mean_kl"]) if results else None
    best_by_ccr = min(results, key=lambda r: r["ccr_vs_baseline_replay"]) if results else None

    # Balanced score = alpha * normalized_CCR + (1-alpha) * normalized_mean_KL
    if results:
        ccr_vals = [r["ccr_vs_baseline_replay"] for r in results]
        kl_vals = [r["mean_kl"] for r in results]
        ccr_lo, ccr_hi = min(ccr_vals), max(ccr_vals)
        kl_lo, kl_hi = min(kl_vals), max(kl_vals)

        alpha = float(args.balance_alpha)

        for r in results:
            norm_ccr = minmax_norm(r["ccr_vs_baseline_replay"], ccr_lo, ccr_hi)
            norm_kl = minmax_norm(r["mean_kl"], kl_lo, kl_hi)
            r["balanced_score"] = alpha * norm_ccr + (1.0 - alpha) * norm_kl

        best_balanced = min(results, key=lambda r: r["balanced_score"])
    else:
        best_balanced = None

    payload = {
        "meta": {
            "grid_step": args.step,
            "n_turns": len(turns),
            "baseline_weights": {
                "w_pat": baseline_w.w_pat,
                "w_dist": baseline_w.w_dist,
                "w_prior": baseline_w.w_prior,
            },
            "balance_alpha": args.balance_alpha,
        },
        "best": {
            "best_by_mean_kl": best_by_kl,
            "best_by_ccr": best_by_ccr,
            "best_balanced": best_balanced,
        },
        "results": results,
    }

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Saved: {out_path}")
    print("\nBest by mean KL:")
    print(json.dumps(best_by_kl, indent=2))
    print("\nBest by CCR:")
    print(json.dumps(best_by_ccr, indent=2))
    print("\nBest balanced:")
    print(json.dumps(best_balanced, indent=2))


if __name__ == "__main__":
    main()