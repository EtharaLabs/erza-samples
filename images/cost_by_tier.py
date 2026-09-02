"""Mean agent cost per run by difficulty tier, one panel per model, both arms.

Output: cost_by_tier.png

Difficulty is the task's pooled unaided mean A over all six no-skill runs (three per
model), binned at the same cut-points as score_by_tier_pooled.py:
Expert A == 0 | Hard 0 < A <= 0.35 | Medium 0.35 < A <= 0.7 | Easy 0.7 < A < 1 | Trivial A == 1.
The tier a task belongs to is therefore the same in both panels.

Cost is agent_result.cost_usd from each run's result.json (harness-priced from the
recorded token usage). Each bar is the mean over that model's runs of that arm on the
tasks in the tier (3 runs per task per arm). n counts tasks.

Usage: uv run --with matplotlib==3.10.5 python3 images/cost_by_tier.py
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = Path(__file__).resolve().parent / "cost_by_tier.png"
MODELS = {"claude-opus-5": "Claude Opus 5", "gpt-5.6-sol": "GPT-5.6 SOL"}
ARMS = ("no-skill", "with-skill")
TIERS = ("Trivial", "Easy", "Medium", "Hard", "Expert")
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
C_ARM = {"no-skill": "#2a78d6", "with-skill": "#eb6834"}
LABEL = {"no-skill": "No Skill", "with-skill": "With Skill"}

plt.rcParams.update({"font.size": 10, "text.color": INK, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.edgecolor": GRID, "axes.linewidth": 0.8,
                     "figure.facecolor": "white", "axes.facecolor": "white"})


def tier_of(a: float) -> str:
    if a == 0:
        return "Expert"
    if a <= 0.35:
        return "Hard"
    if a <= 0.7:
        return "Medium"
    if a < 1:
        return "Easy"
    return "Trivial"


def main() -> None:
    scores: dict[str, list[float]] = defaultdict(list)                     # task -> six no-skill scores
    costs: dict[tuple[str, str, str], list[float]] = defaultdict(list)     # (task, model, arm) -> run costs
    for task in sorted(p for p in ROOT.iterdir() if (p / "task.toml").is_file()):
        for model in MODELS:
            for arm in ARMS:
                runs = sorted((task / "trajectories" / model / arm).glob("run_*"))
                if len(runs) != 3:
                    raise ValueError(f"expected 3 runs in {task.name}/{model}/{arm}")
                for run in runs:
                    r = json.loads((run / "result.json").read_text())
                    cost = (r.get("agent_result") or {}).get("cost_usd")
                    if not isinstance(cost, (int, float)):
                        raise ValueError(f"no cost_usd in {run}")
                    costs[(task.name, model, arm)].append(float(cost))
                    if arm == "no-skill":
                        scores[task.name].append(float(r["scores"]["score"]))
    bins = {t: [] for t in TIERS}
    for task, six in scores.items():
        bins[tier_of(mean(six))].append(task)
    series = {model: {arm: [mean(c for t in bins[tier] for c in costs[(t, model, arm)]) if bins[tier] else math.nan
                            for tier in TIERS] for arm in ARMS} for model in MODELS}
    top = max(v for m in series.values() for s in m.values() for v in s if not math.isnan(v))

    x = list(range(len(TIERS)))
    width = 0.36
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), dpi=140, sharey=True)
    for ax, (model, title) in zip(axes, MODELS.items()):
        for k, arm in enumerate(ARMS):
            pos = [i + (k - 0.5) * width for i in x]
            bars = ax.bar(pos, series[model][arm], width=width, color=C_ARM[arm], label=LABEL[arm], zorder=3)
            for bar, v in zip(bars, series[model][arm]):
                if not math.isnan(v):
                    ax.annotate(f"${v:.2f}", (bar.get_x() + bar.get_width() / 2, v), textcoords="offset points",
                                xytext=(0, 4), ha="center", va="bottom", fontsize=8.5, color=INK)
        ax.set_xticks(x, [f"{t}\n(n={len(bins[t])})" for t in TIERS])
        ax.set_ylim(0, top * 1.22)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_xlabel("Difficulty Tier")
        ax.set_title(title, fontweight="bold", pad=9)
    axes[0].set_ylabel("Mean agent cost per run (USD)")
    axes[0].legend(loc="upper left", frameon=True, edgecolor=GRID)
    fig.suptitle("Mean agent cost per run by difficulty tier", fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout()
    fig.savefig(OUTPUT, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"output": OUTPUT.name, "tiers": {t: [b[:8] for b in bins[t]] for t in TIERS},
                      "cost_usd": {m: {arm: [None if math.isnan(v) else round(v, 3) for v in series[m][arm]] for arm in ARMS}
                                   for m in MODELS}}, indent=1))


if __name__ == "__main__":
    main()
