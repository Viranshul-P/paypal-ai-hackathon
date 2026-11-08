# Pauseline: plan and status

> One project for **Threws Odyssey 2026** (track: **Cybersecurity**, since FinTech is missing from the form) and the **PayPal AI Hackathon** (targets: Grand Prize, **Most Impactful**, Best Use of PayPal + AI).
> Deadlines: Threws **12 Nov, 11:00 PM IST**; PayPal **13 Nov, 1:30 AM IST**. Threws Round 2: **15 Nov, 11 AM IST**.

## The idea in one paragraph

Scammers now talk people into sending money themselves: a "bank officer" with a safe account, "digital arrest" video calls, a grandchild in trouble. Fraud checks miss this because the real owner is paying. **Pauseline** checks each payment for scam pressure in the payer's own words (English/Hindi/Hinglish) and in its context, and asks one or two yes/no questions when unsure. **Every payment is held as a PayPal authorisation**: normal ones are captured and paid out at once; risky ones wait for a cooling-off period or for a **trusted family member**, who approves (capture + payout) or declines (void, never charged). No AI can move money on its own. **Total cost: $0.**

## Status (7 Nov, evening): development complete

| Area | Status |
|---|---|
| PayPal: Orders v2 AUTHORIZE, capture, void, Payouts, webhooks, idempotency | ✅ Verified on the real sandbox (end-to-end payment + payout) |
| Risk engine: rules, en/hi/Hinglish lexicon, 8 questions, two-tier policy | ✅ |
| Our ML classifier (TF-IDF + logistic regression, decontaminated training data) | ✅ |
| LLM layer: gpt-oss-120b on Groq's free tier, cache, quota guard, fallback | ✅ Live-tested |
| Web app: payer screens (voice, Hindi), family dashboard, setup, demo reset | ✅ |
| Benchmark: 112 scenarios, 8 conditions, 3 LLMs, sweeps, speech-noise robustness | ✅ Final test results in EXPERIMENTS.md |
| Tests | ✅ 35 passing |
| Deployment | ✅ Live on Railway: https://pauseline-production.up.railway.app |
| Submission kit (Devpost + Unstop text, video script) | ✅ docs/SUBMISSION.md |

**Headline result (held-out test split):**
- Pauseline catches **95%** of scams and holds **74%** for the family, against 56% and 0% for bank-style rules.
- **No legitimate payment is held.**
- 95% are still caught with speech-recognition noise.
- Every Hindi and Hinglish scam is caught.

## Remaining (team)

| # | Task | Who | By |
|---|---|---|---|
| 1 | ~~`git push` the `pauseline` branch, then merge it into `main`~~ Done | Viranshul | done |
| 2 | Rotate the PayPal secret and Groq key, then make the repo public | Viranshul | 8 Nov |
| 3 | ~~Deploy on Railway and register webhooks~~ Done | Kuldeep | done |
| 4 | ~~Put the live URL in README.md and docs/SUBMISSION.md~~ Done | Kuldeep | done |
| 5 | Talk to 3–5 families about scam calls; add 2–3 quotes to the README and the deck | Everyone | 10 Nov |
| 6 | A Hindi speaker checks the Hindi/Hinglish sentences in `eval/scenarios/build_v1.py` and `src/pauseline/risk/training_data.py` | Kuldeep | 10 Nov |
| 7 | Confirm the headline statistics on the primary pages (ic3.gov, PIB) | Anyone | 10 Nov |
| 8 | Record the video (script in docs/SUBMISSION.md) on the live site; upload to YouTube as public | Everyone | 11 Nov |
| 9 | Submit: Threws on Unstop (Cybersecurity track), then Devpost (teammates added; test credentials in the private field) | Viranshul | 12 Nov |
| 10 | Round 2 deck and rehearsal (problem → demo → results chart → method → limits) | Everyone | 13–14 Nov |

## Cost: zero

- **AI:** our scikit-learn model, plus Groq's free tier: about 1,000 requests/day and 8,000 tokens/min per model, guarded and cached.
- **PayPal:** free sandbox.
- **Hosting:** Railway trial credit ($5, no card).
- **Video:** YouTube.
- **Speech:** the browser's built-in Web Speech API.

## Notes for the presentation

- **Precedents for the design:**
  - US brokers must ask customers for a "trusted contact person" (FINRA Rule 4512);
  - the UK's authorised push payment scam reimbursement rules (PSR, from Oct 2024) make payment firms liable;
  - Indian banks limit first transfers to new beneficiaries.

  Verify the wording before citing.
- **Honest limits:**
  - synthetic benchmark;
  - one documented re-tuning after the first test run;
  - coached victims with bland wording are the residual misses;
  - the free LLM quota caps daily volume, with a working fallback.
