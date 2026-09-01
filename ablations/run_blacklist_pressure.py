# ablations/run_blacklist_pressure.py
from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import Counter, defaultdict

from ablations.data_loader import load_turns_from_transcript_dir
from ablations.offline_scorer import top1, Weights
from ablations.adapters import STAGE_SPECIFIC_BLOCKLIST


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
    ap.add_argument("--out", default="outputs/blacklist_pressure.json")
    args = ap.parse_args()

    turns = load_turns_from_transcript_dir(transcript_dir=args.transcript_dir)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    w = Weights(args.w_pat, args.w_dist, args.w_prior).normalized()

    pressure_count = 0
    changed_count = 0

    per_stage = defaultdict(lambda: {
        "n": 0,
        "pressure": 0,
        "changed": 0,
    })

    forbidden_code_counts = Counter()

    for t in turns:
        uncon = top1(
            stage=t.stage,
            code_hist_all=t.code_hist_all,
            code_hist_stage=t.code_hist_stage,
            weights=w,
            apply_blacklist=False,
        )

        con = top1(
            stage=t.stage,
            code_hist_all=t.code_hist_all,
            code_hist_stage=t.code_hist_stage,
            weights=w,
            apply_blacklist=True,
        )

        forbidden_set = set(STAGE_SPECIFIC_BLOCKLIST.get(t.stage, []))
        is_forbidden = uncon.code in forbidden_set
        is_changed = (uncon.code != con.code)

        pressure_count += int(is_forbidden)
        changed_count += int(is_changed)

        per_stage[t.stage]["n"] += 1
        per_stage[t.stage]["pressure"] += int(is_forbidden)
        per_stage[t.stage]["changed"] += int(is_changed)

        if is_forbidden:
            forbidden_code_counts[uncon.code] += 1

    total = len(turns)

    summary = {
        "total_turns": total,
        "blacklist_pressure_rate": (pressure_count / total) if total else 0.0,
        "blacklist_decision_change_rate": (changed_count / total) if total else 0.0,
        "weights": w.__dict__,
        "per_stage": {
            s: {
                "n": v["n"],
                "blacklist_pressure_count": v["pressure"],
                "blacklist_pressure_rate": (v["pressure"] / v["n"]) if v["n"] else 0.0,
                "decision_change_count": v["changed"],
                "decision_change_rate": (v["changed"] / v["n"]) if v["n"] else 0.0,
            }
            for s, v in sorted(per_stage.items())
        },
        "top_forbidden_unconstrained_codes": forbidden_code_counts.most_common(20),
    }

    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"summary": summary}, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()