"""Run the Pauseline benchmark across experiment conditions.

    uv run python eval/run.py --split dev                  # all on-device conditions (A-G), instant
    uv run python eval/run.py --split dev --llm            # + LLM conditions via Groq free tier (GROQ_API_KEY)
    uv run python eval/run.py --split dev --llm --provider ollama --model llama3.1:8b   # same, on your own GPU
    uv run python eval/run.py --conditions F_pauseline --perturb asr:0.3

The payer is simulated: when the engine asks questions, the scenario's ground truth decides the
answers (truthful, or all-reassuring for coached victims). Results go to eval/results/<run-id>/.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pauseline.models import Decision, PaymentContext, Payee  # noqa: E402
from pauseline.risk.engine import CONDITIONS, FREE_CONDITIONS, RiskEngine  # noqa: E402
from pauseline.risk.questions import QUESTIONS  # noqa: E402

sys.path.insert(0, str(ROOT))
from eval.perturb import asr_noise  # noqa: E402



def load(path: Path, split: str, perturb: str = "none") -> list[dict]:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if split == "all" or r["split"] == split]
    if perturb.startswith("asr"):
        rate = float(perturb.split(":")[1]) if ":" in perturb else 0.15
        rows = [{**r, "statement": asr_noise(r["statement"], rate)} for r in rows]
    return rows


def to_context(s: dict) -> PaymentContext:
    return PaymentContext(
        statement=s["statement"],
        amount=s["amount"],
        currency=s["currency"],
        payee=Payee(name=s["payee"]["name"], known=s["payee"]["known"], relationship=s["payee"].get("relationship", "")),
        history_median=s["history_median"],
        recent_count_1h=s.get("recent_count_1h", 0),
        hour_of_day=s.get("hour_of_day"),
    )


def simulated_answers(s: dict, asked: list[str]) -> dict[str, str]:
    out = {}
    for qid in asked:
        q = QUESTIONS[qid]
        safe = "no" if q.risky_answer == "yes" else "yes"
        truthful_risky = qid in s.get("true_risky_answers", [])
        out[qid] = q.risky_answer if (truthful_risky and not s.get("coached")) else safe
    return out


def run_one(engine: RiskEngine, s: dict) -> dict:
    t0 = time.perf_counter()
    ctx = to_context(s)
    first = engine.assess(ctx)
    final, answers = first, {}
    if first.questions:
        answers = simulated_answers(s, first.questions)
        final = engine.assess(ctx.model_copy(update={"answers": answers}))
    return {
        "id": s["id"],
        "label": s["label"],
        "scam_type": s["scam_type"],
        "lang": s["lang"],
        "coached": s["coached"],
        "known_payee": s["payee"]["known"],
        "initial_risk": first.risk,
        "risk": final.risk,
        "decision": final.decision.value,
        "intervened": final.decision.intervenes,
        "hard_stop": final.decision in (Decision.HOLD_FOR_FAMILY, Decision.BLOCK),
        "asked": first.questions,
        "answers": answers,
        "predicted_type": final.scam_type,
        "llm_risk": final.llm_risk,
        "ml_proba": final.ml_proba,
        "rule_risk": final.rule_risk,
        "assessor": final.assessor,
        "seconds": round(time.perf_counter() - t0, 3),
    }


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (round((c - r) / d, 3), round((c + r) / d, 3))


def metrics(rows: list[dict]) -> dict:
    scams = [r for r in rows if r["label"] == "scam"]
    benign = [r for r in rows if r["label"] == "benign"]
    tp = sum(r["intervened"] for r in scams)
    fp = sum(r["intervened"] for r in benign)
    m = {
        "n": len(rows),
        "scam_recall": round(tp / len(scams), 3) if scams else None,
        "scam_recall_ci95": wilson(tp, len(scams)),
        "hard_stop_recall": round(sum(r["hard_stop"] for r in scams) / len(scams), 3) if scams else None,
        "false_alarm_rate": round(fp / len(benign), 3) if benign else None,
        "false_alarm_ci95": wilson(fp, len(benign)),
        "hard_stop_false_alarm": round(sum(r["hard_stop"] for r in benign) / len(benign), 3) if benign else None,
        "precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "asked_rate_benign": round(sum(bool(r["asked"]) for r in benign) / len(benign), 3) if benign else None,
        "coached_recall": None,
        "recall_by_type": {},
        "recall_by_lang": {},
        "false_alarm_by_lang": {},
        "mean_seconds": round(statistics.mean(r["seconds"] for r in rows), 3) if rows else None,
    }
    coached = [r for r in scams if r["coached"]]
    if coached:
        m["coached_recall"] = round(sum(r["intervened"] for r in coached) / len(coached), 3)
    for key, bucket, field in (("recall_by_type", scams, "scam_type"), ("recall_by_lang", scams, "lang"), ("false_alarm_by_lang", benign, "lang")):
        groups: dict[str, list[dict]] = {}
        for r in bucket:
            groups.setdefault(r[field], []).append(r)
        m[key] = {g: round(sum(x["intervened"] for x in v) / len(v), 3) for g, v in sorted(groups.items())}
    return m


_ASSESSORS: dict = {}


def build_engine(name: str, provider: str, model: str | None) -> RiskEngine:
    cfg = CONDITIONS[name]
    if not cfg.llm:
        return RiskEngine(cfg)
    from dataclasses import replace as dc_replace

    from pauseline.config import get_settings
    from pauseline.risk.llm import build_assessor

    key = (provider, model)
    if key not in _ASSESSORS:  # one assessor per run: quota guard and cache shared across conditions
        s = get_settings()
        if provider:
            s = dc_replace(s, llm_provider_setting=provider)
        a = build_assessor(s, block_on_quota=True, model=model)
        if a is None:
            sys.exit("no LLM configured: set GROQ_API_KEY in .env, or use --provider ollama")
        _ASSESSORS[key] = a
    return RiskEngine(cfg, _ASSESSORS[key])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenarios", default=str(ROOT / "eval" / "scenarios" / "v1.jsonl"))
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--conditions", default="", help="comma-separated; default: offline ones, or all with --llm")
    ap.add_argument("--llm", action="store_true", help="include LLM conditions (free: Groq free tier or Ollama)")
    ap.add_argument("--provider", default="", help="groq | ollama (default: from .env)")
    ap.add_argument("--model", default=None, help="override the LLM model id")
    ap.add_argument("--repeats", type=int, default=1, help="repeat LLM conditions to measure run-to-run variance")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--perturb", default="none", help="none | asr | asr:0.25 (speech-recognition noise)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    names = [c for c in args.conditions.split(",") if c] or (list(CONDITIONS) if args.llm else FREE_CONDITIONS)
    unknown = [c for c in names if c not in CONDITIONS]
    if unknown:
        sys.exit(f"unknown conditions: {unknown}; choose from {list(CONDITIONS)}")
    if not args.llm and any(CONDITIONS[c].llm for c in names):
        sys.exit("these conditions use an LLM; add --llm")

    scenarios = load(Path(args.scenarios), args.split, args.perturb)
    run_id = args.out or datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{args.split}"
    out_dir = ROOT / "eval" / "results" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: dict = {
        "run_id": run_id,
        "scenarios": Path(args.scenarios).name,
        "split": args.split,
        "perturb": args.perturb,
        "n_scenarios": len(scenarios),
        "model": None,
        "conditions": {},
    }
    for name in names:
        cfg = CONDITIONS[name]
        repeats = args.repeats if cfg.llm else 1
        per_repeat = []
        for rep in range(repeats):
            engine = build_engine(name, args.provider, args.model)
            if engine.assessor is not None:
                summary["model"] = engine.assessor.label
            started = time.time()
            if cfg.llm and args.workers > 1 and args.provider == "ollama":
                with ThreadPoolExecutor(args.workers) as pool:
                    rows = list(pool.map(lambda s: run_one(engine, s), scenarios))
            else:
                rows = [run_one(engine, s) for s in scenarios]
            with (out_dir / f"{name}.r{rep}.jsonl").open("w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            m = metrics(rows)
            m["llm_calls"] = engine.llm_calls
            m["llm_errors"] = len(engine.llm_errors)
            if engine.assessor is not None:
                m["llm_cache_hits_total"] = engine.assessor.cache_hits
            m["wall_seconds"] = round(time.time() - started, 1)
            per_repeat.append(m)
            print(f"{name:26s} rep{rep}  recall {m['scam_recall']:.2f}  false-alarm {m['false_alarm_rate']:.2f}  "
                  f"coached {m['coached_recall']}  llm_calls {engine.llm_calls}  errors {len(engine.llm_errors)}")
        agg = dict(per_repeat[0])
        if repeats > 1:
            for k in ("scam_recall", "false_alarm_rate", "hard_stop_recall", "coached_recall"):
                vals = [r[k] for r in per_repeat if r[k] is not None]
                agg[k + "_mean"] = round(statistics.mean(vals), 3)
                agg[k + "_sd"] = round(statistics.pstdev(vals), 3)
        agg["repeats"] = per_repeat
        summary["conditions"][name] = agg

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(summary, out_dir / "summary.md")
    print(f"\nResults: {out_dir}")


def write_markdown(summary: dict, path: Path) -> None:
    lines = [
        f"# Pauseline benchmark run `{summary['run_id']}`",
        "",
        f"Scenarios: `{summary['scenarios']}` · split: **{summary['split']}** ({summary['n_scenarios']}) · perturbation: {summary.get('perturb', 'none')} · "
        f"local LLM: {summary['model'] or 'not used'}",
        "",
        "| Condition | Scam recall (95% CI) | False alarms (95% CI) | Hard-stop recall | Hard-stop false alarms | Coached-victim recall | Benign asked questions |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, m in summary["conditions"].items():
        rc, fc = m["scam_recall_ci95"], m["false_alarm_ci95"]
        lines.append(
            f"| {name} | {m['scam_recall']:.2f} ({rc[0]:.2f}-{rc[1]:.2f}) | {m['false_alarm_rate']:.2f} ({fc[0]:.2f}-{fc[1]:.2f}) | "
            f"{m['hard_stop_recall']:.2f} | {m['hard_stop_false_alarm']:.2f} | {m['coached_recall']} | {m['asked_rate_benign']} |"
        )
    lines += ["", "## Recall by scam type", "", "| Condition | " + " | ".join(next(iter(summary["conditions"].values()))["recall_by_type"]) + " |"]
    types = list(next(iter(summary["conditions"].values()))["recall_by_type"])
    lines.append("|---" * (len(types) + 1) + "|")
    for name, m in summary["conditions"].items():
        lines.append(f"| {name} | " + " | ".join(f"{m['recall_by_type'].get(t, 0):.2f}" for t in types) + " |")
    lines += ["", "## By language", "", "| Condition | Recall en / hi / hinglish | False alarms en / hi / hinglish |", "|---|---|---|"]
    for name, m in summary["conditions"].items():
        r, f = m["recall_by_lang"], m["false_alarm_by_lang"]
        lines.append(
            f"| {name} | {r.get('en', 0):.2f} / {r.get('hi', 0):.2f} / {r.get('hinglish', 0):.2f} | "
            f"{f.get('en', 0):.2f} / {f.get('hi', 0):.2f} / {f.get('hinglish', 0):.2f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
