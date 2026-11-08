"""The Pauseline risk engine: signals -> risk -> decision. Free and on-device.

Components, each producing risk signals:
- context rules (new payee, unusual amount, velocity, time)
- scam-phrase lexicon (English, Hindi, Hinglish)
- ML classifier on the payer's words (TF-IDF + logistic regression, trained locally)
- answers to clarifying questions
- an open-weight LLM (gpt-oss / Qwen on Groq's free tier, or Ollama locally), when configured

Risk = noisy-OR of all signal weights, times a small reassurance factor from honest answers.
Design rules:
1. Every signal can only ADD risk; the payer's reassuring answers lower it a little. One exception
   by design: when the LLM is working, risk from context alone is capped lower (CONTEXT_CAP_WITH_LLM),
   so a healthy LLM can let an unusual but clean payment through. No AI component can move money.
2. A blocked payee is always blocked (deterministic).
3. Questions are asked once, only when there is some doubt.
4. Every experiment condition in eval/ is an EngineConfig, so product and research share code.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from pauseline.models import Assessment, Decision, PaymentContext, Signal
from pauseline.risk import questions as qbank
from pauseline.risk.signals import combine, context_signals, language_signals, lexicon_scam_type

COOL_OFF_AT = 0.40
HOLD_AT = 0.70
ASK_AT = 0.20  # ask clarifying questions when initial risk is at least this
ML_FLOOR = 0.50  # classifier probabilities below this add nothing
ML_MAX_WEIGHT = 0.75  # weight of a classifier probability of 1.0
# LLM risk -> signal weight. Calibrated on dev with eval/sweep_llm.py: the raw score works best,
# because clarifying questions (re-assessed by the LLM) correct its over-suspicion.
LLM_FLOOR = 0.0
LLM_MAX_WEIGHT = 1.0
# Cap on risk from unusual context alone (new payee, big amount, no warning signs in the words).
# Chosen on the dev split per engine (eval/sweep.py, EXPERIMENTS.md):
# - without the LLM (and as the fallback when it is unavailable): 0.69, so context alone can at most
#   trigger a cooling-off, never a family hold; this keeps coached victims, whose words are bland;
# - with the LLM: 0.35, so context alone only triggers questions. The LLM already catches coached
#   victims, and a looser cap only adds false cooling-offs (dev: false alarms 0.17 -> 0.06, no loss).
CONTEXT_CAP = 0.69
CONTEXT_CAP_WITH_LLM = 0.35


@dataclass(frozen=True)
class EngineConfig:
    name: str
    context_rules: bool = True
    lexicon: bool = False
    ml: bool = False
    llm: bool = False  # open-weight LLM (Groq free tier or Ollama)
    llm_context: bool = True
    questions: bool = False
    fast_path: bool = False  # skip the LLM for clearly routine payments
    context_cap: float | None = CONTEXT_CAP  # None = classic bank rules, context alone can hold money
    # When to ask questions. "any": whenever risk >= ASK_AT. "evidence": only when the payment would be
    # stopped anyway (risk >= COOL_OFF_AT), or the words themselves raised a warning. Chosen on dev.
    ask_policy: str = "evidence"
    llm_floor: float | None = None  # None = module default (LLM_FLOOR)
    llm_max_weight: float | None = None


CONDITIONS: dict[str, EngineConfig] = {
    c.name: c
    for c in (
        EngineConfig("A_rules_context", context_cap=None),
        EngineConfig("B_rules_lexicon", lexicon=True),
        EngineConfig("C_ml_text_only", context_rules=False, ml=True),
        EngineConfig("D_rules_lexicon_ml", lexicon=True, ml=True),
        EngineConfig("F_pauseline", lexicon=True, ml=True, questions=True),
        EngineConfig("G_rules_plus_questions", lexicon=True, questions=True),
        # need an LLM (Groq free tier or Ollama):
        EngineConfig("L_llm_only", context_rules=False, llm=True),
        EngineConfig(
            "M_pauseline_full", lexicon=True, ml=True, llm=True, questions=True, fast_path=True, context_cap=CONTEXT_CAP_WITH_LLM
        ),
    )
}
FREE_CONDITIONS = [n for n, c in CONDITIONS.items() if not c.llm]
PRODUCT_CONFIG = CONDITIONS["F_pauseline"]
PRODUCT_CONFIG_WITH_LLM = CONDITIONS["M_pauseline_full"]


def decide(risk: float, ctx: PaymentContext) -> Decision:
    if ctx.payee.blocked:
        return Decision.BLOCK
    if risk >= HOLD_AT:
        return Decision.HOLD_FOR_FAMILY
    if risk >= COOL_OFF_AT:
        return Decision.COOL_OFF
    return Decision.ALLOW


def llm_weight(risk: float, floor: float | None = None, max_weight: float | None = None) -> float:
    f = LLM_FLOOR if floor is None else floor
    w = LLM_MAX_WEIGHT if max_weight is None else max_weight
    if risk <= f:
        return 0.0
    return round(w * (risk - f) / (1 - f), 4)


def ml_weight(proba: float) -> float:
    if proba < ML_FLOOR:
        return 0.0
    return round(ML_MAX_WEIGHT * (proba - ML_FLOOR) / (1 - ML_FLOOR), 4)


_FALLBACK_MESSAGES = {
    "en": {
        "default": "We've paused this payment for a moment to keep your money safe. Your trusted contact can help you check it.",
        "safe_account": "Real banks never ask you to move money to a 'safe account'. We've paused this payment so you can check with someone you trust.",
        "legal_threat": "Police and government officers never ask for money over the phone or on a video call. We've paused this payment.",
        "unusual_method": "Requests to pay with gift cards or crypto are a common sign of a scam. We've paused this payment.",
        "secrecy": "Being asked to keep a payment secret is a warning sign. We've paused this payment so you can talk to someone you trust.",
        "answer:on_call_now": "Please hang up the call first. Real banks, police and companies never stay on the phone while you send money.",
        "prize_or_fee": "You never have to pay to receive a real prize or refund. We've paused this payment.",
    },
    "hi": {
        "default": "आपके पैसे सुरक्षित रखने के लिए हमने यह पेमेंट थोड़ी देर के लिए रोका है। आपके भरोसेमंद व्यक्ति इसे जांचने में मदद करेंगे।",
        "safe_account": "असली बैंक कभी भी 'सुरक्षित खाते' में पैसे भेजने को नहीं कहते। हमने यह पेमेंट रोका है।",
        "legal_threat": "पुलिस या सरकारी अधिकारी कभी फ़ोन या वीडियो कॉल पर पैसे नहीं मांगते। हमने यह पेमेंट रोका है।",
        "unusual_method": "गिफ्ट कार्ड या क्रिप्टो से पैसे मांगना धोखाधड़ी का आम संकेत है। हमने यह पेमेंट रोका है।",
        "secrecy": "पेमेंट को गुप्त रखने को कहना खतरे का संकेत है। हमने यह पेमेंट रोका है।",
        "answer:on_call_now": "कृपया पहले फ़ोन काट दें। असली बैंक या पुलिस पैसे भेजते समय कभी फ़ोन पर नहीं रहते।",
        "prize_or_fee": "असली इनाम या रिफ़ंड पाने के लिए कभी पैसे नहीं देने पड़ते। हमने यह पेमेंट रोका है।",
    },
}

SIGNAL_LABELS = {
    "payee_blocked": "payee is on the block list",
    "new_payee": "new payee",
    "amount_far_above_usual": "amount far above usual",
    "amount_above_usual": "amount above usual",
    "large_to_new_payee": "large amount to a new payee",
    "rapid_repeat": "several payments in the last hour",
    "late_night": "late at night",
    "safe_account": "'safe account' / moving savings",
    "authority_impersonation": "mentions police, bank or officials",
    "legal_threat": "threat of arrest or legal action",
    "secrecy": "asked to keep it secret",
    "urgency": "pressure to pay now",
    "coached": "someone is directing the payment",
    "unusual_method": "gift cards or crypto",
    "remote_access": "remote-access app",
    "prize_or_fee": "fee to claim a prize",
    "investment_returns": "promised returns",
    "family_emergency_new_contact": "relative in trouble, new number",
    "romance_abroad": "online contact never met",
    "refund_overpayment": "'refund mistake' to send back",
    "job_task": "deposit for a task job",
    "ml_scam_language": "wording resembles scam scripts (AI model)",
    "llm": "AI language model judged it risky",
    "ai_flag": "AI note",
    "answer:on_call_now": "said someone is on the phone directing them",
    "answer:someone_asked": "said a stranger asked for the payment",
    "answer:secrecy": "said they were told to keep it secret",
    "answer:threatened": "said they were threatened",
    "answer:verified_independently": "has not checked it independently",
    "answer:promised_money": "was promised money back or a prize",
    "answer:special_method": "was asked to pay in an unusual way",
    "answer:met_in_person": "has never met the person",
}


def _looks_hindi(text: str) -> bool:
    return any("ऀ" <= ch <= "ॿ" for ch in text)


def fallback_message(signals: list[Signal], statement: str) -> str:
    lang = "hi" if _looks_hindi(statement) else "en"
    names = {s.name for s in signals}
    for key in ("answer:on_call_now", "safe_account", "legal_threat", "unusual_method", "prize_or_fee", "secrecy"):
        if key in names:
            return _FALLBACK_MESSAGES[lang][key]
    return _FALLBACK_MESSAGES[lang]["default"]


def fallback_summary(ctx: PaymentContext, signals: list[Signal]) -> str:
    ranked = [s for s in sorted(signals, key=lambda s: -s.weight) if s.weight > 0][:4]
    flags = "; ".join(SIGNAL_LABELS.get(s.name, s.name.replace("_", " ")) for s in ranked)
    return (
        f"A payment of {ctx.amount:g} {ctx.currency} to {ctx.payee.name} was paused. "
        f"Warning signs: {flags or 'unusual payment'}. Their words: \"{ctx.statement[:200]}\""
    )


class RiskEngine:
    def __init__(self, config: EngineConfig = PRODUCT_CONFIG, assessor=None, classifier=None):
        if config.llm and assessor is None:
            raise ValueError(f"config {config.name} needs an LLM assessor")
        self.config = config
        self.assessor = assessor
        if config.ml and classifier is None:
            from pauseline.risk.classifier import get_classifier

            classifier = get_classifier()
        self.classifier = classifier
        self.llm_calls = 0
        self.llm_errors: list[str] = []

    def assess(self, ctx: PaymentContext) -> Assessment:
        """One assessment pass. If ctx.answers is set, answers are folded in."""
        started = time.perf_counter()
        cfg = self.config
        signals: list[Signal] = []
        ctx_signals: list[Signal] = context_signals(ctx) if (cfg.context_rules or ctx.payee.blocked) else []
        if cfg.lexicon:
            signals += language_signals(ctx.statement)

        ml_proba = None
        if cfg.ml and self.classifier is not None:
            pred = self.classifier.predict(ctx.statement)
            ml_proba = pred.proba
            w = ml_weight(pred.proba)
            if w > 0:
                evidence = f"P(scam)={pred.proba:.2f}" + (f"; words: {', '.join(pred.top_terms)}" if pred.top_terms else "")
                signals.append(Signal(name="ml_scam_language", weight=w, evidence=evidence))

        reassure = 1.0
        if cfg.questions and ctx.answers:
            answer_signals, reassure = qbank.answer_effect(ctx.answers)
            signals += answer_signals
        def total(extra: list[Signal], llm_ok: bool = True) -> float:
            ctx_risk = combine(ctx_signals)
            cap = cfg.context_cap
            if cfg.llm and not llm_ok and cap is not None:
                cap = max(cap, CONTEXT_CAP)  # LLM unavailable: fall back to the no-LLM operating point
            if cap is not None and not ctx.payee.blocked:
                ctx_risk = min(ctx_risk, cap)
            return (1 - (1 - ctx_risk) * (1 - combine(extra))) * reassure

        rule_risk = total(signals)

        judgement = None
        assessor_name = cfg.name
        routine = (
            ctx.payee.known
            and not [s for s in ctx_signals + signals if s.weight >= 0.1]
            and (ctx.history_median is None or ctx.amount <= 2 * ctx.history_median)
        )
        if cfg.llm and not (cfg.fast_path and routine):
            from pauseline.risk.llm import LLMUnavailable

            try:
                self.llm_calls += 1
                judgement = self.assessor.assess(ctx, include_context=cfg.llm_context)
                signals.append(Signal(name="llm", weight=llm_weight(judgement.risk, cfg.llm_floor, cfg.llm_max_weight), evidence=f"risk {judgement.risk:.2f}"))
                signals += [Signal(name="ai_flag", weight=0.0, evidence=f) for f in judgement.red_flags]
            except LLMUnavailable as e:
                self.llm_errors.append(str(e))
                assessor_name += " (language model unavailable, ML + rules only)"

        risk = total(signals, llm_ok=judgement is not None or not cfg.llm or (cfg.fast_path and routine))
        signals = ctx_signals + signals
        decision = decide(risk, ctx)
        scam_type = judgement.scam_type if judgement and judgement.scam_type != "none" else lexicon_scam_type(signals)
        if scam_type == "none" and risk >= ASK_AT:
            scam_type = "other"

        qs: list[str] = []
        words_warn = any(s.weight > 0 for s in signals if s not in ctx_signals)
        if cfg.ask_policy == "any":
            should_ask = risk >= ASK_AT
        elif cfg.ask_policy == "strict":  # the LLM's suspicion alone does not trigger questions
            rule_words = any(s.weight > 0 for s in signals if s not in ctx_signals and s.name != "llm")
            should_ask = rule_risk >= COOL_OFF_AT or (rule_words and risk >= ASK_AT) or risk >= HOLD_AT
        else:
            should_ask = risk >= COOL_OFF_AT or (words_warn and risk >= ASK_AT)
        if cfg.questions and not ctx.answers and should_ask and decision is not Decision.BLOCK:
            qs = qbank.pick_questions(signals, judgement.suggested_questions if judgement else None)

        intervenes = decision.intervenes
        message = summary = ""
        if intervenes:
            message = (judgement.message_to_payer if judgement else "") or fallback_message(signals, ctx.statement)
            summary = (judgement.summary_for_family if judgement else "") or fallback_summary(ctx, signals)
        return Assessment(
            risk=round(risk, 4),
            decision=decision,
            scam_type=scam_type if (intervenes or risk >= ASK_AT) else "none",
            signals=signals,
            questions=qs,
            message_to_payer=message,
            summary_for_family=summary,
            assessor=assessor_name,
            llm_risk=judgement.risk if judgement else None,
            ml_proba=ml_proba,
            rule_risk=round(rule_risk, 4),
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
        )


def replace_answers(ctx: PaymentContext, answers: dict[str, str]) -> PaymentContext:
    return ctx.model_copy(update={"answers": dict(answers)})


def build_engine(config: EngineConfig | None = None) -> RiskEngine:
    """Engine for the app: free ML + rules always; adds the LLM layer when one is configured."""
    from pauseline.config import get_settings
    from pauseline.risk.llm import build_assessor

    s = get_settings()
    assessor = build_assessor(s)
    if config is None:
        config = PRODUCT_CONFIG_WITH_LLM if assessor else PRODUCT_CONFIG
    if config.llm and assessor is None:
        config = PRODUCT_CONFIG
    return RiskEngine(config, assessor if config.llm else None)
