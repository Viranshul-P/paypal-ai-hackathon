# Deploying Pauseline on Railway

About 15 minutes. You need a Railway account (sign up with GitHub, no card) and these values from the team (sent privately, never committed):

| Name | What it is |
|---|---|
| `PAYPAL_CLIENT_ID` | PayPal sandbox app client id |
| `PAYPAL_CLIENT_SECRET` | PayPal sandbox app secret |
| `PAUSELINE_DEMO_RECIPIENT_EMAIL` | Sandbox *personal* account that receives demo payouts |
| `GROQ_API_KEY` | Groq free-tier API key |
| `PAUSELINE_FAMILY_PIN` | PIN for Family view and Setup. While it is `1234` (the default), the lock screen shows it |
| `PAUSELINE_COOLING_OFF_SECONDS` | `120` for demos |

## 1. Create the service
1. Log in at **railway.com** with GitHub. Check that your account is on the **Full Trial**. A Limited Trial restricts outbound network access, which can block PayPal and Groq.
2. Click **New Project → Deploy from GitHub repo** and pick this repo, branch `main`. Railway reads `Dockerfile` and `railway.json`.

## 2. Add the variables
Under the service's **Variables** tab, add the values above. Then open **Settings → Networking → Generate Domain**, set `PAUSELINE_PUBLIC_URL` to that address (for example `https://pauseline-production.up.railway.app`), and let it redeploy.

## 3. Check it
- The deploy log should end with `Application startup complete`.
- Open `https://<your-site>/health` → `{"ok": true}`.
- Open the home page. The footer should say **PayPal sandbox. AI: on-device ML + gpt-oss-120b (Groq).**
- Go to **Send money**, pay Rahul 80 for "college books", and log in on the PayPal button with the sandbox **payer** account → "Sent".

## 4. Register PayPal webhooks (once you have the URL)
On a computer with the repo and the team's `.env`:

```bash
uv run python scripts/register_webhook.py https://<your-site>
```

It prints `PAYPAL_WEBHOOK_ID=...`. Add that to the Railway variables. PayPal events (authorised, captured, voided, payout) will now appear in **Family view → Activity**.

## Good to know
- **Trial credit:** $5 for up to 30 days. Check usage on the Railway dashboard before judging.
- **Demo data resets on every restart.** There is no persistent disk, which keeps the demo clean. **Setup → Reset demo** also clears it.
- **AI quota:** the site uses Groq's free tier (about 1,000 checks a day) and protects it with a cache, a budget guard and per-visitor limits. If the quota ever runs out, the site keeps working with the on-device ML model, and the footer shows "ML only".
- **Updating:** every push to `main` triggers a new deploy.
- `render.yaml` is kept for anyone who prefers Render's free tier.
