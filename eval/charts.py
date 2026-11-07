"""Results chart for the README and slides (static PNG, light theme).

    uv run python eval/charts.py free-test llm-test --title "Test split (75 scenarios)" --out results-test

Reads eval/results/<run>/summary.json for each run, merges their conditions, and writes
docs/figures/<out>.png. Two panels, one axis each (0-100%):
  left:  scams          - stopped at all (cooling-off or hold) vs held for the family
  right: legit payments - flagged at all vs held for the family
Palette: categorical slots 1-2 of the dataviz reference palette, validated for CVD (light).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, MUTED, GRID, BASE, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

LABELS = {
    "A_rules_context": "A  Bank-style rules",
    "B_rules_lexicon": "B  Rules + scam phrases",
    "C_ml_text_only": "C  Our ML model alone",
    "D_rules_lexicon_ml": "D  Rules + phrases + ML",
    "G_rules_plus_questions": "G  Rules + phrases + questions",
    "F_pauseline": "F  Pauseline, no LLM",
    "L_llm_only": "L  LLM alone",
    "M_pauseline_full": "M  Pauseline (deployed)",
}
ORDER = list(LABELS)


def load(runs: list[str]) -> dict:
    merged: dict = {}
    for r in runs:
        merged.update(json.loads((ROOT / "eval" / "results" / r / "summary.json").read_text(encoding="utf-8"))["conditions"])
    return {k: merged[k] for k in ORDER if k in merged}


def panel(ax, names, a, b, title, a_label, b_label):
    y = range(len(names))
    h = 0.36
    ax.barh([i - h / 2 - 0.01 for i in y], a, height=h, color=BLUE, label=a_label, zorder=3)
    ax.barh([i + h / 2 + 0.01 for i in y], b, height=h, color=ORANGE, label=b_label, zorder=3)
    for i, (va, vb) in enumerate(zip(a, b)):
        ax.text(va + 1.2, i - h / 2 - 0.01, f"{va:.0f}%", va="center", fontsize=8.5, color=INK2)
        ax.text(vb + 1.2, i + h / 2 + 0.01, f"{vb:.0f}%", va="center", fontsize=8.5, color=INK2 if vb else MUTED)
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], color=MUTED, fontsize=9)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=10, color=INK)
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(axis="both", length=0)
    ax.set_title(title, loc="left", fontsize=12, color=INK, fontweight="bold", pad=30)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.04), ncol=2, frameon=False, fontsize=9, labelcolor=INK2, borderaxespad=0)
    ax.set_facecolor(SURFACE)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--title", default="")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    data = load(args.runs)
    names = [LABELS[k] for k in data]
    pct = lambda key: [100 * (data[k][key] or 0) for k in data]  # noqa: E731

    fig, (left, right) = plt.subplots(1, 2, figsize=(13, 0.62 * len(names) + 2.2), facecolor=SURFACE, sharey=True)
    panel(left, names, pct("scam_recall"), pct("hard_stop_recall"), "Scams: higher is better", "Stopped (cooling-off or hold)", "Held for the family")
    panel(right, names, pct("false_alarm_rate"), pct("hard_stop_false_alarm"), "Legitimate payments: lower is better", "Flagged (cooling-off or hold)", "Held for the family")
    right.tick_params(labelleft=False)
    left.invert_yaxis()  # shared y: invert once so A is on top and M at the bottom
    if args.title:
        fig.suptitle(args.title, x=0.01, ha="left", fontsize=14, color=INK, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95 if args.title else 1))
    out = ROOT / "docs" / "figures" / f"{args.out}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
