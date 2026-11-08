"""Runtime configuration, read from environment variables (and a local .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DEFAULT_FAMILY_PIN = "1234"  # local demo only; the lock screen shows it while it is in use


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # PayPal. With no client id/secret, Pauseline runs against an in-memory fake PayPal.
    paypal_client_id: str = field(default_factory=lambda: os.getenv("PAYPAL_CLIENT_ID", ""))
    paypal_client_secret: str = field(default_factory=lambda: os.getenv("PAYPAL_CLIENT_SECRET", ""))
    paypal_base_url: str = field(
        default_factory=lambda: os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")
    )
    paypal_webhook_id: str = field(default_factory=lambda: os.getenv("PAYPAL_WEBHOOK_ID", ""))
    # Send captured money on to the recipient with PayPal Payouts. If Payouts is not enabled
    # on the sandbox account, set this to false: the capture itself is then the delivery.
    paypal_use_payouts: bool = field(default_factory=lambda: _bool("PAYPAL_USE_PAYOUTS", True))
    currency: str = field(default_factory=lambda: os.getenv("PAUSELINE_CURRENCY", "USD"))

    # AI, all free. Always on: rules + phrase lexicon + our locally trained ML classifier.
    # LLM layer: Groq's free tier (hosted open-weight gpt-oss-120b) when GROQ_API_KEY is set,
    # or Ollama on your own machine. PAUSELINE_LLM_PROVIDER = auto | groq | ollama | none.
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    llm_provider_setting: str = field(default_factory=lambda: os.getenv("PAUSELINE_LLM_PROVIDER", "auto").lower())
    llm_model: str = field(default_factory=lambda: os.getenv("PAUSELINE_LLM_MODEL", ""))
    llm_base_url: str = field(default_factory=lambda: os.getenv("PAUSELINE_LLM_BASE_URL", ""))
    llm_timeout: float = field(default_factory=lambda: float(os.getenv("PAUSELINE_LLM_TIMEOUT", "12")))
    # Stay under Groq's free-tier limits (measured 7 Nov from response headers: 1,000 requests/day
    # and 8,000 tokens/minute per model).
    llm_rpm: int = field(default_factory=lambda: int(os.getenv("PAUSELINE_LLM_RPM", "25")))
    llm_tpm: int = field(default_factory=lambda: int(os.getenv("PAUSELINE_LLM_TPM", "7000")))
    llm_rpd: int = field(default_factory=lambda: int(os.getenv("PAUSELINE_LLM_RPD", "900")))
    llm_tpd: int = field(default_factory=lambda: int(os.getenv("PAUSELINE_LLM_TPD", "400000")))
    llm_cache_path: Path = field(
        default_factory=lambda: Path(os.getenv("PAUSELINE_LLM_CACHE", str(ROOT / "data" / "llm_cache.db")))
    )
    # Public site protection: payment checks per visitor per minute.
    assess_per_minute: int = field(default_factory=lambda: int(os.getenv("PAUSELINE_ASSESS_PER_MINUTE", "8")))

    # The trusted contact's PIN. It guards family decisions and setup, so that someone directing the
    # payer over the phone cannot have them approve their own held payment.
    family_pin: str = field(default_factory=lambda: os.getenv("PAUSELINE_FAMILY_PIN", "") or DEFAULT_FAMILY_PIN)

    # Policy
    cooling_off_seconds: int = field(
        default_factory=lambda: int(os.getenv("PAUSELINE_COOLING_OFF_SECONDS", str(24 * 3600)))
    )
    db_path: Path = field(
        default_factory=lambda: Path(os.getenv("PAUSELINE_DB", str(ROOT / "pauseline.db")))
    )
    public_base_url: str = field(
        default_factory=lambda: os.getenv("PAUSELINE_PUBLIC_URL", "http://127.0.0.1:8000")
    )

    @property
    def family_pin_is_default(self) -> bool:
        return self.family_pin == DEFAULT_FAMILY_PIN

    @property
    def llm_provider(self) -> str:
        p = self.llm_provider_setting
        if p == "auto":
            return "groq" if self.groq_api_key else "none"
        if p == "groq" and not self.groq_api_key:
            return "none"
        return p if p in {"groq", "ollama", "none"} else "none"

    @property
    def paypal_live(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_client_secret)


def get_settings() -> Settings:
    return Settings()
