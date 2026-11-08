"""PayPal REST client (sandbox) plus an in-memory fake with the same interface.

Money flow (Pauseline is the platform in the middle):
1. create_order(intent=AUTHORIZE)       payer approves it with the PayPal button
2. authorize_order                      funds are HELD on the payer's account, nothing taken yet
3a. capture_authorization -> payout     released: money taken, then sent on to the recipient
3b. void_authorization                  cancelled: the hold is dropped, the payer is never charged

Docs: https://developer.paypal.com/docs/api/orders/v2/ , /payments/v2/ , /payments.payouts-batch/v1/
"""

from __future__ import annotations

import itertools
import time
import uuid
from dataclasses import dataclass, field
from typing import Protocol

import httpx


class PayPalError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, debug_id: str | None = None, details: object = None):
        super().__init__(message)
        self.status = status
        self.debug_id = debug_id
        self.details = details


@dataclass
class OrderResult:
    order_id: str
    status: str
    approve_url: str | None = None


@dataclass
class AuthorizationResult:
    authorization_id: str
    status: str  # CREATED means funds are held; DENIED means PayPal refused
    expiration_time: str | None = None


@dataclass
class CaptureResult:
    capture_id: str
    status: str  # COMPLETED or PENDING


@dataclass
class PayoutResult:
    batch_id: str
    status: str


class PayPalGateway(Protocol):
    live: bool

    def create_order(self, *, amount: float, currency: str, reference_id: str, description: str) -> OrderResult: ...
    def authorize_order(self, order_id: str, *, request_id: str) -> AuthorizationResult: ...
    def capture_authorization(self, authorization_id: str, *, request_id: str) -> CaptureResult: ...
    def void_authorization(self, authorization_id: str, *, request_id: str) -> None: ...
    def send_payout(self, *, receiver_email: str, amount: float, currency: str, note: str, request_id: str) -> PayoutResult: ...
    def verify_webhook(self, headers: dict[str, str], event: dict, webhook_id: str) -> bool: ...


def _money(amount: float) -> str:
    return f"{amount:.2f}"


