"""Score by difficulty tier for both models, on pooled difficulty bins.

Output: score_by_tier_pooled.png

Difficulty is the task's POOLED unaided mean A over all six no-skill runs
(three claude-opus-5 and three gpt-5.6-sol), binned at fixed cut-points:
Expert A == 0 | Hard 0 < A <= 0.35 | Medium 0.35 < A <= 0.7 |
Easy 0.7 < A < 1 | Trivial A == 1.

One no-skill curve per model (tier mean of the model's per-task means, three
runs per task) and a single with-skill curve pooled over both models, which is
drawn once because both models score 1.000 on every with-skill run. Points for
the two models sit at the same x in each tier. Faint dots are the individual
tasks' per-model no-skill means. n counts tasks in the tier.

Usage: uv run --with matplotlib==3.10.5 python3 images/score_by_tier_pooled.py
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
OUTPUT = Path(__file__).resolve().parent / "score_by_tier_pooled.png"
MODELS = {"claude-opus-5": "Claude Opus 5", "gpt-5.6-sol": "GPT-5.6 SOL"}
CONDITIONS = ("no-skill", "with-skill")
TIERS = ("Trivial", "Easy", "Medium", "Hard", "Expert")

INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"
C_WITHSKILL = "#eb6834"
C_MODEL = {"claude-opus-5": "#2a78d6", "gpt-5.6-sol": "#8a63d2"}
M_MODEL = {"claude-opus-5": "o", "gpt-5.6-sol": "D"}
# Label placement (offset points). Systematic rule, applied per tier:
#   with-skill point      -> label straight above.
#   two no-skill points   -> the higher one is labelled straight above (ABOVE_NS), unless it sits
#                            within NEAR_TOP of the with-skill line, in which case right below it
#                            (BELOW_NEAR); the lower one is labelled below (BELOW).
#   coincident no-skill   -> if they also coincide with the with-skill line, claude directly LEFT of
#                            the marker and gpt below; otherwise claude above and gpt below.
ABOVE = (0, 10)          # with-skill labels
ABOVE_NS = (7, 10)       # no-skill "above" labels: nudged right, clear of the line arriving from the upper left
BELOW_NEAR = (0, -12)    # right under the marker
BELOW = (-3, -16)        # under the marker, nudged left, clear of the line leaving to the lower right
LEFT = (-12, 0)          # directly left of the marker, vertically centred
NEAR_TOP = 10.0
COINCIDENT = 2.0

plt.rcParams.update(
    {
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "axes.edgecolor": GRID,
        "axes.linewidth": 0.8,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def tier_of(a: float) -> str:
    """Pooled-bin rule. A is the mean over all six unaided runs."""
    if a == 0:
        return "Expert"
    if a <= 0.35:
        return "Hard"
    if a <= 0.7:
        return "Medium"
    if a < 1:
        return "Easy"
    return "Trivial"


def run_number(run_dir: Path) -> int:
    return int(run_dir.name.removeprefix("run_"))


def run_score(run_dir: Path) -> float:
    """The run's recorded scalar, checked across its mirrors."""
    result_score = float(json.loads((run_dir / "result.json").read_text())["scores"]["score"])
    mirror = float((run_dir / "verifier" / "score.md").read_text().split()[0])
    if not math.isclose(result_score, mirror, abs_tol=5.1e-5):
        raise ValueError(f"score mirror mismatch in {run_dir}: {result_score} != {mirror}")
    process_path = run_dir / "verifier" / "process.json"
    if process_path.is_file():
        outcome = json.loads(process_path.read_text()).get("outcome")
        if outcome is not None:
            ratio = int(outcome["cases_passed"]) / int(outcome["cases_total"])
            if not math.isclose(ratio, mirror, abs_tol=5.1e-5):
                raise ValueError(f"outcome ratio mismatch in {run_dir}: {ratio} != {mirror}")
    return mirror


def load() -> dict[str, dict[str, dict[str, list[float]]]]:
    """task -> model -> condition -> [run_1, run_2, run_3]."""
    data: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(lambda: defaultdict(dict))
    for task in sorted(p for p in ROOT.iterdir() if (p / "task.toml").is_file()):
        for model in MODELS:
            for condition in CONDITIONS:
                arm = task / "trajectories" / model / condition
                runs = sorted((p for p in arm.glob("run_*") if p.is_dir()), key=run_number)
                if [run_number(p) for p in runs] != [1, 2, 3]:
                    raise ValueError(f"expected runs 1, 2, 3 in {arm}")
                data[task.name][model][condition] = [run_score(p) for p in runs]
    return {t: dict(m) for t, m in data.items()}


