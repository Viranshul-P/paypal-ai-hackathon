"""On-device scam-language classifier (free, offline, no API).

TF-IDF over word 1-2-grams and character 2-5-grams, then logistic regression. Character n-grams
cope with Hinglish spelling variants ("abhi"/"abi"), Devanagari, and speech-recognition errors.
It trains in a few seconds on CPU from training_data.generate(), is cached to models/, and
explains each prediction with the phrases that pushed the score up.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from pauseline.risk.training_data import decontaminate, generate

ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = ROOT / "models"
TRAIN_SEED = 7
TRAIN_PER_CLASS = 1500
DECONTAMINATE_AT = 0.8
BENCHMARK = ROOT / "eval" / "scenarios" / "v1.jsonl"
# Words incl. Devanagari with its vowel signs (the default pattern splits Hindi words apart).
TOKEN_PATTERN = r"[\wऀ-ॿ]{2,}"
# Filler words never shown as an explanation (English + Hinglish + Hindi).
EXPLAIN_SKIP = set(
    "a an the to for of in on at is are was be my me i he she they it this that and or but with from by as "
    "have has had will would must should can need so not do did ka ki ke ko se pe par hai hain ho tha thi "
    "ne mein main aur bhi wale wala ye wo is us का की के को से पर है हैं ने में और".split()
)


@dataclass
class Prediction:
    proba: float  # P(scam) from the statement alone
    top_terms: list[str]  # phrases that pushed towards "scam", strongest first


def build_pipeline(c: float = 4.0) -> Pipeline:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    min_df=2,
                    sublinear_tf=True,
                    lowercase=True,
                    token_pattern=TOKEN_PATTERN,
                ),
            ),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True, lowercase=True)),
        ]
    )
    return Pipeline([("features", features), ("clf", LogisticRegression(C=c, max_iter=3000, class_weight="balanced"))])


def benchmark_texts() -> list[str]:
    if not BENCHMARK.exists():
        return []
    return [json.loads(l)["statement"] for l in BENCHMARK.read_text(encoding="utf-8").splitlines() if l.strip()]


def training_rows() -> tuple[list[dict], int]:
    """The exact training set: generated, then decontaminated against the benchmark."""
    return decontaminate(generate(TRAIN_PER_CLASS, TRAIN_SEED), benchmark_texts(), DECONTAMINATE_AT)


def _data_fingerprint(rows: list[dict]) -> str:
    blob = json.dumps([[r["text"], r["label"]] for r in rows], ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


class ScamClassifier:
    def __init__(self, pipeline: Pipeline, meta: dict):
        self.pipeline = pipeline
        self.meta = meta
        feats: FeatureUnion = pipeline.named_steps["features"]
        self._names = np.asarray(feats.get_feature_names_out())
        self._coef = pipeline.named_steps["clf"].coef_[0]
        self._is_word = np.char.startswith(self._names.astype(str), "word__")

    @classmethod
    def train(cls, rows: list[dict] | None = None, c: float = 4.0) -> "ScamClassifier":
        removed = 0
        if rows is None:
            rows, removed = training_rows()
        pipe = build_pipeline(c)
        pipe.fit([r["text"] for r in rows], [r["label"] for r in rows])
        meta = {
            "n_train": len(rows),
            "n_scam": sum(r["label"] for r in rows),
            "data_fingerprint": _data_fingerprint(rows),
            "sklearn": sklearn.__version__,
            "C": c,
            "removed_as_too_similar_to_benchmark": removed,
        }
        return cls(pipe, meta)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipeline": self.pipeline, "meta": self.meta}, path)

    @classmethod
    def load(cls, path: Path) -> "ScamClassifier":
        # joblib uses pickle. Only load files this app trained itself into models/ (git-ignored,
        # never downloaded or shared); any other file could execute code when loaded.
        blob = joblib.load(path)
        return cls(blob["pipeline"], blob["meta"])

    def predict(self, text: str, n_terms: int = 3) -> Prediction:
        text = text or ""
        proba = float(self.pipeline.predict_proba([text])[0][1])
        x = self.pipeline.named_steps["features"].transform([text])
        row = x.tocsr()
        idx, vals = row.indices, row.data
        contrib = vals * self._coef[idx]
        order = np.argsort(-contrib)
        terms: list[str] = []
        for j in order:
            if contrib[j] <= 0 or len(terms) >= n_terms:
                break
            if self._is_word[idx[j]]:
                term = str(self._names[idx[j]]).split("__", 1)[1]
                words = term.split()
                if all(w in EXPLAIN_SKIP for w in words) or (len(words) == 1 and len(term) < 4 and term.isascii()):
                    continue
                if any(term in t or t in term for t in terms):
                    continue
                terms.append(term)
        return Prediction(proba=round(proba, 4), top_terms=terms)


_lock = threading.Lock()
_cached: ScamClassifier | None = None


def get_classifier() -> ScamClassifier:
    """Load the cached model, or train and cache it (a few seconds) if missing or stale."""
    global _cached
    with _lock:
        if _cached is not None:
            return _cached
        path = MODEL_DIR / f"scam_classifier-seed{TRAIN_SEED}.joblib"
        if path.exists():
            try:
                model = ScamClassifier.load(path)
                fresh = model.meta.get("data_fingerprint") == _data_fingerprint(training_rows()[0])
                if model.meta.get("sklearn") == sklearn.__version__ and fresh:
                    _cached = model
                    return model
            except Exception:
                pass  # corrupt or incompatible: retrain
        model = ScamClassifier.train()
        model.save(path)
        _cached = model
        return model
