import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
df = pd.read_csv("grades_matrix_v2.csv")   # change filename if needed

# Column groups
nd_cols = ["nd_grade_gpt", "nd_grade_gemini", "nd_grade_llama"]
ad_cols = ["ad_grade_gpt", "ad_grade_gemini", "ad_grade_llama"]
so_cols = ["so_grade_gpt", "so_grade_gemini", "so_grade_llama"]

# Compute means
nd_means = df[nd_cols].mean().values
ad_means = df[ad_cols].mean().values
so_means = df[so_cols].mean().values

all_means = list(nd_means) + list(ad_means) + list(so_means)

# Short labels for display
labels = [
    "GPT", "Gemini", "Llama",
    "GPT", "Gemini", "Llama",
    "GPT", "Gemini", "Llama"
]

# Custom x positions:
# bars within a group are close together
# groups have a slightly bigger gap between them
x = [0.00, 0.22, 0.44,   0.90, 1.12, 1.34,   1.80, 2.02, 2.24]

# Colors by group
colors = (
    ["#4C78A8"] * 3 +   # nd = blue
    ["#F58518"] * 3 +   # ad = orange
    ["#54A24B"] * 3     # so = green
)

# Plot
plt.figure(figsize=(10, 5))
bars = plt.bar(x, all_means, width=0.14, color=colors)

# X tick labels
plt.xticks(x, labels)

# Group labels under bars
group_centers = [0.22, 1.12, 2.02]
group_names = ["ND Grade", "AD Grade", "SO Grade"]

for xc, name in zip(group_centers, group_names):
    plt.text(xc, -0.18, name, ha="center", va="top",
             transform=plt.gca().get_xaxis_transform(),
             fontsize=11, fontweight="bold")

# Titles and axes
plt.title("Average Scores by Model and Grade Type")
plt.ylabel("Average Score")
plt.ylim(0, 5)

# Optional: add value labels above bars
for bar in bars:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height + 0.03,
        f"{height:.2f}",
        ha="center",
        va="bottom",
        fontsize=9
    )

plt.tight_layout()
plt.show()