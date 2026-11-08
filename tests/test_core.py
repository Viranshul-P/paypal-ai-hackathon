from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from pauseline.app import create_app, seed_demo
from pauseline.config import Settings
from pauseline.models import Decision, PaymentContext, Payee
from pauseline.paypal.client import FakePayPal, PayPalError
from pauseline.risk.engine import CONDITIONS, PRODUCT_CONFIG, RiskEngine
from pauseline.risk.signals import combine, language_signals
from pauseline.service import FlowError, PauselineService
from pauseline.store import Store


def ctx(statement: str, amount: float = 50, known: bool = True, median: float | None = 60, **kw) -> PaymentContext:
    return PaymentContext(
        statement=statement, amount=amount, payee=Payee(name="X", known=known), history_median=median, **kw
    )


# ---------------------------------------------------------------- signals


def test_lexicon_catches_core_scam_phrases():
    names = {s.name for s in language_signals("The bank officer told me to move my savings to a safe account, don't tell my son")}
    assert {"safe_account", "secrecy", "coached"} <= names


def test_lexicon_hindi_and_hinglish():
    assert {s.name for s in language_signals("CBI wale bol rahe hain digital arrest ho jayega, kisi ko mat batana")} >= {
        "legal_threat",
        "secrecy",
        "authority_impersonation",
    }
    assert "secrecy" in {s.name for s in language_signals("किसी को मत बताना")}


def test_lexicon_quiet_on_normal_payments():
    for text in ["Rahul's college books", "electricity bill for October", "rent for November", "Dr Mehta consultation fee"]:
        assert language_signals(text) == [], text


def test_combine_is_bounded():
    from pauseline.models import Signal

    assert combine([]) == 0
    assert 0 < combine([Signal(name="a", weight=0.5), Signal(name="b", weight=0.5)]) < 1


# ---------------------------------------------------------------- engine (offline)


def test_routine_payment_allowed_without_questions():
    a = RiskEngine(PRODUCT_CONFIG).assess(ctx("Rahul's college books"))
    assert a.decision is Decision.ALLOW and a.questions == []


def test_scam_payment_held():
    eng = RiskEngine(PRODUCT_CONFIG)
    c = ctx("The police officer on the video call said I will be arrested unless I pay now, do not tell anyone", amount=3000, known=False)
    first = eng.assess(c)
    assert first.questions, "should ask clarifying questions"
    final = eng.assess(c.model_copy(update={"answers": {q: "yes" for q in first.questions}}))
    assert final.decision is Decision.HOLD_FOR_FAMILY
    assert final.message_to_payer and final.summary_for_family


def test_blocked_payee_always_blocked():
    c = PaymentContext(statement="gift", amount=10, payee=Payee(name="Bad", known=True, blocked=True))
    assert RiskEngine(CONDITIONS["A_rules_context"]).assess(c).decision is Decision.BLOCK


def test_reassuring_answers_lower_but_dont_erase_risk():
    eng = RiskEngine(PRODUCT_CONFIG)
    c = ctx("He said it's urgent, send it immediately", amount=900, known=False)
    before = eng.assess(c).risk
    after = eng.assess(c.model_copy(update={"answers": {"on_call_now": "no", "someone_asked": "no"}})).risk
    assert 0 < after < before


def test_llm_conditions_require_assessor():
    with pytest.raises(ValueError):
        RiskEngine(CONDITIONS["M_pauseline_full"])


def test_product_engine_is_free_and_on_device():
    assert not PRODUCT_CONFIG.llm and PRODUCT_CONFIG.ml


# ---------------------------------------------------------------- PayPal fake


def test_fake_paypal_state_rules_and_idempotency():
    pp = FakePayPal()
    o = pp.create_order(amount=10, currency="USD", reference_id="t1", description="x")
    assert pp.create_order(amount=10, currency="USD", reference_id="t1", description="x").order_id == o.order_id
    a = pp.authorize_order(o.order_id, request_id="auth-t1")
    c1 = pp.capture_authorization(a.authorization_id, request_id="cap-t1")
    assert pp.capture_authorization(a.authorization_id, request_id="cap-t1").capture_id == c1.capture_id
    with pytest.raises(PayPalError):
        pp.void_authorization(a.authorization_id, request_id="void-t1")


