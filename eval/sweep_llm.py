"""Calibrate the LLM's weight on the DEV split (answers come from the cache, so this is nearly free).

    uv run python eval/sweep_llm.py

LLMs over-flag large payments to new payees. This sweeps how the LLM's risk maps to a signal weight
(ignore below `floor`, scale the rest up to `max_weight`) inside the full Pauseline engine (M).
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from eval.run import build_engine, load, metrics, run_one  # noqa: E402
from pauseline.risk.engine import CONDITIONS, RiskEngine  # noqa: E402

GRID = [(0.0, 1.0), (0.3, 1.0), (0.5, 1.0), (0.6, 1.0), (0.5, 0.75), (0.6, 0.75), (0.7, 0.75)]


def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else None
    scenarios = load(ROOT / "eval" / "scenarios" / "v1.jsonl", "dev")
    assessor = build_engine("M_pauseline_full", "", model).assessor
    print(f"model: {assessor.label}")
    print("| llm floor | llm max weight | scam recall | false alarms | hard-stop recall | hard-stop false alarms | coached recall |")
    print("|---|---|---|---|---|---|---|")
    for floor, w in GRID:
        engine = RiskEngine(replace(CONDITIONS["M_pauseline_full"], llm_floor=floor, llm_max_weight=w), assessor)
        m = metrics([run_one(engine, s) for s in scenarios])
        print(
            f"| {floor} | {w} | {m['scam_recall']:.2f} | {m['false_alarm_rate']:.2f} | {m['hard_stop_recall']:.2f} | "
            f"{m['hard_stop_false_alarm']:.2f} | {m['coached_recall']:.2f} |"
        )
    print(f"\nLLM calls this sweep: {assessor.calls}, cache hits: {assessor.cache_hits}")


if __name__ == "__main__":
    main()
