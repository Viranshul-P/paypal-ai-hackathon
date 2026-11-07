"""Register Pauseline's PayPal webhook (sandbox) once the site has a public HTTPS URL.

    uv run python scripts/register_webhook.py https://pauseline.onrender.com

Prints the webhook id: put it in PAYPAL_WEBHOOK_ID (Render dashboard and .env) so incoming
events are signature-verified.
"""

from __future__ import annotations

import sys

from pauseline.config import get_settings
from pauseline.paypal.client import PayPalClient, PayPalError

EVENTS = [
    "CHECKOUT.ORDER.APPROVED",
    "PAYMENT.AUTHORIZATION.CREATED",
    "PAYMENT.AUTHORIZATION.VOIDED",
    "PAYMENT.CAPTURE.COMPLETED",
    "PAYMENT.CAPTURE.DENIED",
    "PAYMENT.PAYOUTS-ITEM.SUCCEEDED",
    "PAYMENT.PAYOUTS-ITEM.FAILED",
]


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].startswith("https://"):
        sys.exit("usage: register_webhook.py https://your-site")
    url = sys.argv[1].rstrip("/") + "/webhooks/paypal"
    s = get_settings()
    pp = PayPalClient(s.paypal_client_id, s.paypal_client_secret, s.paypal_base_url)
    try:
        body = pp._request("POST", "/v1/notifications/webhooks", json={"url": url, "event_types": [{"name": e} for e in EVENTS]})
    except PayPalError as e:
        sys.exit(f"PayPal refused: {e} (debug id {e.debug_id})")
    print(f"registered {url}\nPAYPAL_WEBHOOK_ID={body['id']}")


if __name__ == "__main__":
    main()