# ---------------------------------------------------------------- service lifecycle


@pytest.fixture
def svc(tmp_path):
    store = Store(tmp_path / "t.db")
    seed_demo(store)
    settings = Settings(db_path=tmp_path / "t.db", cooling_off_seconds=60, paypal_use_payouts=True)
    return PauselineService(store, FakePayPal(), RiskEngine(PRODUCT_CONFIG), settings)


def payee(svc, name):
    return svc.store.find_payee_by_name(name)["id"]


def run_to_hold(svc, payee_name, amount, statement, answers="yes"):
    t = svc.create_transfer(payee(svc, payee_name), amount, statement)
    if t["asked"]:
        t = svc.answer_questions(t["id"], {q: answers for q in t["asked"]})
    svc.start_payment(t["id"])
    return svc.payer_approved(t["id"])


def test_routine_payment_released_and_paid_out(svc):
    t = run_to_hold(svc, "Rahul", 60, "Rahul's books")
    assert t["status"] == "released" and t["capture_id"] and t["payout_batch_id"]
    assert svc.paypal.payouts[-1]["amount"] == 60


def test_scam_held_then_family_declines_voids(svc):
    t = run_to_hold(svc, "Safe Account Services", 4000, "Bank fraud team says my account is hacked, move savings to safe account now, they are still on the phone")
    assert t["status"] == "held" and t["decision"] == "hold_for_family"
    t = svc.family_decide(t["id"], approve=False, note="Call me")
    assert t["status"] == "cancelled"
    assert svc.paypal.auths[t["authorization_id"]].status == "VOIDED"
    assert not svc.paypal.payouts


def test_family_approve_releases(svc):
    t = run_to_hold(svc, "Safe Account Services", 4000, "they told me to move money to a safe account")
    t = svc.family_decide(t["id"], approve=True)
    assert t["status"] == "released"


def test_cooling_off_auto_release(svc):
    svc.engine = RiskEngine(CONDITIONS["B_rules_lexicon"])  # no questions: deterministic decision
    t = svc.create_transfer(payee(svc, "Dr. Mehta Clinic"), 700, "urgent, pay immediately")
    svc.start_payment(t["id"])
    t = svc.payer_approved(t["id"])
    assert t["decision"] == "cool_off" and t["status"] == "held"
    assert svc.tick(now=time.time()) == []
    assert svc.tick(now=time.time() + 61) == [t["id"]]
    assert svc.store.get_transfer(t["id"])["status"] == "released"


def test_questions_must_be_answered_before_paying(svc):
    t = svc.create_transfer(payee(svc, "Safe Account Services"), 3000, "the officer said do not tell anyone")
    assert t["asked"]
    with pytest.raises(FlowError):
        svc.start_payment(t["id"])


# ---------------------------------------------------------------- HTTP API


def test_http_flow(svc):
    client = TestClient(create_app(svc))
    assert client.get("/").status_code == 200
    assert client.get("/send").status_code == 200
    assert client.get("/family").status_code == 200
    pid = payee(svc, "Rahul")
    t = client.post("/api/transfers", json={"payee_id": pid, "amount": 50, "statement": "books"}).json()
    order = client.post(f"/api/transfers/{t['id']}/order").json()
    assert order["order_id"]
    t = client.post(f"/api/transfers/{t['id']}/approved").json()
    assert t["status"] == "released"
    overview = client.get("/api/family/overview", headers={"X-Family-Pin": svc.settings.family_pin}).json()
    assert overview["recent"][0]["id"] == t["id"]


def test_demo_reset_voids_holds_and_reseeds(svc):
    client = TestClient(create_app(svc))
    t = run_to_hold(svc, "Safe Account Services", 4000, "they told me to move money to a safe account, keep it secret")
    assert t["status"] == "held"
    assert client.post("/api/demo/reset", headers={"X-Family-Pin": svc.settings.family_pin}).json() == {"ok": True}
    assert svc.paypal.auths[t["authorization_id"]].status == "VOIDED"
    assert svc.store.list_transfers() == [] and svc.store.find_payee_by_name("Rahul")
    assert client.get("/health").json() == {"ok": True}
    assert client.get("/favicon.ico").status_code == 200


