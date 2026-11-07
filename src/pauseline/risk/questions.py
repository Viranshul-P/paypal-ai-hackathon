"""Clarifying questions Pauseline may ask the payer before money leaves.

All questions are yes/no so they can be answered with two big buttons or by voice.
Each has the answer that raises risk and how much. Scammers often coach victims to
give the "safe" answer, so a reassuring answer lowers risk only a little.
"""

from __future__ import annotations

from dataclasses import dataclass

from pauseline.models import Signal


@dataclass(frozen=True)
class Question:
    id: str
    en: str
    hi: str
    risky_answer: str  # "yes" or "no"
    weight: float  # signal weight when the risky answer is given
    reassure: float  # how much a reassuring answer reduces risk (multiplier on remaining risk)


QUESTIONS: dict[str, Question] = {
    q.id: q
    for q in (
        Question(
            "on_call_now",
            "Is someone on the phone or a video call with you right now, telling you what to do?",
            "क्या अभी कोई फ़ोन या वीडियो कॉल पर आपको बता रहा है कि क्या करना है?",
            "yes",
            0.55,
            0.95,
        ),
        Question(
            "someone_asked",
            "Did someone you have not met in person ask you to make this payment?",
            "क्या किसी ऐसे व्यक्ति ने यह पेमेंट करने को कहा जिनसे आप कभी मिले नहीं?",
            "yes",
            0.35,
            0.9,
        ),
        Question(
            "secrecy",
            "Were you told to keep this payment secret, or not to tell your family or bank?",
            "क्या आपसे कहा गया कि यह पेमेंट किसी को, परिवार या बैंक को, न बताएं?",
            "yes",
            0.5,
            0.95,
        ),
        Question(
            "threatened",
            "Did anyone say you could be arrested, fined, or lose your money if you don't pay?",
            "क्या किसी ने कहा कि पैसे न देने पर गिरफ्तारी, जुर्माना या नुकसान होगा?",
            "yes",
            0.55,
            0.95,
        ),
        Question(
            "verified_independently",
            "Did you check this yourself, using a phone number or website you already had (not one they gave you)?",
            "क्या आपने खुद, अपने पास पहले से मौजूद नंबर या वेबसाइट से, इसकी जांच की है?",
            "no",
            0.2,
            0.8,
        ),
        Question(
            "promised_money",
            "Were you promised a prize, a refund, or high returns if you pay first?",
            "क्या आपसे इनाम, रिफ़ंड या ज़्यादा मुनाफ़े का वादा किया गया है?",
            "yes",
            0.45,
            0.95,
        ),
        Question(
            "special_method",
            "Were you asked to pay in an unusual way, like gift cards, crypto, or a 'safe account'?",
            "क्या आपसे गिफ्ट कार्ड, क्रिप्टो या 'सुरक्षित खाते' जैसे अलग तरीके से पैसे भेजने को कहा गया?",
            "yes",
            0.5,
            0.95,
        ),
        Question(
            "met_in_person",
            "Have you met this person in real life?",
            "क्या आप इस व्यक्ति से असल ज़िंदगी में मिले हैं?",
            "no",
            0.3,
            0.85,
        ),
    )
}

# Which questions are most informative given which signals fired. Order = priority.
_BY_SIGNAL: dict[str, tuple[str, ...]] = {
    "coached": ("on_call_now", "secrecy"),
    "authority_impersonation": ("threatened", "on_call_now"),
    "legal_threat": ("threatened", "on_call_now"),
    "safe_account": ("special_method", "on_call_now"),
    "secrecy": ("secrecy", "someone_asked"),
    "unusual_method": ("special_method", "someone_asked"),
    "remote_access": ("on_call_now", "verified_independently"),
    "prize_or_fee": ("promised_money", "verified_independently"),
    "investment_returns": ("promised_money", "met_in_person"),
    "family_emergency_new_contact": ("verified_independently", "secrecy"),
    "romance_abroad": ("met_in_person", "someone_asked"),
    "refund_overpayment": ("verified_independently", "on_call_now"),
    "job_task": ("promised_money", "someone_asked"),
    "large_to_new_payee": ("someone_asked", "verified_independently"),
    "amount_far_above_usual": ("someone_asked", "on_call_now"),
    "new_payee": ("someone_asked", "met_in_person"),
}


def pick_questions(signals: list[Signal], suggested: list[str] | None = None, limit: int = 2) -> list[str]:
    """Choose up to `limit` questions: model suggestions first (if valid), then by strongest signal."""
    chosen: list[str] = []
    for qid in suggested or []:
        if qid in QUESTIONS and qid not in chosen:
            chosen.append(qid)
    for s in sorted(signals, key=lambda s: s.weight, reverse=True):
        for qid in _BY_SIGNAL.get(s.name, ()):
            if qid not in chosen:
                chosen.append(qid)
    return chosen[:limit]


def answer_effect(answers: dict[str, str]) -> tuple[list[Signal], float]:
    """Turn answers into (risk signals, reassurance multiplier on remaining risk)."""
    signals: list[Signal] = []
    reassure = 1.0
    for qid, raw in answers.items():
        q = QUESTIONS.get(qid)
        if q is None:
            continue
        ans = str(raw).strip().lower()
        if ans not in {"yes", "no"}:
            continue
        if ans == q.risky_answer:
            signals.append(Signal(name=f"answer:{qid}", weight=q.weight, evidence=f"{q.en} -> {ans}"))
        else:
            reassure *= q.reassure
    return signals, reassure
