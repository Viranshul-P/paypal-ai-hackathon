# Deploying Pauseline on Render (free)

About 15 minutes. You need: a Render account (free), the GitHub repo **public**, and these values from the team (sent privately, never committed):

| Name | What it is |
|---|---|
| `PAYPAL_CLIENT_ID` | PayPal sandbox app client id |
| `PAYPAL_CLIENT_SECRET` | PayPal sandbox app secret |
| `PAUSELINE_DEMO_RECIPIENT_EMAIL` | Sandbox *personal* account that receives demo payouts |
| `GROQ_API_KEY` | Groq free-tier API key |

## 1. Create the service
1. Log in at **render.com** (signing up with GitHub is easiest).
2. Click **New → Blueprint**.
3. Choose **Public Git repository** and paste the repo URL. Or, if the repo is under your account, connect GitHub and pick it.
4. Render reads `render.yaml` and shows one web service called **pauseline** on the **Free** plan. Click **Apply**.

## 2. Add the secrets
When Render asks for the values marked `sync: false`, or later under **pauseline → Environment**, fill in:

- `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAUSELINE_DEMO_RECIPIENT_EMAIL`, `GROQ_API_KEY`: from the team.
- `PAUSELINE_PUBLIC_URL`: the site's address, e.g. `https://pauseline.onrender.com`. You'll see it at the top of the service page after the first deploy.
- `PAYPAL_WEBHOOK_ID`: leave empty for now (step 4).

Click **Save, rebuild and deploy**.

## 3. Check it
- The build log should end with `classifier ready in ...` and then `Application startup complete`.
- Open `https://<your-site>/health` → `{"ok": true}`.
- Open the home page. The header should say **PayPal: sandbox · AI: on-device ML + gpt-oss-120b (Groq)**.
- Go to **Send money**, pay Rahul 80 for "college books", and log in on the PayPal button with the sandbox **payer** account → "Done".

## 4. Register PayPal webhooks (once you have the URL)
On a computer with the repo and the team's `.env`:

```bash
uv run python scripts/register_webhook.py https://<your-site>
```

It prints `PAYPAL_WEBHOOK_ID=...`. Put that value in Render → Environment, then save and redeploy. PayPal events (authorised, captured, voided, payout) will now appear in **Family view → Activity**.

## Good to know
- **The free tier sleeps after 15 minutes idle.** The first visit then takes about 50 seconds. Open the site a minute before a demo or judging session.
- **Demo data resets on every restart.** The free plan has no disk, which keeps the demo clean. Judges can also click **Setup → Reset demo**.
- **AI quota:** the site uses Groq's free tier (about 1,000 checks a day) and protects it with a cache, a budget guard and per-visitor limits. If the quota ever runs out, the site keeps working with the on-device ML model, and the header shows "ML only".
- **Updating:** every push to the branch Render deploys from triggers a new deploy automatically.
