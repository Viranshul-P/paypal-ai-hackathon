"""Core data types shared by the risk engine, the service layer and the evaluation harness."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Decision(str, Enum):
    """What happens to a payment after PayPal has authorised (held) the funds."""

    ALLOW = "allow"  # capture now
    COOL_OFF = "cool_off"  # family is told; released automatically after the cooling-off period unless declined
    HOLD_FOR_FAMILY = "hold_for_family"  # released only if the trusted contact approves
    BLOCK = "block"  # void the authorisation (payee is on the block list)

    @property
    def intervenes(self) -> bool:
        return self is not Decision.ALLOW


class TransferStatus(str, Enum):
    DRAFT = "draft"  # created, being assessed, questions may be pending
    AWAITING_PAYER = "awaiting_payer"  # PayPal order created, payer has not approved yet
    HELD = "held"  # authorised by PayPal, waiting on family or cooling-off
    RELEASED = "released"  # captured (and paid out)
    CANCELLED = "cancelled"  # authorisation voided
    FAILED = "failed"


ScamType = Literal[
    "none",
    "bank_safe_account",
    "digital_arrest_or_government",
    "family_emergency",
    "tech_support",
    "romance",
    "prize_or_lottery",
    "investment_or_crypto",
    "fake_invoice_or_refund",
    "job_or_task",
    "other",
]

SCAM_TYPES: tuple[str, ...] = ScamType.__args__  # type: ignore[attr-defined]


class Payee(BaseModel):
    name: str
    email: str = ""
    known: bool = False  # in the payer's trusted payee list
    relationship: str = ""  # e.g. "grandson", "electricity company"
    blocked: bool = False


class PaymentContext(BaseModel):
    """Everything the risk engine may look at for one payment request."""

    statement: str = Field(description="What the payer said or typed about the payment, in their own words")
    amount: float
    currency: str = "USD"
    payee: Payee
    history_median: float | None = Field(
        default=None, description="Median of the payer's past payment amounts, if any"
    )
    recent_count_1h: int = 0  # payments made in the last hour
    hour_of_day: int | None = None  # local time, 0-23
    answers: dict[str, str] = Field(default_factory=dict)  # question id -> "yes" / "no"


class Signal(BaseModel):
    name: str
    weight: float
    evidence: str = ""


class Assessment(BaseModel):
    risk: float  # 0..1
    decision: Decision
    scam_type: str = "none"
    signals: list[Signal] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)  # question ids to ask the payer
    message_to_payer: str = ""
    summary_for_family: str = ""
    assessor: str = ""  # which components produced this
    llm_risk: float | None = None
    ml_proba: float | None = None
    rule_risk: float | None = None
    latency_ms: float | None = None
