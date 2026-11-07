"""Deterministic risk signals.

Two families:
- context signals: what a bank's rules already look at (new payee, unusual amount, velocity, time);
- language signals: scam-pressure phrases in what the payer says, in English, Hindi and Hinglish.

Weights are hand-set starting points; tune them on the dev split only (see EXPERIMENTS.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pauseline.models import PaymentContext, Signal

# Absolute amounts above which a first payment to a new payee is "large", per currency.
LARGE_AMOUNT = {"USD": 500.0, "INR": 25000.0, "EUR": 450.0, "GBP": 400.0}


@dataclass(frozen=True)
class Lexicon:
    name: str
    weight: float
    patterns: tuple[str, ...]
    scam_type: str = "other"


# Each pattern is a regex fragment matched case-insensitively on word boundaries.
# Keep entries specific: generic words ("bank", "family") create false alarms on normal payments.
LEXICONS: tuple[Lexicon, ...] = (
    Lexicon(
        "safe_account",
        0.45,
        (
            r"safe account",
            r"secure account",
            r"safety account",
            r"protect (?:my|your|the) (?:money|savings|funds)",
            r"account (?:is|was|has been) (?:hacked|compromised|frozen|blocked)",
            r"move (?:my|the|all)? ?(?:money|savings|funds)",
            r"सुरक्षित खात\S*",
            r"surakshit khata",
            r"paise? (?:safe|surakshit) karne",
        ),
        "bank_safe_account",
    ),
    Lexicon(
        "authority_impersonation",
        0.30,
        (
            r"police",
            r"cbi",
            r"\bed officer",
            r"enforcement directorate",
            r"customs",
            r"narcotics",
            r"income tax (?:officer|department)",
            r"\birs\b",
            r"social security (?:administration|office|number)",
            r"\btrai\b",
            r"\brbi\b",
            r"reserve bank",
            r"fraud department",
            r"bank (?:officer|manager|official) (?:called|said|told)",
            r"(?:fedex|courier|parcel) .{0,40}(?:drugs|illegal|seized)",
            r"पुलिस",
            r"अफ़?सर\S*",
        ),
        "digital_arrest_or_government",
    ),
    Lexicon(
        "legal_threat",
        0.40,
        (
            r"digital arrest",
            r"arrest(?:ed)? warrant",
            r"(?:will|would|could) (?:be )?arrest",
            r"money laundering",
            r"\bfir\b",
            r"court case",
            r"legal action",
            r"case (?:against|on) (?:me|my|him|her)",
            r"गिरफ्तार\S*",
            r"giraftar",
            r"arrest ho",
        ),
        "digital_arrest_or_government",
    ),
    Lexicon(
        "secrecy",
        0.35,
        (
            r"(?:don'?t|do not|not to|never) tell",
            r"keep (?:it|this) (?:a )?secret",
            r"keep (?:it|this) (?:between us|quiet|confidential)",
            r"(?:don'?t|do not) (?:inform|discuss)",
            r"kisi ko (?:mat|na|nahi) bata\w*",
            r"किसी को (?:मत|न) बता\S*",
            r"chup(?:ke| chap)",
        ),
    ),
    Lexicon(
        "urgency",
        0.15,
        (
            r"right now",
            r"immediately",
            r"urgent(?:ly)?",
            r"within (?:an|one|1|two|2) hours?",
            r"before (?:tonight|midnight|the end of (?:the )?day)",
            r"as soon as possible",
            r"\babhi\b",
            r"turant",
            r"jaldi",
            r"तुरंत",
            r"अभी",
        ),
    ),
    Lexicon(
        "coached",
        0.25,
        (
            r"(?:he|she|they|the (?:man|lady|officer|caller|agent)) (?:told|asked|said|instructed) me",
            r"on the (?:phone|call|line) with",
            r"(?:still|staying) on the (?:phone|call|line)",
            r"video call",
            r"(?:the|a) caller",
            r"(?:officer|caller|agent|man|lady|person|sir|madam) (?:told|asked|instructed) me",
            r"(?:told|asked|instructed) me to (?:pay|send|transfer|move|buy)",
            r"unknown number",
            r"unke kehne par",
            r"usne bola",
            r"unhone bola",
            r"call pe",
            r"फोन पर",
        ),
    ),
    Lexicon(
        "unusual_method",
        0.35,
        (
            r"gift ?cards?",
            r"google play cards?",
            r"apple cards?",
            r"itunes",
            r"steam cards?",
            r"crypto(?:currency)?",
            r"bitcoin",
            r"\busdt\b",
            r"tether",
            r"wallet address",
            r"voucher codes?",
        ),
    ),
    Lexicon(
        "remote_access",
        0.40,
        (
            r"anydesk",
            r"teamviewer",
            r"quick ?support",
            r"remote (?:access|control|desktop)",
            r"(?:install|download)(?:ed)? (?:an|the|this)? ?app (?:they|he|she) (?:sent|told)",
            r"screen ?shar",
        ),
        "tech_support",
    ),
    Lexicon(
        "prize_or_fee",
        0.35,
        (
            r"won (?:a|the)? ?(?:lottery|prize|lucky draw|car|jackpot)",
            r"lottery",
            r"lucky draw",
            r"processing fee",
            r"release fee",
            r"customs (?:fee|duty|charge)",
            r"clearance (?:fee|charge)",
            r"(?:tax|fee) to (?:claim|release|receive)",
            r"inaam",
            r"इनाम\S*",
        ),
        "prize_or_lottery",
    ),
    Lexicon(
        "investment_returns",
        0.30,
        (
            r"guaranteed (?:returns?|profit)",
            r"double (?:my|your|the) money",
            r"\d+ ?% (?:return|profit)s? (?:a|per|every) (?:day|week|month)",
            r"trading (?:platform|app|group)",
            r"investment (?:group|platform|opportunity)",
            r"withdraw(?:al)? fee",
            r"unlock (?:my|the) (?:profit|withdrawal|account)",
        ),
        "investment_or_crypto",
    ),
    Lexicon(
        "family_emergency_new_contact",
        0.30,
        (
            r"new number",
            r"lost (?:his|her|my) phone",
            r"(?:in|from) (?:jail|police custody|hospital).{0,40}(?:new|different|this) number",
            r"bail",
            r"lawyer (?:called|said|needs)",
            r"(?:grandson|granddaughter|nephew|niece|son|daughter).{0,60}(?:arrested|accident|jail|stuck)",
            r"(?:arrested|accident|jail|stuck).{0,60}(?:grandson|granddaughter|nephew|niece)",
        ),
        "family_emergency",
    ),
    Lexicon(
        "romance_abroad",
        0.30,
        (
            r"met (?:him|her) online",
            r"(?:never|haven'?t) met (?:him|her) in person",
            r"(?:oil rig|army|military|peacekeeping|ship) .{0,30}(?:abroad|overseas|stuck)",
            r"(?:flight|visa|ticket) (?:money|fee) (?:to|so) (?:come|visit|see) me",
            r"dating (?:app|site)",
        ),
        "romance",
    ),
    Lexicon(
        "refund_overpayment",
        0.35,
        (
            r"refunded (?:me )?too much",
            r"(?:sent|paid|refunded) (?:me )?(?:extra|by mistake|accidentally)",
            r"send (?:the|it) back",
            r"overpaid",
            r"return the (?:extra|difference)",
        ),
        "fake_invoice_or_refund",
    ),
    Lexicon(
        "job_task",
        0.30,
        (
            r"(?:task|tasks) (?:job|work|app)",
            r"(?:like|rate|review) (?:videos|products|hotels).{0,30}(?:earn|pay)",
            r"deposit to (?:unlock|start|continue)",
            r"work from home .{0,40}(?:deposit|fee|pay first)",
            r"registration fee",
        ),
        "job_or_task",
    ),
)

_COMPILED = [
    (lex, [re.compile(r"(?<!\w)" + p + r"(?!\w)", re.IGNORECASE) for p in lex.patterns]) for lex in LEXICONS
]


def language_signals(statement: str) -> list[Signal]:
    """Scam-pressure phrases in the payer's own words. At most one signal per lexicon."""
    found: list[Signal] = []
    text = statement or ""
    for lex, regexes in _COMPILED:
        for rx in regexes:
            m = rx.search(text)
            if m:
                found.append(Signal(name=lex.name, weight=lex.weight, evidence=m.group(0)))
                break
    return found


