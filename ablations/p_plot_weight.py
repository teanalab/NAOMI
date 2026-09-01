import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# =============================
# Paths
# =============================
json_path = Path("ablations/outputs/weight_sweep_005.json")   # change if needed
plot_dir = Path("ablations/plots")
plot_dir.mkdir(parents=True, exist_ok=True)

# =============================
# Load JSON
# =============================
with json_path.open("r", encoding="utf-8") as f:
    payload = json.load(f)

results = payload["results"]
baseline = payload["meta"]["baseline_weights"]

# =============================
# Flatten into DataFrame
# =============================
rows = []
for r in results:
    row = {
        "w_pat": r["weights"]["w_pat"],
        "w_dist": r["weights"]["w_dist"],
        "w_prior": r["weights"]["w_prior"],
        "ccr": r["ccr_vs_baseline_replay"],
        "mean_kl": r["mean_kl"],
    }
    for stage, val in r["kl_by_stage"].items():
        row[f"kl_{stage}"] = val
    rows.append(row)

df = pd.DataFrame(rows)

# Save flattened CSV too
df.to_csv(plot_dir / "weight_sweep_flat.csv", index=False)

print("Top 10 by lowest mean_kl:")
print(df.sort_values("mean_kl").head(10)[["w_pat", "w_dist", "w_prior", "ccr", "mean_kl"]])

print("\nTop 10 by lowest ccr:")
print(df.sort_values("ccr").head(10)[["w_pat", "w_dist", "w_prior", "ccr", "mean_kl"]])


# =============================
# Helper: heatmap
# =============================
def make_heatmap(value_col: str, title: str, filename: str):
    pivot = df.pivot(index="w_pat", columns="w_dist", values=value_col)
    pivot = pivot.sort_index().sort_index(axis=1)

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(pivot.values, origin="lower", aspect="auto")

    ax.set_title(title)
    ax.set_xlabel("w_dist")
    ax.set_ylabel("w_pat")

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{x:.2f}" for x in pivot.columns], rotation=45)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{y:.2f}" for y in pivot.index])

    if baseline["w_pat"] in pivot.index and baseline["w_dist"] in pivot.columns:
        y = list(pivot.index).index(baseline["w_pat"])
        x = list(pivot.columns).index(baseline["w_dist"])
        ax.scatter(x, y, marker="x", s=120)

    fig.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(plot_dir / filename, dpi=200, bbox_inches="tight")
    plt.close()


# =============================
# Plot 1: CCR heatmap
# =============================
make_heatmap(
    value_col="ccr",
    title="Decision Change Rate vs Baseline Replay",
    filename="heatmap_ccr.png",
)

# =============================
# Plot 2: Mean KL heatmap
# =============================
make_heatmap(
    value_col="mean_kl",
    title="Mean KL to Stage Targets",
    filename="heatmap_mean_kl.png",
)

# =============================
# Plot 3: Scatter of KL vs CCR
# =============================
fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter(df["ccr"], df["mean_kl"], alpha=0.8)
ax.set_xlabel("Decision Change Rate vs Baseline Replay")
ax.set_ylabel("Mean KL")
ax.set_title("Tradeoff: Stability vs Distribution Alignment")

baseline_mask = (
    (df["w_pat"] == baseline["w_pat"]) &
    (df["w_dist"] == baseline["w_dist"]) &
    (df["w_prior"] == baseline["w_prior"])
)
if baseline_mask.any():
    b = df[baseline_mask].iloc[0]
    ax.scatter([b["ccr"]], [b["mean_kl"]], marker="x", s=120)
    ax.annotate(
        "baseline",
        (b["ccr"], b["mean_kl"]),
        xytext=(8, 8),
        textcoords="offset points"
    )

plt.tight_layout()
plt.savefig(plot_dir / "scatter_ccr_vs_mean_kl.png", dpi=200, bbox_inches="tight")
plt.close()

# =============================
# Plot 4: Per-stage KL vs w_pat for points with baseline w_prior
# =============================
slice_df = df[df["w_prior"].round(6) == round(baseline["w_prior"], 6)].copy()
slice_df = slice_df.sort_values(["w_pat", "w_dist"])

if not slice_df.empty:
    fig, ax = plt.subplots(figsize=(8, 5))
    for col in ["kl_ENGAGING", "kl_FOCUSING", "kl_EVOKING", "kl_PLANNING"]:
        if col in slice_df.columns:
            ax.plot(slice_df["w_pat"], slice_df[col], marker="o", label=col.replace("kl_", ""))

    ax.set_xlabel("w_pat")
    ax.set_ylabel("KL")
    ax.set_title("Per-Stage KL when w_prior is fixed at baseline")
    ax.legend()
    plt.tight_layout()
    plt.savefig(plot_dir / "per_stage_kl_fixed_prior.png", dpi=200, bbox_inches="tight")
    plt.close()

# =============================
# Plot 5: Top 15 best points by lowest mean KL
# =============================
best15 = df.sort_values("mean_kl").head(15).copy()
best15["label"] = best15.apply(
    lambda r: f"({r['w_pat']:.2f},{r['w_dist']:.2f},{r['w_prior']:.2f})",
    axis=1
)

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(best15["label"], best15["mean_kl"])
ax.set_xlabel("(w_pat, w_dist, w_prior)")
ax.set_ylabel("Mean KL")
ax.set_title("Top 15 Weight Settings by Lowest Mean KL")
plt.xticks(rotation=60, ha="right")
plt.tight_layout()
plt.savefig(plot_dir / "best15_mean_kl.png", dpi=200, bbox_inches="tight")
plt.close()

print(f"\nSaved plots to: {plot_dir.resolve()}")
print("Files created:")
for p in sorted(plot_dir.glob("*")):
    print(" -", p.name)