# ---------------------------------------------------------------- family PIN and flow guards


def test_family_actions_need_the_pin(svc):
    client = TestClient(create_app(svc))
    pin = {"X-Family-Pin": svc.settings.family_pin}
    t = run_to_hold(svc, "Safe Account Services", 4000, "they told me to move money to a safe account")
    url = f"/api/transfers/{t['id']}/family"

    assert client.post(url, json={"approve": True}).status_code == 401
    assert client.post(url, json={"approve": True}, headers={"X-Family-Pin": "wrong"}).status_code == 401
    assert client.get("/api/family/overview").status_code == 401
    assert client.post("/api/demo/reset").status_code == 401
    assert svc.store.get_transfer(t["id"])["status"] == "held"

    assert client.post(url, json={"approve": True}, headers=pin).json()["status"] == "released"


def test_only_family_can_vouch_for_a_payee(svc):
    client = TestClient(create_app(svc))
    pin = {"X-Family-Pin": svc.settings.family_pin}
    new = client.post("/api/payees", json={"name": "New Person", "email": "n@example.com", "known": False})
    assert new.status_code == 200
    assert client.post("/api/payees", json={"name": "Vouched", "email": "v@example.com", "known": True}).status_code == 401
    assert client.patch(f"/api/payees/{new.json()['id']}", json={"known": True}).status_code == 401
    assert client.patch(f"/api/payees/{new.json()['id']}", json={"known": True}, headers=pin).json()["known"] is True
    assert client.post("/api/payees", json={"name": "Bad", "email": "not-an-email", "known": False}).status_code == 422


def test_wrong_pins_are_rate_limited(svc):
    client = TestClient(create_app(svc))
    codes = [client.get("/api/family/overview", headers={"X-Family-Pin": "0000"}).status_code for _ in range(21)]
    assert codes[:20] == [401] * 20 and codes[20] == 429


def test_questions_can_only_be_answered_once_and_in_full(svc):
    t = svc.create_transfer(payee(svc, "Safe Account Services"), 3000, "the officer said do not tell anyone")
    with pytest.raises(FlowError):
        svc.answer_questions(t["id"], {t["asked"][0]: "maybe"})
    svc.answer_questions(t["id"], {q: "yes" for q in t["asked"]})
    with pytest.raises(FlowError):
        svc.answer_questions(t["id"], {q: "no" for q in t["asked"]})


def test_paypal_outage_is_a_clear_error_not_a_crash(svc):
    def down(**kwargs):
        raise PayPalError("Could not reach PayPal: ConnectTimeout")

    svc.paypal.create_order = down
    t = svc.create_transfer(payee(svc, "Rahul"), 50, "books")
    with pytest.raises(FlowError, match="could not start"):
        svc.start_payment(t["id"])


def test_bad_webhooks_are_rejected_not_crashed(tmp_path):
    def refuses(*args):
        raise PayPalError("INVALID_REQUEST", 400)

    store = Store(tmp_path / "w.db")
    settings = Settings(db_path=tmp_path / "w.db", paypal_webhook_id="wh-1")
    gateway = FakePayPal(live=True)
    gateway.verify_webhook = refuses
    client = TestClient(create_app(PauselineService(store, gateway, RiskEngine(PRODUCT_CONFIG), settings)))
    assert client.post("/webhooks/paypal", json={}).status_code == 400
    assert client.post("/webhooks/paypal", content=b"not json").status_code == 400
    assert store.events() == []


def test_failed_payout_is_reported_not_shown_as_sent(svc):
    def down(**kwargs):
        raise PayPalError("PAYOUTS_NOT_ENABLED", 403)

    svc.paypal.send_payout = down
    client = TestClient(create_app(svc))
    t = client.post("/api/transfers", json={"payee_id": payee(svc, "Rahul"), "amount": 50, "statement": "books"}).json()
    client.post(f"/api/transfers/{t['id']}/order")
    done = client.post(f"/api/transfers/{t['id']}/approved").json()
    assert done["status"] == "released" and done["delivery_failed"] is True
