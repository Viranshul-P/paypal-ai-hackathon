"""Deterministic perturbations for robustness experiments.

asr_noise imitates what speech-to-text does to a spoken payment request: no punctuation or
capitals, dropped short words, and common mis-hearings. It is seeded, so a run is reproducible.
"""

from __future__ import annotations

import random
import re

# Mis-hearings typical of English speech recognition on accented / elderly speech.
HOMOPHONES = {
    "to": "two",
    "for": "four",
    "safe": "save",
    "account": "a count",
    "police": "please",
    "arrest": "a rest",
    "arrested": "a rested",
    "gift": "give",
    "cards": "cars",
    "bail": "bale",
    "customs": "custom",
    "secret": "secrets",
    "tell": "tail",
    "fee": "free",
    "warrant": "warrent",
    "officer": "office",
    "lottery": "lotto",
    "crypto": "crypt",
    "bitcoin": "bit coin",
}
_PUNCT = re.compile(r"[^\w\sऀ-ॿ']", re.UNICODE)


def asr_noise(text: str, rate: float = 0.15, seed: int = 0) -> str:
    rng = random.Random(f"{seed}:{text}")
    words = _PUNCT.sub(" ", text.lower()).split()
    out: list[str] = []
    for w in words:
        r = rng.random()
        if r < rate * 0.4 and len(w) <= 3:
            continue  # dropped short word
        if r < rate and w in HOMOPHONES:
            out.append(HOMOPHONES[w])
            continue
        out.append(w)
    return " ".join(out)