class PayPalClient:
    """Thin, explicit wrapper around the PayPal REST endpoints Pauseline uses."""

    live = True

    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://api-m.sandbox.paypal.com", timeout: float = 30.0):
        self._id = client_id
        self._secret = client_secret
        self._base = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self._base, timeout=timeout)
        self._token: str | None = None
        self._token_expires = 0.0

    # -- auth ---------------------------------------------------------------
    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        try:
            r = self._http.post(
                "/v1/oauth2/token",
                auth=(self._id, self._secret),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as e:
            raise PayPalError(f"Could not reach PayPal: {type(e).__name__}") from e
        if r.status_code != 200:
            raise PayPalError(f"PayPal auth failed: {r.text[:300]}", r.status_code)
        body = r.json()
        self._token = body["access_token"]
        self._token_expires = time.time() + float(body.get("expires_in", 3000))
        return self._token

    def _request(self, method: str, path: str, *, json: dict | None = None, request_id: str | None = None) -> dict:
        headers = {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        if request_id:
            headers["PayPal-Request-Id"] = request_id  # idempotency: retries never double-charge
        try:
            r = self._http.request(method, path, json=json, headers=headers)
        except httpx.HTTPError as e:
            raise PayPalError(f"Could not reach PayPal: {type(e).__name__}") from e
        if r.status_code >= 400:
            try:
                body = r.json()
            except ValueError:
                body = {"message": r.text[:300]}
            raise PayPalError(
                f"PayPal {method} {path} failed: {body.get('name', '')} {body.get('message', '')}".strip(),
                r.status_code,
                body.get("debug_id"),
                body.get("details"),
            )
        return r.json() if r.content else {}

    # -- orders / payments --------------------------------------------------
    def create_order(self, *, amount: float, currency: str, reference_id: str, description: str) -> OrderResult:
        body = self._request(
            "POST",
            "/v2/checkout/orders",
            json={
                "intent": "AUTHORIZE",
                "purchase_units": [
                    {
                        "reference_id": reference_id,
                        "custom_id": reference_id,
                        "description": description[:127],
                        "amount": {"currency_code": currency, "value": _money(amount)},
                    }
                ],
            },
            request_id=f"order-{reference_id}",
        )
        approve = next((l["href"] for l in body.get("links", []) if l.get("rel") in {"approve", "payer-action"}), None)
        return OrderResult(order_id=body["id"], status=body.get("status", ""), approve_url=approve)

    def authorize_order(self, order_id: str, *, request_id: str) -> AuthorizationResult:
        body = self._request("POST", f"/v2/checkout/orders/{order_id}/authorize", json={}, request_id=request_id)
        auth = body["purchase_units"][0]["payments"]["authorizations"][0]
        return AuthorizationResult(auth["id"], auth.get("status", ""), auth.get("expiration_time"))

    def capture_authorization(self, authorization_id: str, *, request_id: str) -> CaptureResult:
        body = self._request(
            "POST",
            f"/v2/payments/authorizations/{authorization_id}/capture",
            json={"final_capture": True},
            request_id=request_id,
        )
        return CaptureResult(body["id"], body.get("status", ""))

    def void_authorization(self, authorization_id: str, *, request_id: str) -> None:
        self._request("POST", f"/v2/payments/authorizations/{authorization_id}/void", request_id=request_id)

    def send_payout(self, *, receiver_email: str, amount: float, currency: str, note: str, request_id: str) -> PayoutResult:
        body = self._request(
            "POST",
            "/v1/payments/payouts",
            json={
                "sender_batch_header": {
                    "sender_batch_id": request_id,
                    "email_subject": "You have received a payment",
                    "email_message": note[:1000],
                },
                "items": [
                    {
                        "recipient_type": "EMAIL",
                        "receiver": receiver_email,
                        "amount": {"value": _money(amount), "currency": currency},
                        "note": note[:4000],
                        "sender_item_id": request_id,
                    }
                ],
            },
            request_id=request_id,
        )
        header = body.get("batch_header", {})
        return PayoutResult(header.get("payout_batch_id", ""), header.get("batch_status", ""))

    def verify_webhook(self, headers: dict[str, str], event: dict, webhook_id: str) -> bool:
        h = {k.lower(): v for k, v in headers.items()}
        body = self._request(
            "POST",
            "/v1/notifications/verify-webhook-signature",
            json={
                "auth_algo": h.get("paypal-auth-algo", ""),
                "cert_url": h.get("paypal-cert-url", ""),
                "transmission_id": h.get("paypal-transmission-id", ""),
                "transmission_sig": h.get("paypal-transmission-sig", ""),
                "transmission_time": h.get("paypal-transmission-time", ""),
                "webhook_id": webhook_id,
                "webhook_event": event,
            },
        )
        return body.get("verification_status") == "SUCCESS"


@dataclass
class _FakeAuth:
    order_id: str
    amount: float
    currency: str
    status: str = "CREATED"


@dataclass
class FakePayPal:
    """In-memory PayPal double that enforces the same state rules as the real API.

    - authorize only once per order; capture/void only a CREATED authorisation;
    - the same request id returns the same result (idempotency), like PayPal-Request-Id.
    """

    live: bool = False
    orders: dict[str, dict] = field(default_factory=dict)
    auths: dict[str, _FakeAuth] = field(default_factory=dict)
    payouts: list[dict] = field(default_factory=list)
    _seen: dict[str, object] = field(default_factory=dict)
    _ids: itertools.count = field(default_factory=lambda: itertools.count(1))

    def _id(self, prefix: str) -> str:
        return f"{prefix}{next(self._ids):06d}{uuid.uuid4().hex[:6].upper()}"

    def create_order(self, *, amount: float, currency: str, reference_id: str, description: str) -> OrderResult:
        key = f"order-{reference_id}"
        if key in self._seen:
            return self._seen[key]  # type: ignore[return-value]
        oid = self._id("FAKEORDER")
        self.orders[oid] = {"amount": amount, "currency": currency, "status": "CREATED", "reference_id": reference_id}
        res = OrderResult(oid, "CREATED", None)
        self._seen[key] = res
        return res

    def approve(self, order_id: str) -> None:
        """Stands in for the payer approving in the PayPal popup."""
        self.orders[order_id]["status"] = "APPROVED"

    def authorize_order(self, order_id: str, *, request_id: str) -> AuthorizationResult:
        if request_id in self._seen:
            return self._seen[request_id]  # type: ignore[return-value]
        order = self.orders.get(order_id)
        if order is None:
            raise PayPalError("RESOURCE_NOT_FOUND", 404)
        if order["status"] == "CREATED":
            order["status"] = "APPROVED"  # demo mode: approval is implicit
        if order["status"] != "APPROVED":
            raise PayPalError("ORDER_ALREADY_AUTHORIZED", 422)
        order["status"] = "COMPLETED"
        aid = self._id("FAKEAUTH")
        self.auths[aid] = _FakeAuth(order_id, order["amount"], order["currency"])
        res = AuthorizationResult(aid, "CREATED", None)
        self._seen[request_id] = res
        return res

    def capture_authorization(self, authorization_id: str, *, request_id: str) -> CaptureResult:
        if request_id in self._seen:
            return self._seen[request_id]  # type: ignore[return-value]
        auth = self.auths.get(authorization_id)
        if auth is None:
            raise PayPalError("RESOURCE_NOT_FOUND", 404)
        if auth.status != "CREATED":
            raise PayPalError(f"AUTHORIZATION_{auth.status}", 422)
        auth.status = "CAPTURED"
        res = CaptureResult(self._id("FAKECAP"), "COMPLETED")
        self._seen[request_id] = res
        return res

    def void_authorization(self, authorization_id: str, *, request_id: str) -> None:
        if request_id in self._seen:
            return
        auth = self.auths.get(authorization_id)
        if auth is None:
            raise PayPalError("RESOURCE_NOT_FOUND", 404)
        if auth.status != "CREATED":
            raise PayPalError(f"AUTHORIZATION_{auth.status}", 422)
        auth.status = "VOIDED"
        self._seen[request_id] = True

    def send_payout(self, *, receiver_email: str, amount: float, currency: str, note: str, request_id: str) -> PayoutResult:
        if request_id in self._seen:
            return self._seen[request_id]  # type: ignore[return-value]
        self.payouts.append({"receiver": receiver_email, "amount": amount, "currency": currency, "note": note})
        res = PayoutResult(self._id("FAKEPAYOUT"), "SUCCESS")
        self._seen[request_id] = res
        return res

    def verify_webhook(self, headers: dict[str, str], event: dict, webhook_id: str) -> bool:
        return True


def build_gateway() -> PayPalGateway:
    from pauseline.config import get_settings

    s = get_settings()
    if s.paypal_live:
        return PayPalClient(s.paypal_client_id, s.paypal_client_secret, s.paypal_base_url)
    return FakePayPal()
