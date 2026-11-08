"""FastAPI app: payer screens, trusted-contact dashboard, JSON API, PayPal webhooks."""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import os
import re
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from pauseline.config import get_settings
from pauseline.paypal.client import PayPalError, build_gateway
from pauseline.risk.engine import SIGNAL_LABELS, build_engine
from pauseline.risk.questions import QUESTIONS
from pauseline.service import FlowError, PauselineService
from pauseline.store import Store

HERE = Path(__file__).parent
WEB = HERE / "web"  # the built React app (frontend/)


class NewTransfer(BaseModel):
    payee_id: str
    amount: float = Field(gt=0)
    statement: str = Field(default="", max_length=2000)


class Answers(BaseModel):
    answers: dict[str, str]


class FamilyDecision(BaseModel):
    approve: bool
    note: str = ""


class NewPayee(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = ""
    relationship: str = ""
    known: bool = True
    blocked: bool = False

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = v.strip()
        if v and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("please enter a valid email address")
        return v


class IntentRequest(BaseModel):
    text: str = Field(default="", max_length=2000)


class PayeeUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    relationship: str | None = None
    known: bool | None = None
    blocked: bool | None = None


def seed_demo(store: Store) -> None:
    """Demo household: Kamla (the payer), her daughter Asha (trusted contact), a few known payees."""
    if store.get_setting("seeded"):
        return
    # Payouts need a real sandbox personal account email (developer.paypal.com -> Sandbox accounts).
    recipient = os.getenv("PAUSELINE_DEMO_RECIPIENT_EMAIL", "")
    store.set_setting("payer_name", "Kamla")
    store.set_setting("contact_name", "Asha")
    store.set_setting("contact_relationship", "daughter")
    store.add_payee("Rahul", recipient or "rahul@example.com", "grandson", known=True)
    store.add_payee("City Electric", recipient or "billing@cityelectric.example.com", "electricity bill", known=True)
    store.add_payee("Dr. Mehta Clinic", recipient or "frontdesk@mehtaclinic.example.com", "doctor", known=True)
    store.add_payee("Safe Account Services", recipient or "secure-desk@example.com", "", known=False)
    for amt in (40, 65, 120, 35, 80, 55, 150, 45, 60, 90):
        store.add_past_payment(amt)
    store.set_setting("seeded", "1")


def create_app(service: PauselineService | None = None) -> FastAPI:
    settings = service.settings if service is not None else get_settings()
    if service is None:
        store = Store(settings.db_path)
        seed_demo(store)
        service = PauselineService(store, build_gateway(), build_engine(), settings)
    svc = service

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        async def ticker():
            while True:
                await asyncio.sleep(10)
                try:
                    await asyncio.to_thread(svc.tick)
                except Exception as e:  # keep the loop alive; the error is logged on the timeline
                    svc.store.log(None, "tick.error", str(e))

        task = asyncio.create_task(ticker())
        try:
            yield
        finally:
            task.cancel()

    app = FastAPI(title="Pauseline", lifespan=lifespan)
    app.state.service = svc
    app.mount("/assets", StaticFiles(directory=str(WEB / "assets"), check_dir=False), name="assets")

    def ai_mode() -> str:
        a = svc.engine.assessor
        if svc.engine.config.llm and a is not None:
            if a.last_error or (a.guard and a.guard.state()["cooling_down_s"]):
                return f"on-device ML · {a.label} paused, ML only"
            return f"on-device ML + {a.label}"
        return "on-device ML" if svc.engine.config.ml else "rules only"

    # Per-visitor limit on payment checks, so one person cannot spend the shared free LLM quota.
    hits: dict[str, deque] = defaultdict(deque)
    hits_lock = threading.Lock()

    def check_rate(request: Request) -> None:
        ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()) or (request.client.host if request.client else "?")
        now = time.time()
        with hits_lock:
            q = hits[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= settings.assess_per_minute:
                raise HTTPException(429, "Too many payment checks in a minute. Please wait a moment and try again.")
            q.append(now)

    # Family decisions and setup need the trusted contact's PIN. Wrong guesses are limited across
    # all visitors, because the forwarded address can be spoofed.
    pin_failures: deque = deque()

    def require_family(request: Request) -> None:
        now = time.time()
        with hits_lock:
            while pin_failures and now - pin_failures[0] > 60:
                pin_failures.popleft()
            if len(pin_failures) >= 20:
                raise HTTPException(429, "Too many wrong PINs. Please wait a minute and try again.")
        given = request.headers.get("x-family-pin", "")
        if not hmac.compare_digest(given.encode(), settings.family_pin.encode()):
            with hits_lock:
                pin_failures.append(now)
            raise HTTPException(401, "That PIN is not right.")

    # -- pages: every route is the React app -----------------------------------
    @app.get("/", include_in_schema=False)
    @app.get("/send", include_in_schema=False)
    @app.get("/family", include_in_schema=False)
    @app.get("/setup", include_in_schema=False)
    def spa():
        return FileResponse(WEB / "index.html")

    @app.get("/api/config")
    def api_config():
        return {
            "paypal_live": svc.paypal.live,
            "paypal_client_id": settings.paypal_client_id,
            "currency": settings.currency,
            "ai_mode": ai_mode(),
            "cloud_ai": bool(svc.engine.config.llm and svc.engine.assessor is not None),
            "demo_pin": settings.family_pin if settings.family_pin_is_default else "",
            "payer_name": svc.store.get_setting("payer_name", "You"),
            "contact_name": svc.store.get_setting("contact_name", "your trusted contact"),
            "contact_relationship": svc.store.get_setting("contact_relationship", ""),
        }

    # -- API: payer -----------------------------------------------------------


    def _wrap(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FlowError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

    def _public(t: dict) -> dict:
        a = t.get("assessment") or {}
        lang_hi = any("ऀ" <= ch <= "ॿ" for ch in t.get("statement", ""))
        payee_row = svc.store.get_payee(t["payee_id"]) or {}
        return {
            # Money was captured but PayPal did not accept the payout to the recipient.
            "delivery_failed": bool(
                t["status"] == "released" and settings.paypal_use_payouts and payee_row.get("email") and not t.get("payout_batch_id")
            ),
            "id": t["id"],
            "status": t["status"],
            "decision": t.get("decision"),
            "risk": t.get("risk"),
            "amount": t["amount"],
            "currency": t["currency"],
            "payee": svc.store.get_payee(t["payee_id"]),
            "statement": t.get("statement", ""),
            "scam_type": t.get("scam_type"),
            "message_to_payer": a.get("message_to_payer", ""),
            "summary_for_family": a.get("summary_for_family", ""),
            "signals": [
                {**s, "label": SIGNAL_LABELS.get(s["name"], s["name"].replace("_", " "))}
                for s in a.get("signals", [])
                if s.get("evidence")
            ],
            "assessor": a.get("assessor", ""),
            "questions": [
                {"id": q, "text": QUESTIONS[q].hi if lang_hi else QUESTIONS[q].en, "text_hi": QUESTIONS[q].hi}
                for q in (a.get("questions") or [])
                if q in QUESTIONS
            ],
            "answers": t.get("answers") or {},
            "order_id": t.get("order_id"),
            "authorization_id": t.get("authorization_id"),
            "capture_id": t.get("capture_id"),
            "payout_batch_id": t.get("payout_batch_id"),
            "release_at": t.get("release_at"),
            "family_decision": t.get("family_decision"),
            "family_note": t.get("family_note"),
            "created_at": t["created_at"],
            "updated_at": t["updated_at"],
        }

    @app.post("/api/transfers")
    def api_create(body: NewTransfer, request: Request):
        check_rate(request)
        return _public(_wrap(svc.create_transfer, body.payee_id, body.amount, body.statement))

    @app.post("/api/transfers/{tid}/answers")
    def api_answers(tid: str, body: Answers, request: Request):
        check_rate(request)
        return _public(_wrap(svc.answer_questions, tid, body.answers))

    @app.post("/api/transfers/{tid}/order")
    def api_order(tid: str):
        t = _wrap(svc.start_payment, tid)
        return {"order_id": t["order_id"], "transfer": _public(t)}

    @app.post("/api/transfers/{tid}/approved")
    def api_approved(tid: str):
        return _public(_wrap(svc.payer_approved, tid))

    @app.post("/api/transfers/{tid}/cancel")
    def api_cancel(tid: str):
        return _public(_wrap(svc.payer_cancel, tid))

    @app.get("/api/transfers/{tid}")
    def api_get(tid: str):
        t = svc.store.get_transfer(tid)
        if not t:
            raise HTTPException(404, "not found")
        return _public(t)

    @app.post("/api/intent")
    def api_intent(body: IntentRequest):
        """Best-effort parse of a spoken request: 'Send 200 to Rahul for his books'."""
        text = body.text
        amount = None
        m = re.search(r"(\d[\d,]*(?:\.\d{1,2})?)", text)
        if m:
            amount = float(m.group(1).replace(",", ""))
        payee = None
        for p in svc.store.list_payees():
            first = p["name"].split()[0]
            if re.search(rf"\b{re.escape(first)}\b", text, re.IGNORECASE):
                payee = p
                break
        return {"amount": amount, "payee": payee, "statement": text}

    # -- API: family ----------------------------------------------------------

    @app.get("/api/family/overview")
    def api_family(request: Request):
        require_family(request)
        transfers = [_public(t) for t in svc.store.list_transfers(50)]
        return {
            "pending": [t for t in transfers if t["status"] == "held"],
            "recent": [t for t in transfers if t["status"] != "held"][:20],
            "events": svc.store.events(limit=60),
        }

    @app.post("/api/transfers/{tid}/family")
    def api_family_decide(tid: str, body: FamilyDecision, request: Request):
        require_family(request)
        return _public(_wrap(svc.family_decide, tid, body.approve, body.note))

    # -- API: setup -----------------------------------------------------------

    @app.get("/api/payees")
    def api_payees():
        return svc.store.list_payees()

    @app.post("/api/payees")
    def api_add_payee(body: NewPayee, request: Request):
        if body.known or body.blocked:  # the payer can add someone new, but only family can vouch for them
            require_family(request)
        return svc.store.add_payee(body.name, body.email, body.relationship, body.known, body.blocked)

    @app.patch("/api/payees/{pid}")
    def api_update_payee(pid: str, body: PayeeUpdate, request: Request):
        require_family(request)
        svc.store.update_payee(pid, **body.model_dump(exclude_none=True))
        return svc.store.get_payee(pid)

    @app.post("/api/tick")
    def api_tick():
        return {"released": svc.tick()}

    @app.get("/api/status")
    def api_status():
        a = svc.engine.assessor
        out = {
            "paypal": "sandbox" if svc.paypal.live else "demo (no PayPal keys)",
            "engine": svc.engine.config.name,
            "ai": ai_mode(),
            "cost": "free: no paid APIs",
            "cooling_off_seconds": settings.cooling_off_seconds,
        }
        if a is not None:
            st = a.status()
            out["llm_calls"] = st["calls"]
            out["llm_cache_hits"] = st["cache_hits"]
            if st["quota"]:
                out["llm_tokens_today"] = st["quota"]["tokens_last_day"]
            if st["last_error"]:
                out["llm_last_error"] = st["last_error"]
        return out

    @app.post("/api/demo/reset")
    def api_demo_reset(request: Request):
        """Start the shared demo household fresh. Held PayPal authorisations are voided first."""
        require_family(request)
        check_rate(request)
        for t in svc.store.list_transfers(500):
            if t["status"] == "held":
                try:
                    svc.cancel(t["id"], reason="demo reset")
                except FlowError:
                    pass
        svc.store.reset()
        seed_demo(svc.store)
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/favicon.ico")
    def favicon():
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0f5c55"/>'
            '<rect x="10" y="8" width="4" height="16" rx="2" fill="#fff"/><rect x="18" y="8" width="4" height="16" rx="2" fill="#fff"/></svg>'
        )
        return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})

    # -- PayPal webhooks ------------------------------------------------------
    @app.post("/webhooks/paypal")
    async def paypal_webhook(request: Request):
        try:
            event = await request.json()
        except ValueError:
            return JSONResponse({"error": "body is not valid JSON"}, status_code=400)
        if svc.paypal.live:
            if not settings.paypal_webhook_id:
                return JSONResponse({"error": "PAYPAL_WEBHOOK_ID not set"}, status_code=503)
            try:
                ok = await asyncio.to_thread(svc.paypal.verify_webhook, dict(request.headers), event, settings.paypal_webhook_id)
            except PayPalError:  # PayPal refuses to check a request with missing or malformed signature headers
                ok = False
            if not ok:
                return JSONResponse({"error": "signature verification failed"}, status_code=400)
        svc.handle_webhook(event)
        return {"ok": True}

    return app


def main() -> None:
    import uvicorn

    uvicorn.run("pauseline.app:create_app", factory=True, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