def main() -> None:
    data = load()
    bins: dict[str, list[str]] = {tier: [] for tier in TIERS}
    pooled: dict[str, float] = {}
    for task, per_model in data.items():
        a = mean(s for model in MODELS for s in per_model[model]["no-skill"])
        pooled[task] = a
        bins[tier_of(a)].append(task)

    def tier_mean(tier: str, model: str, condition: str) -> float:
        tasks = bins[tier]
        return mean(mean(data[t][model][condition]) for t in tasks) * 100 if tasks else math.nan

    x = list(range(len(TIERS)))
    fig, ax = plt.subplots(figsize=(10.5, 5.4), dpi=140)
    manifest = {
        "output": OUTPUT.name,
        "rule": tier_of.__doc__,
        "pooled_A": {t[:8]: round(v, 4) for t, v in pooled.items()},
        "tiers": {tier: [t[:8] for t in bins[tier]] for tier in TIERS},
        "series": {},
    }

    # One with-skill curve, pooled over both models (every with-skill run scores 1.000).
    with_skill = [
        mean(mean(data[t][m]["with-skill"]) for t in bins[tier] for m in MODELS) * 100 if bins[tier] else math.nan
        for tier in TIERS
    ]
    spread = max(
        abs(tier_mean(tier, "claude-opus-5", "with-skill") - tier_mean(tier, "gpt-5.6-sol", "with-skill"))
        for tier in TIERS if bins[tier]
    )
    manifest["with_skill_pooled_pct"] = [None if math.isnan(v) else round(v, 1) for v in with_skill]
    manifest["with_skill_model_spread_pp"] = round(spread, 3)
    ax.plot(x, with_skill, "--", color=C_WITHSKILL, linewidth=2, marker="s", markersize=8,
            label="With Skill (both models)", zorder=4)
    for i, v in enumerate(with_skill):
        if not math.isnan(v):
            ax.annotate(f"{v:.0f}%", (i, v), textcoords="offset points", xytext=ABOVE, ha="center", va="bottom",
                        fontsize=9, color=C_WITHSKILL, zorder=6)

    no_skill_by_model: dict[str, list[float]] = {}
    for model, label in MODELS.items():
        no_skill = [tier_mean(tier, model, "no-skill") for tier in TIERS]
        no_skill_by_model[model] = no_skill
        manifest["series"][model] = {"no_skill_pct": [None if math.isnan(v) else round(v, 1) for v in no_skill]}
        ax.plot(x, no_skill, "--", color=C_MODEL[model], linewidth=2, marker=M_MODEL[model], markersize=8,
                label=f"{label} (No Skill)", zorder=5)
        for i, tier in enumerate(TIERS):
            task_values = [mean(data[t][model]["no-skill"]) * 100 for t in bins[tier]]
            ax.scatter([i] * len(task_values), task_values, s=22, color=C_MODEL[model], alpha=0.3,
                       linewidths=0, zorder=3)

    def put(model: str, i: int, v: float, offset: tuple[int, int], ha: str) -> None:
        va = "center" if offset[1] == 0 else ("bottom" if offset[1] > 0 else "top")
        ax.annotate(f"{v:.0f}%", (i, v), textcoords="offset points", xytext=offset, ha=ha, va=va,
                    fontsize=8.5, color=C_MODEL[model], zorder=6)

    placements = []
    for i, tier in enumerate(TIERS):
        if not bins[tier]:
            continue
        c, g = no_skill_by_model["claude-opus-5"][i], no_skill_by_model["gpt-5.6-sol"][i]
        if abs(c - g) < COINCIDENT:
            if with_skill[i] - max(c, g) < NEAR_TOP:
                put("claude-opus-5", i, c, LEFT, "right")
                placements.append((tier, "claude left", "gpt below"))
            else:
                put("claude-opus-5", i, c, ABOVE_NS, "center")
                placements.append((tier, "claude above", "gpt below"))
            put("gpt-5.6-sol", i, g, BELOW, "center")
            continue
        hi_model, lo_model = ("claude-opus-5", "gpt-5.6-sol") if c > g else ("gpt-5.6-sol", "claude-opus-5")
        hi, lo = max(c, g), min(c, g)
        hi_offset = BELOW_NEAR if with_skill[i] - hi < NEAR_TOP else ABOVE_NS
        put(hi_model, i, hi, hi_offset, "center")
        put(lo_model, i, lo, BELOW, "center")
        placements.append((tier, f"{hi_model} {'right below' if hi_offset is BELOW_NEAR else 'above'}", f"{lo_model} below"))
    manifest["label_placements"] = placements

    for i, tier in enumerate(TIERS):
        if not bins[tier]:
            ax.annotate("No tasks", (i, 4), ha="center", fontsize=8, color=INK2)

    ax.set_xticks(x, [f"{tier}\n(n={len(bins[tier])})" for tier in TIERS])
    ax.set_xlim(-0.4, len(TIERS) - 0.6)
    ax.set_ylim(-15, 114)
    ax.set_yticks(range(0, 101, 20), [f"{v}%" for v in range(0, 101, 20)])
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_ylabel("Mean Score")
    ax.set_xlabel("Difficulty Tier")
    ax.set_title("Mean score by difficulty tier", fontweight="bold", pad=12)
    ax.legend(loc="lower left", frameon=True, edgecolor=GRID, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUTPUT, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