def lexicon_scam_type(signals: list[Signal]) -> str:
    """Most likely scam type from the strongest typed language signal."""
    typed = {lex.name: lex.scam_type for lex in LEXICONS if lex.scam_type != "other"}
    best = max((s for s in signals if s.name in typed), key=lambda s: s.weight, default=None)
    return typed[best.name] if best else "none"


def context_signals(ctx: PaymentContext) -> list[Signal]:
    """What conventional payment rules look at. No language understanding."""
    out: list[Signal] = []
    if ctx.payee.blocked:
        out.append(Signal(name="payee_blocked", weight=1.0, evidence=ctx.payee.name))
    if not ctx.payee.known:
        out.append(Signal(name="new_payee", weight=0.15, evidence=ctx.payee.name))
    large = LARGE_AMOUNT.get(ctx.currency.upper(), LARGE_AMOUNT["USD"])
    if ctx.history_median and ctx.history_median > 0:
        ratio = ctx.amount / ctx.history_median
        if ratio >= 10:
            out.append(Signal(name="amount_far_above_usual", weight=0.30, evidence=f"{ratio:.0f}x usual"))
        elif ratio >= 4:
            out.append(Signal(name="amount_above_usual", weight=0.15, evidence=f"{ratio:.1f}x usual"))
    if ctx.amount >= large and not ctx.payee.known:
        out.append(
            Signal(name="large_to_new_payee", weight=0.20, evidence=f"{ctx.amount:g} {ctx.currency}")
        )
    if ctx.recent_count_1h >= 2:
        out.append(
            Signal(name="rapid_repeat", weight=0.15, evidence=f"{ctx.recent_count_1h} payments in the last hour")
        )
    if ctx.hour_of_day is not None and (ctx.hour_of_day >= 23 or ctx.hour_of_day < 5):
        out.append(Signal(name="late_night", weight=0.05, evidence=f"{ctx.hour_of_day}:00"))
    return out


def combine(signals: list[Signal]) -> float:
    """Noisy-OR of signal weights: each signal independently 'explains' risk. Returns 0..1."""
    remaining = 1.0
    for s in signals:
        remaining *= 1.0 - max(0.0, min(1.0, s.weight))
    return round(1.0 - remaining, 4)
