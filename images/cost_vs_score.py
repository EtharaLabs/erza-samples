"""Plot recorded agent cost against outcome score, separately for each model.

Each point is one run. Correlations and linear fits are computed within each
model and condition. A constant cost or score makes correlation undefined.

Usage: uv run --python 3.12 --with matplotlib==3.10.5 python images/cost_vs_score.py
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import correlation, linear_regression, mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MultipleLocator, PercentFormatter

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = Path(__file__).with_suffix(".png")
MODELS = {"claude-opus-5": "Claude Opus 5", "gpt-5.6-sol": "GPT-5.6 SOL"}
ARMS = ("no-skill", "with-skill")
COLORS = {"no-skill": "#2a78d6", "with-skill": "#eb6834"}
MARKERS = {"no-skill": "o", "with-skill": "s"}
LABELS = {"no-skill": "No Skill", "with-skill": "With Skill"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"


def load_runs():
    records = []
    for task in sorted(p for p in ROOT.iterdir() if (p / "task.toml").is_file()):
        for model in MODELS:
            for arm in ARMS:
                runs = sorted(p for p in (task / "trajectories" / model / arm).glob("run_*") if p.is_dir())
                if [p.name for p in runs] != ["run_1", "run_2", "run_3"]:
                    raise ValueError(f"expected runs 1, 2, 3 in {task.name}/{model}/{arm}")
                for run in runs:
                    result = json.loads((run / "result.json").read_text())
                    cost = (result.get("agent_result") or {}).get("cost_usd")
                    score = result["scores"]["score"]
                    for name, value in (("cost_usd", cost), ("score", score)):
                        if type(value) not in (int, float) or not math.isfinite(value):
                            raise ValueError(f"invalid {name} in {run}")
                    if cost < 0 or not 0 <= score <= 1:
                        raise ValueError(f"cost or score outside its range in {run}")
                    mirror = float((run / "verifier" / "score.md").read_text().strip())
                    if not math.isclose(score, mirror, rel_tol=0, abs_tol=5.1e-5):
                        raise ValueError(f"score mirror mismatch in {run}")
                    records.append({"task": task.name, "model": model, "arm": arm,
                                    "run": run.name, "cost_usd": float(cost), "score": float(score)})
    if not records:
        raise ValueError("no recorded runs found")
    return records


def summarize(records):
    cells = defaultdict(list)
    for record in records:
        cells[record["model"], record["arm"]].append(record)
    summary = {}
    for model in MODELS:
        summary[model] = {}
        for arm in ARMS:
            rows = cells[model, arm]
            costs, scores = [r["cost_usd"] for r in rows], [r["score"] for r in rows]
            variable = len(set(costs)) > 1 and len(set(scores)) > 1
            summary[model][arm] = {
                "n": len(rows), "mean_cost_usd": mean(costs), "mean_score": mean(scores),
                "pearson_r": correlation(costs, scores) if variable else None,
                "correlation_note": None if variable else "undefined: cost or score is constant",
            }
    return cells, summary


def main():
    records = load_runs()
    cells, summary = summarize(records)
    plt.rcParams.update({
        "font.size": 10, "text.color": INK, "axes.labelcolor": INK,
        "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": GRID,
        "axes.linewidth": 0.8, "figure.facecolor": "white", "axes.facecolor": "white",
    })
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 6.6), dpi=180, sharex=True, sharey=True)
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.21, top=0.74, wspace=0.08)
    top_cost = max(r["cost_usd"] for r in records)
    for ax, (model, title) in zip(axes, MODELS.items()):
        correlation_labels = []
        for arm in ARMS:
            rows = cells[model, arm]
            costs, scores = [r["cost_usd"] for r in rows], [r["score"] for r in rows]
            ax.scatter(costs, scores, s=44, marker=MARKERS[arm], color=COLORS[arm],
                       alpha=0.65, edgecolors="white", linewidths=0.5, zorder=3)
            r = summary[model][arm]["pearson_r"]
            if r is not None:
                slope, intercept = linear_regression(costs, scores)
                ends = [min(costs), max(costs)]
                ax.plot(ends, [slope * x + intercept for x in ends], color=COLORS[arm],
                        linestyle="--", linewidth=1.3, alpha=0.8, zorder=2)
                correlation_labels.append(f"{LABELS[arm]}: Pearson r = {r:+.2f}")
            else:
                correlation_labels.append(f"{LABELS[arm]}: r undefined")
        ax.set_title(title, fontweight="bold", fontsize=12, pad=30)
        ax.text(0.5, 1.025, "  |  ".join(correlation_labels), transform=ax.transAxes,
                ha="center", va="bottom", fontsize=9, color=MUTED)
        ax.set_xlim(-0.08, top_cost * 1.06)
        ax.set_ylim(-0.06, 1.09)
        ax.xaxis.set_major_locator(MultipleLocator(0.5))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"${value:.1f}"))
        ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1])
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_xlabel("Agent cost per run (USD)", labelpad=10)
        ax.grid(color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Outcome score", labelpad=10)
    fig.suptitle("Agent cost and outcome score", fontsize=16, fontweight="bold", y=0.975)
    n_tasks = len({r["task"] for r in records})
    fig.text(0.5, 0.915, f"{len(records)} recorded runs across {n_tasks} tasks · Each point is one run",
             ha="center", color=MUTED, fontsize=11)
    handles = [Line2D([], [], color=COLORS[arm], marker=MARKERS[arm], linestyle="none",
                      markersize=7, label=LABELS[arm]) for arm in ARMS]
    handles.append(Line2D([], [], color=MUTED, linestyle="--", linewidth=1.3, label="Linear fit"))
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.885),
               ncol=3, frameon=False)
    constant_scores = all(len({r["score"] for r in cells[model, "with-skill"]}) == 1 for model in MODELS)
    if constant_scores:
        note = "With Skill has no score variation, so its cost–score correlation is undefined."
    else:
        note = "Correlations and dashed linear fits are computed separately within each condition."
    fig.text(0.07, 0.095, note, fontsize=9, color=MUTED)
    fig.text(0.07, 0.06,
             "Descriptive association across tasks and repeated runs; it does not establish a causal effect of spending.",
             fontsize=9, color=MUTED)
    fig.savefig(OUTPUT, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"output": OUTPUT.name, "tasks": n_tasks, "runs": len(records),
                      "cost_field": "agent_result.cost_usd", "score_field": "scores.score",
                      "series": summary}, indent=2))


if __name__ == "__main__":
    main()
