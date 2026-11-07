"""Payment lifecycle: assess -> (ask) -> PayPal order -> hold -> release / cancel.

    draft --start_payment--> awaiting_payer --payer_approved--> held --release--> released
                                                                   \\--cancel---> cancelled

Every held payment is a PayPal authorisation: the payer's funds are reserved but not taken.
Release = capture (+ payout to the recipient). Cancel = void (the payer is never charged).
"""

from __future__ import annotations

import time
from datetime import datetime

from pauseline.config import Settings, get_settings
from pauseline.models import Assessment, Decision, PaymentContext, Payee, TransferStatus
from pauseline.paypal.client import FakePayPal, PayPalError, PayPalGateway
from pauseline.risk.engine import RiskEngine, replace_answers
from pauseline.store import Store


class FlowError(RuntimeError):
    """A request that does not fit the transfer's current state."""


class PauselineService:
    def __init__(self, store: Store, gateway: PayPalGateway, engine: RiskEngine, settings: Settings | None = None):
        self.store = store
        self.paypal = gateway
        self.engine = engine
        self.settings = settings or get_settings()

    # -- helpers ------------------------------------------------------------
    def _transfer(self, tid: str) -> dict:
        t = self.store.get_transfer(tid)
        if t is None:
            raise FlowError("transfer not found")
        return t

    def _context(self, t: dict, answers: dict[str, str] | None = None) -> PaymentContext:
        p = self.store.get_payee(t["payee_id"])
        assert p is not None
        return PaymentContext(
            statement=t["statement"],
            amount=t["amount"],
            currency=t["currency"],
            payee=Payee(
                name=p["name"], email=p["email"], known=p["known"], relationship=p["relationship"], blocked=p["blocked"]
            ),
            history_median=self.store.history_median(),
            recent_count_1h=self.store.recent_count(),
            hour_of_day=t.get("hour_of_day"),
            answers=answers or {},
        )

    def _save_assessment(self, tid: str, a: Assessment, **extra) -> dict:
        return self.store.update_transfer(
            tid,
            decision=a.decision.value,
            risk=a.risk,
            scam_type=a.scam_type,
            assessment=a.model_dump(mode="json"),
            **extra,
        )

    # -- 1. create + assess -------------------------------------------------
    def create_transfer(self, payee_id: str, amount: float, statement: str, hour_of_day: int | None = None) -> dict:
        if amount <= 0:
            raise FlowError("amount must be positive")
        if self.store.get_payee(payee_id) is None:
            raise FlowError("unknown payee")
        hour = datetime.now().hour if hour_of_day is None else hour_of_day
        t = self.store.create_transfer(
            payee_id=payee_id,
            amount=round(float(amount), 2),
            currency=self.settings.currency,
            statement=statement.strip(),
            hour_of_day=hour,
            status=TransferStatus.DRAFT.value,
        )
        a = self.engine.assess(self._context(t))
        self.store.log(t["id"], "assessed", {"risk": a.risk, "decision": a.decision.value, "by": a.assessor})
        return self._save_assessment(t["id"], a, asked=a.questions)

    # -- 2. answers to clarifying questions ---------------------------------
    def answer_questions(self, tid: str, answers: dict[str, str]) -> dict:
        t = self._transfer(tid)
        if t["status"] != TransferStatus.DRAFT.value:
            raise FlowError("questions can only be answered before paying")
        clean = {k: v.lower() for k, v in answers.items() if k in t["asked"] and v.lower() in {"yes", "no"}}
        a = self.engine.assess(replace_answers(self._context(t), clean))
        a.questions = []  # ask once
        self.store.log(tid, "answered", {"answers": clean, "risk": a.risk, "decision": a.decision.value})
        return self._save_assessment(tid, a, answers=clean)

    # -- 3. PayPal order ----------------------------------------------------
    def start_payment(self, tid: str) -> dict:
        t = self._transfer(tid)
        if t["status"] not in {TransferStatus.DRAFT.value, TransferStatus.AWAITING_PAYER.value}:
            raise FlowError(f"cannot start payment from status {t['status']}")
        if t["asked"] and not t["answers"]:
            raise FlowError("please answer the questions first")
        if t["status"] == TransferStatus.AWAITING_PAYER.value and t["order_id"]:
            return t
        p = self.store.get_payee(t["payee_id"]) or {}
        order = self.paypal.create_order(
            amount=t["amount"], currency=t["currency"], reference_id=tid, description=f"Pauseline payment to {p.get('name', '')}"
        )
        self.store.log(tid, "paypal.order_created", {"order_id": order.order_id})
        return self.store.update_transfer(tid, order_id=order.order_id, status=TransferStatus.AWAITING_PAYER.value)

    # -- 4. payer approved in PayPal: authorise (hold) and apply the decision --
    def payer_approved(self, tid: str) -> dict:
        t = self._transfer(tid)
        if t["status"] != TransferStatus.AWAITING_PAYER.value:
            if t["status"] in {TransferStatus.HELD.value, TransferStatus.RELEASED.value}:
                return t  # duplicate callback
            raise FlowError(f"cannot authorise from status {t['status']}")
        if isinstance(self.paypal, FakePayPal):
            self.paypal.approve(t["order_id"])
        try:
            auth = self.paypal.authorize_order(t["order_id"], request_id=f"auth-{tid}")
        except PayPalError as e:
            self.store.log(tid, "paypal.error", {"step": "authorize", "error": str(e), "debug_id": e.debug_id})
            return self.store.update_transfer(tid, status=TransferStatus.FAILED.value)
        if auth.status != "CREATED":
            # PayPal can return 201 with a DENIED authorisation: always check the status, not the HTTP code.
            self.store.log(tid, "paypal.authorization_denied", {"status": auth.status})
            return self.store.update_transfer(tid, authorization_id=auth.authorization_id, status=TransferStatus.FAILED.value)
        self.store.log(tid, "paypal.authorized", {"authorization_id": auth.authorization_id, "held": True})
        t = self.store.update_transfer(tid, authorization_id=auth.authorization_id, status=TransferStatus.HELD.value)
        return self._apply_decision(t)

    def _apply_decision(self, t: dict) -> dict:
        tid = t["id"]
        decision = Decision(t["decision"])
        if decision is Decision.ALLOW:
            return self.release(tid, reason="low risk")
        if decision is Decision.BLOCK:
            return self.cancel(tid, reason="payee is blocked")
        if decision is Decision.COOL_OFF:
            release_at = time.time() + self.settings.cooling_off_seconds
            self.store.log(tid, "held.cooling_off", {"release_at": release_at})
            self.store.log(tid, "family.notified", {"kind": "fyi_cooling_off"})
            return self.store.update_transfer(tid, release_at=release_at)
        self.store.log(tid, "held.for_family", {})
        self.store.log(tid, "family.notified", {"kind": "approval_needed"})
        return t

    # -- 5. release / cancel ------------------------------------------------
    def release(self, tid: str, reason: str) -> dict:
        t = self._transfer(tid)
        if t["status"] != TransferStatus.HELD.value:
            raise FlowError(f"cannot release from status {t['status']}")
        try:
            cap = self.paypal.capture_authorization(t["authorization_id"], request_id=f"capture-{tid}")
        except PayPalError as e:
            self.store.log(tid, "paypal.error", {"step": "capture", "error": str(e), "debug_id": e.debug_id})
            raise FlowError(f"PayPal capture failed: {e}") from e
        self.store.log(tid, "paypal.captured", {"capture_id": cap.capture_id, "status": cap.status, "reason": reason})
        fields: dict = {"capture_id": cap.capture_id, "status": TransferStatus.RELEASED.value}
        p = self.store.get_payee(t["payee_id"]) or {}
        if self.settings.paypal_use_payouts and p.get("email"):
            try:
                po = self.paypal.send_payout(
                    receiver_email=p["email"],
                    amount=t["amount"],
                    currency=t["currency"],
                    note=f"Payment via Pauseline: {t['statement'][:200]}",
                    request_id=f"payout-{tid}",
                )
                fields["payout_batch_id"] = po.batch_id
                self.store.log(tid, "paypal.payout_sent", {"batch_id": po.batch_id, "status": po.status})
            except PayPalError as e:
                # Funds are captured; delivery can be retried without charging the payer again.
                self.store.log(tid, "paypal.error", {"step": "payout", "error": str(e), "debug_id": e.debug_id})
        self.store.add_past_payment(t["amount"])
        return self.store.update_transfer(tid, **fields)

    def cancel(self, tid: str, reason: str) -> dict:
        t = self._transfer(tid)
        if t["status"] == TransferStatus.CANCELLED.value:
            return t
        if t["status"] == TransferStatus.HELD.value and t["authorization_id"]:
            try:
                self.paypal.void_authorization(t["authorization_id"], request_id=f"void-{tid}")
            except PayPalError as e:
                self.store.log(tid, "paypal.error", {"step": "void", "error": str(e), "debug_id": e.debug_id})
                raise FlowError(f"PayPal void failed: {e}") from e
            self.store.log(tid, "paypal.voided", {"authorization_id": t["authorization_id"], "reason": reason})
        elif t["status"] not in {TransferStatus.DRAFT.value, TransferStatus.AWAITING_PAYER.value}:
            raise FlowError(f"cannot cancel from status {t['status']}")
        else:
            self.store.log(tid, "cancelled", {"reason": reason})
        return self.store.update_transfer(tid, status=TransferStatus.CANCELLED.value)

    # -- 6. trusted contact -------------------------------------------------
    def family_decide(self, tid: str, approve: bool, note: str = "") -> dict:
        t = self._transfer(tid)
        if t["status"] != TransferStatus.HELD.value:
            raise FlowError("this payment is not waiting for a decision")
        self.store.update_transfer(tid, family_decision="approved" if approve else "declined", family_note=note[:500])
        self.store.log(tid, "family.approved" if approve else "family.declined", {"note": note[:500]})
        if approve:
            return self.release(tid, reason="trusted contact approved")
        return self.cancel(tid, reason="trusted contact declined")

    def payer_cancel(self, tid: str) -> dict:
        return self.cancel(tid, reason="payer changed their mind")

    # -- 7. background ------------------------------------------------------
    def tick(self, now: float | None = None) -> list[str]:
        """Release cooling-off payments whose time is up and that the family did not decline."""
        released = []
        for t in self.store.due_for_release(now):
            try:
                self.release(t["id"], reason="cooling-off period ended")
                released.append(t["id"])
            except FlowError as e:
                self.store.log(t["id"], "release.failed", str(e))
        return released

    # -- 8. webhooks --------------------------------------------------------
    def handle_webhook(self, event: dict) -> None:
        kind = event.get("event_type", "unknown")
        resource = event.get("resource", {}) or {}
        tid = None
        order_id = (resource.get("supplementary_data", {}) or {}).get("related_ids", {}).get("order_id")
        auth_id = resource.get("id") if kind.startswith("PAYMENT.AUTHORIZATION") else None
        if order_id:
            t = self.store.find_transfer_by_order(order_id)
            tid = t["id"] if t else None
        if tid is None and auth_id:
            t = self.store.find_transfer_by_authorization(auth_id)
            tid = t["id"] if t else None
        if tid is None and resource.get("custom_id"):
            tid = resource["custom_id"]
        self.store.log(tid, f"webhook.{kind}", {"resource_id": resource.get("id"), "status": resource.get("status")})
