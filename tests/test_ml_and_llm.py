"""The on-device classifier and the LLM layer (Groq / Ollama, stubbed with httpx.MockTransport)."""

from __future__ import annotations

import json

import httpx
import pytest

from pauseline.models import Decision, PaymentContext, Payee
from pauseline.risk.classifier import get_classifier, training_rows
from pauseline.risk.engine import CONDITIONS, RiskEngine, ml_weight
from pauseline.risk.llm import ChatLLMAssessor, LLMCache, LLMUnavailable, QuotaGuard


def ctx(statement, known=False, amount=500):
    return PaymentContext(statement=statement, amount=amount, payee=Payee(name="X", known=known), history_median=60)


# ---------------------------------------------------------------- classifier


def test_classifier_separates_obvious_cases_and_explains():
    clf = get_classifier()
    scam = clf.predict("The bank officer is on the phone, he says move my savings to a safe account and tell nobody")
    ok = clf.predict("electricity bill for this month")
    assert scam.proba > 0.8 > 0.2 > ok.proba
    assert scam.top_terms


def test_training_data_has_no_benchmark_copies():
    rows, _ = training_rows()
    bench = {json.loads(l)["statement"].lower().strip() for l in open("eval/scenarios/v1.jsonl", encoding="utf-8") if l.strip()}
    assert not bench & {r["text"].lower().strip() for r in rows}


def test_ml_weight_ignores_low_confidence():
    assert ml_weight(0.3) == 0 and 0 < ml_weight(0.8) < ml_weight(1.0) <= 0.75


# ---------------------------------------------------------------- LLM layer


def chat_stub(payload: dict, status: int = 200, headers: dict | None = None):
    """Stands in for Groq / Ollama's OpenAI-compatible /chat/completions."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        body = {"choices": [{"message": {"content": json.dumps(payload)}}], "usage": {"total_tokens": 700}}
        return httpx.Response(status, json=body, headers=headers or {})

    return httpx.Client(base_url="http://llm", transport=httpx.MockTransport(handler)), seen


def assessor(http, **kw):
    return ChatLLMAssessor(base_url="http://llm", model="openai/gpt-oss-120b", http=http, **kw)


JUDGEMENT = {
    "risk": 0.9,
    "scam_type": "bank_safe_account",
    "red_flags": ["caller directing transfer"],
    "suggested_questions": ["on_call_now"],
    "message_to_payer": "Please hang up first.",
    "summary_for_family": "A caller is directing the payment.",
}


def test_request_shape_and_parse():
    http, seen = chat_stub(JUDGEMENT)
    j = assessor(http).assess(ctx("move to safe account"))
    body = seen[0]
    assert body["model"] == "openai/gpt-oss-120b" and body["reasoning_effort"] == "low"
    assert body["response_format"] == {"type": "json_object"} and "JSON" in body["messages"][0]["content"]
    assert json.loads(body["messages"][1]["content"])["statement"] == "move to safe account"
    assert j.risk == 0.9 and j.suggested_questions == ["on_call_now"] and j.tokens == 700


def test_cache_saves_quota(tmp_path):
    http, seen = chat_stub(JUDGEMENT)
    a = assessor(http, cache=LLMCache(tmp_path / "c.db"))
    a.assess(ctx("move to safe account"))
    second = a.assess(ctx("move to safe account"))
    assert len(seen) == 1 and second.cached and a.cache_hits == 1


def test_quota_guard_fails_fast_and_429_sets_cooldown():
    http, _ = chat_stub(JUDGEMENT)
    a = assessor(http, guard=QuotaGuard(rpm=1, tpm=100_000, tpd=1_000_000))
    a.assess(ctx("one"))
    with pytest.raises(LLMUnavailable, match="quota"):
        a.assess(ctx("two"))
    http429, _ = chat_stub(JUDGEMENT, status=429, headers={"retry-after": "20"})
    g = QuotaGuard()
    with pytest.raises(LLMUnavailable):
        assessor(http429, guard=g).assess(ctx("three"))
    assert g.state()["cooling_down_s"] >= 19


def test_bad_json_is_unavailable():
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    a = assessor(httpx.Client(base_url="http://llm", transport=httpx.MockTransport(handler)))
    with pytest.raises(LLMUnavailable):
        a.assess(ctx("x"))


def test_llm_adds_caution_and_fast_path_skips_it():
    http, seen = chat_stub(JUDGEMENT)
    eng = RiskEngine(CONDITIONS["M_pauseline_full"], assessor(http))
    assert eng.assess(ctx("transferring to my other account")).decision is Decision.HOLD_FOR_FAMILY
    n = len(seen)
    assert eng.assess(ctx("Rahul's books", known=True, amount=40)).decision is Decision.ALLOW
    assert len(seen) == n  # routine payment: model not called


def test_llm_down_falls_back_to_ml_and_rules():
    http, _ = chat_stub({}, status=500)
    eng = RiskEngine(CONDITIONS["M_pauseline_full"], assessor(http))
    a = eng.assess(ctx("they told me to buy gift cards and keep it secret"))
    assert "unavailable" in a.assessor and a.decision is not Decision.ALLOW


def test_context_cap_depends_on_llm_availability():
    """With the LLM, unusual context alone never delays a payment; if the LLM is down, the no-LLM cap applies."""
    big_new = PaymentContext(statement="hospital deposit for my husband's operation", amount=3000, payee=Payee(name="X"), history_median=60)
    calm = {**JUDGEMENT, "risk": 0.05, "scam_type": "none", "red_flags": [], "suggested_questions": [], "message_to_payer": "", "summary_for_family": ""}
    http, _ = chat_stub(calm)
    up = RiskEngine(CONDITIONS["M_pauseline_full"], assessor(http)).assess(big_new)
    assert up.decision is Decision.ALLOW
    http_down, _ = chat_stub({}, status=500)
    down = RiskEngine(CONDITIONS["M_pauseline_full"], assessor(http_down)).assess(big_new)
    assert down.decision is Decision.COOL_OFF
