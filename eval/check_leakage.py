"""How close is the classifier's training data to the benchmark? (Should be: not very.)

For every benchmark statement, find its most similar training sentence (TF-IDF character
n-gram cosine). Reports exact matches and near-duplicates so we can say in EXPERIMENTS.md
that the test set measures generalisation, not memorisation.

    uv run python eval/check_leakage.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pauseline.risk.classifier import training_rows  # noqa: E402


def main(threshold: float = 0.8) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rows, removed = training_rows()
    train = [r["text"] for r in rows]
    print(f"decontamination removed {removed} generated sentences (cosine >= 0.8 to a benchmark statement)")
    bench = [json.loads(l) for l in (ROOT / "eval" / "scenarios" / "v1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True).fit(train + [b["statement"] for b in bench])
    sims = cosine_similarity(vec.transform([b["statement"] for b in bench]), vec.transform(train))
    best = sims.max(axis=1)
    exact = {t.lower().strip() for t in train} & {b["statement"].lower().strip() for b in bench}
    near = [(b["id"], b["statement"], train[sims[i].argmax()], round(float(best[i]), 3)) for i, b in enumerate(bench) if best[i] >= threshold]
    print(f"benchmark statements: {len(bench)}   training sentences: {len(train)}")
    print(f"exact duplicates: {len(exact)}")
    print(f"max similarity: mean {best.mean():.3f}, median {sorted(best)[len(best) // 2]:.3f}, max {best.max():.3f}")
    print(f"near-duplicates (cosine >= {threshold}): {len(near)}")
    for bid, s, t, sim in near:
        print(f"  {bid} ({sim}): {s!r}\n        ~ {t!r}")


if __name__ == "__main__":
    main()
