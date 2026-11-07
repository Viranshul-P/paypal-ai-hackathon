"""Operating-point sweep on the DEV split: how the context cap trades recall against false alarms.

    uv run python eval/sweep.py                 # prints a table; pick the operating point here, never on test

Each row is the full Pauseline engine (F) with a different cap on context-only risk.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from eval.run import load, metrics, run_one  # noqa: E402
from pauseline.risk.engine import CONDITIONS, RiskEngine  # noqa: E402

CAPS = [0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.69, None]


def main() -> None:
    scenarios = load(ROOT / "eval" / "scenarios" / "v1.jsonl", "dev")
    base = CONDITIONS["F_pauseline"]
    print("| ask policy | context cap | scam recall | false alarms | hard-stop recall | hard-stop false alarms | coached recall | benign asked |")
    print("|---|---|---|---|---|---|---|---|")
    for policy in ("any", "evidence"):
        for cap in CAPS:
            engine = RiskEngine(replace(base, context_cap=cap, ask_policy=policy))
            m = metrics([run_one(engine, s) for s in scenarios])
            print(
                f"| {policy} | {cap if cap is not None else 'none'} | {m['scam_recall']:.2f} | {m['false_alarm_rate']:.2f} | "
                f"{m['hard_stop_recall']:.2f} | {m['hard_stop_false_alarm']:.2f} | {m['coached_recall']:.2f} | {m['asked_rate_benign']:.2f} |"
            )


if __name__ == "__main__":
    main()
