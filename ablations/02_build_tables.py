import pandas as pd

# Load CSV
df = pd.read_csv("grades_matrix_v2.csv")   # change filename if needed

# Organize by judge
judge_scores = {
    "GPT Judge": {
        "ND": "nd_grade_gpt",
        "AD": "ad_grade_gpt",
        "SO": "so_grade_gpt",
    },
    "Gemini Judge": {
        "ND": "nd_grade_gemini",
        "AD": "ad_grade_gemini",
        "SO": "so_grade_gemini",
    },
    "Llama Judge": {
        "ND": "nd_grade_llama",
        "AD": "ad_grade_llama",
        "SO": "so_grade_llama",
    },
}

conditions = ["ND", "AD", "SO"]

# Mean score for each judge under each condition
results = {}
for judge, cols in judge_scores.items():
    means = {cond: df[col].mean() for cond, col in cols.items()}
    ranking = sorted(means.items(), key=lambda x: x[1], reverse=True)

    results[judge] = {
        "means": means,
        "ranking": ranking,
        "best_condition": ranking[0][0],
        "best_score": ranking[0][1],
        "worst_condition": ranking[-1][0],
        "worst_score": ranking[-1][1],
        "spread": ranking[0][1] - ranking[-1][1],
        "diffs": {
            "AD - ND": means["AD"] - means["ND"],
            "SO - ND": means["SO"] - means["ND"],
            "AD - SO": means["AD"] - means["SO"],
        }
    }

# Overall condition means across all three judges
overall_condition_means = {}
for cond in conditions:
    cols = [judge_scores[j][cond] for j in judge_scores]
    overall_condition_means[cond] = df[cols].mean().mean()

overall_ranking = sorted(overall_condition_means.items(), key=lambda x: x[1], reverse=True)

# Count how often each condition is best across judges
best_counts = {cond: 0 for cond in conditions}
for judge in results:
    best_counts[results[judge]["best_condition"]] += 1

# Print structured summary
print("=" * 70)
print("LLM-READABLE SUMMARY OF PROMPT-CONDITION RESULTS")
print("=" * 70)

print("\n1. Overall average score by condition (averaged across all judges):")
for cond, score in overall_ranking:
    print(f"   - {cond}: {score:.3f}")

print("\n2. Per-judge trends:")
for judge, info in results.items():
    print(f"\n   {judge}:")
    print(
        f"   - Mean scores: "
        f"ND={info['means']['ND']:.3f}, "
        f"AD={info['means']['AD']:.3f}, "
        f"SO={info['means']['SO']:.3f}"
    )
    print(
        f"   - Ranking: "
        + " > ".join([f"{cond} ({score:.3f})" for cond, score in info["ranking"]])
    )
    print(
        f"   - Best condition: {info['best_condition']} "
        f"({info['best_score']:.3f})"
    )
    print(
        f"   - Worst condition: {info['worst_condition']} "
        f"({info['worst_score']:.3f})"
    )
    print(
        f"   - Differences: "
        f"AD-ND={info['diffs']['AD - ND']:+.3f}, "
        f"SO-ND={info['diffs']['SO - ND']:+.3f}, "
        f"AD-SO={info['diffs']['AD - SO']:+.3f}"
    )

print("\n3. Best-condition count across judges:")
for cond in conditions:
    print(f"   - {cond}: best for {best_counts[cond]} / {len(judge_scores)} judges")

# Generate a compact natural-language interpretation
print("\n4. Main trends and interpretation:")
top_cond, top_score = overall_ranking[0]
mid_cond, mid_score = overall_ranking[1]
bot_cond, bot_score = overall_ranking[-1]

print(
    f"   - Overall, the highest-scoring condition is {top_cond} "
    f"(mean={top_score:.3f}), followed by {mid_cond} "
    f"(mean={mid_score:.3f}), with {bot_cond} lowest "
    f"(mean={bot_score:.3f})."
)

for cond in conditions:
    if best_counts[cond] > 0:
        print(
            f"   - {cond} is the top condition for {best_counts[cond]} "
            f"out of {len(judge_scores)} judges."
        )

ad_gain = overall_condition_means["AD"] - overall_condition_means["ND"]
so_gain = overall_condition_means["SO"] - overall_condition_means["ND"]
ad_vs_so = overall_condition_means["AD"] - overall_condition_means["SO"]

print(
    f"   - Relative to ND, AD changes the average score by {ad_gain:+.3f}, "
    f"while SO changes it by {so_gain:+.3f}."
)
print(
    f"   - Comparing the two definition-based settings directly, "
    f"AD - SO = {ad_vs_so:+.3f}."
)

if ad_gain > 0:
    print("   - This suggests that providing all definitions tends to improve scoring over no-definition prompting.")
elif ad_gain < 0:
    print("   - This suggests that providing all definitions tends to reduce scoring relative to no-definition prompting.")
else:
    print("   - This suggests little to no average difference between AD and ND.")

if so_gain > 0:
    print("   - Single-definition prompting also improves over ND on average.")
elif so_gain < 0:
    print("   - Single-definition prompting underperforms ND on average.")
else:
    print("   - Single-definition prompting is roughly tied with ND on average.")