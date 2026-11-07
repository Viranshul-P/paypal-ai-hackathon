# Submission kit

Ready-to-paste text for both hackathons. Replace every `TODO` (live URL, video link) before submitting.

**Headline statistics (secondary sources; confirm on the primary pages before quoting):**
- **US:** people aged 60+ reported about **$7.75 billion** in losses to the FBI's Internet Crime Complaint Center in 2025, up 59% on 2024 (FBI IC3 2025 report, as summarised by [HousingWire](https://www.housingwire.com/articles/fbi-seniors-cybercrime-2025/)). Primary: [ic3.gov](https://www.ic3.gov).
- **India:** **₹1,935 crore** was lost to "digital arrest" scams in 2024, per a government statement to Parliament ([Inc42](https://inc42.com/?p=504907)); I4C counted ₹120 crore in January–April 2024 alone ([Business Standard](https://business-standard.com/india-news/indians-lose-over-rs-120-cr-in-digital-arrest-frauds-pm-modi-cautions-risk-124102800276_1.html)). Primary: PIB / [cybercrime.gov.in](https://cybercrime.gov.in).

---

## Shared facts

- **Name:** Pauseline
- **Tagline:** A pause before money leaves. Scam-aware PayPal payments with a trusted family contact.
- **Live demo:** TODO (Render URL)
- **Repo:** https://github.com/Viranshul-P/threws-odyssey-2026 (public, MIT)
- **Video:** TODO (YouTube, under 3 minutes)
- **Team:** Viranshul, Priyanshu Doshi, Kuldeep Goklani (Team Beyonders)

### Test access for judges
- The live site needs no login.
- On the PayPal button, log in with the sandbox payer account. The email and password are in the private submission field, not in the repo.
- **Family view** is at `/family`. **Setup → Reset demo** clears the shared household.

---

## Devpost (PayPal AI Hackathon)

**Inspiration**
Scams have changed. Criminals no longer need your password: they phone, pose as your bank, the police or a grandchild, and talk you into sending the money yourself. In India these "digital arrest" calls keep someone on a video call for hours until they pay. Fraud checks look for stolen accounts, but here the real owner is paying, so the money goes through. We wanted a pause between the pressure and the payment, and a way for families to help without taking away anyone's independence.

**What it does**
- Pauseline is a payment app with a safety net built on PayPal.
- The payer picks who to pay and says what it's for, by typing or speaking in English, Hindi or Hinglish.
- Pauseline checks for scam pressure in their own words and in the payment's context. When unsure, it asks one or two yes/no questions, such as "Is someone on the phone with you right now, telling you what to do?"
- **Every payment is first held as a PayPal authorisation:**
  - normal payments are captured at once and paid out to the recipient;
  - unusual ones get a cooling-off period, and the family member is told;
  - payments with clear warning signs wait for a **trusted family member**, who sees the payer's words, the warning signs and the answers, then approves (capture + payout) or declines (void).
- A declined payment never charges the payer.

**How we built it**
- **PayPal:**
  - Orders v2 with `intent: AUTHORIZE` and the JS SDK button;
  - Payments v2 authorise, capture and void;
  - Payouts to deliver funds;
  - webhooks with signature verification;
  - `PayPal-Request-Id` so retries never double-charge.
- **AI, all free:**
  1. **Our own ML classifier**: TF-IDF over words and character n-grams, plus logistic regression. Trained on 2,800 synthetic English, Hindi and Hinglish sentences, decontaminated against our benchmark, and explaining each decision with the phrases that drove it.
  2. **An English/Hindi scam-phrase lexicon and context rules.**
  3. **An open-weight LLM** (gpt-oss-120b on Groq's free tier). It writes the calm message to the payer and the summary for the family, and suggests the best questions.
- **Safety principle:** every AI component can only add caution. Money moves only through deterministic policy or a human.
- **Built for a free public quota:** response caching, a token/request budget guard, per-visitor rate limits, and automatic fallback to the on-device model.
- **Stack:** FastAPI, SQLite, vanilla JS. Hosted on Render.

**Challenges**
- LLMs flag large payments to new payees as scams: tuition, contractors, hospital deposits. We calibrated the LLM's weight on a dev split and introduced two tiers: unusual context alone can only cool off, while a hold needs warning signs in the words or a risky answer.
- Our first training set leaked phrases from our test set. A leakage check caught it, and we added decontamination.

**Accomplishments**
- A complete hold → decide → capture/void → payout flow on real PayPal sandbox APIs.
- A 112-scenario benchmark with coached victims who lie, as scammers instruct.
- On a held-out test set: Pauseline catches **95% of scams** and holds **74% for the family**, against 56% and 0% for bank-style rules. **No legitimate payment was held.** With 15% speech-recognition noise it still catches 95%. Every Hindi and Hinglish scam was caught.

**What we learned**
- Classic bank rules can delay a payment but can't tell a scam from a big legitimate payment. The payer's words carry that signal.
- Asking questions helps, but coached victims answer "no". Families are the real safety net.

**What's next**
- A partnership with a wallet or bank to run it in the real payment flow.
- Periodic family review of recurring payees.
- More Indian languages.
- Whisper-based voice input.

**Built with:** paypal-orders-v2, paypal-payments, paypal-payouts, paypal-webhooks, paypal-js-sdk, python, fastapi, scikit-learn, groq, gpt-oss, sqlite, javascript, web-speech-api, render

**AI tools used:**
- In the product: our scikit-learn classifier; gpt-oss-120b via Groq (risk second opinion, messages, question choice).
- To build it: Claude Code (code, research, documentation, drafting benchmark scenarios, all reviewed by the team).

---

## Unstop (Threws Odyssey), track: Cybersecurity

**Problem statement**
Authorised push payment scams, such as fake bank "safe accounts", "digital arrest" video calls and fake family emergencies, trick the account owner into sending money themselves. Because the owner authenticates and approves, conventional fraud detection (which looks for unauthorised access) lets the payment through. The victims are often older adults, and families find out after the money is gone.

**Proposed solution**
Pauseline puts a pause between social-engineering pressure and the payment:
1. It detects scam pressure from the payer's own words plus the payment context.
2. When uncertain, it asks targeted yes/no questions.
3. It holds every payment as a PayPal authorisation.
4. It escalates risky ones to a trusted family member, who approves or declines before any money moves.

**Key features**
- A two-tier hold: a cooling-off period, or a family decision.
- Voice input in English, Hindi and Hinglish.
- A family dashboard showing the evidence.
- Explainable AI: the phrases behind each decision.
- A deployed, free, real PayPal sandbox integration.

**Technology stack:** Python, FastAPI, scikit-learn, Groq (gpt-oss-120b, open-weight), PayPal REST APIs (Orders, Payments, Payouts, Webhooks), SQLite, JavaScript, Web Speech API, Render.

**Research and experimentation (summary)**
- **Benchmark:** 112 synthetic scenarios with 9 scam types; 10 coached victims; hard legitimate cases; English, Hindi and Hinglish.
- **Method:**
  - 8 conditions, from bank-style rules to the full system;
  - a dev/test split with all tuning on dev;
  - leakage control between training and test data;
  - speech-recognition noise robustness.
- **Results (held-out test split, 75 scenarios):**
  - **Bank-style rules:** catch 56% of scams, hold 0% for the family, flag 39% of legitimate payments.
  - **Pauseline:** catches **95%** (95% CI 83–99%), holds **74%**, flags 17% of legitimate payments (all only delayed), and **holds 0%** of them.
  - Coached victims: 71% caught.
  - Hindi and Hinglish scams: 100% caught.
  - 15% speech-recognition noise: 95% still caught.
  - Our ML model alone: 0% false alarms.
  - LLM comparison: gpt-oss-120b vs gpt-oss-20b vs Qwen 3.8 27B on dev.
  - One documented re-tuning (on dev) after the first test run, with both results reported.

**Dataset and external resources:**
- the synthetic benchmark (in the repo);
- public scam typologies from the [FBI IC3](https://www.ic3.gov), the [US FTC](https://reportfraud.ftc.gov) and Indian advisories on "digital arrest" (CERT-In; [cybercrime.gov.in](https://cybercrime.gov.in));
- PayPal sandbox;
- Groq free tier.

---

## Video script (under 3 minutes; record on the live site)

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | Home page | "Scammers don't steal passwords any more. They call, pretend to be your bank or the police, and talk you into paying yourself. Banks can't tell, because it really is you paying. In India, people lost ₹1,935 crore to 'digital arrest' scams in 2024 alone." |
| 0:20–0:45 | Send money → Rahul, 80, "college books" (voice) | "Kamla pays her grandson as usual. Pauseline sees nothing wrong, so PayPal captures it and pays Rahul at once." Show the sandbox capture and payout |
| 0:45–1:45 | Send money → "Safe Account Services", 3000, the bank-officer script | "Now Kamla has a 'bank officer' on the phone." Show the question card and the hold message being read aloud. Switch to Family view: "Asha, her daughter, sees exactly why: Kamla's words, the warning signs, her answers." Decline. Show the sandbox authorisation voided: "The money never left. Kamla was never charged." |
| 1:45–2:25 | EXPERIMENTS charts | "We tested 8 detector designs on 112 scenarios, including victims coached to lie. Bank-style rules catch 56% of scams and never hold one for the family. Pauseline catches 95%, holds 74% for the family, and holds zero legitimate payments, even with speech-recognition errors." Show `docs/figures/results-test.png` |
| 2:25–3:00 | Architecture diagram | "The AI only adds caution. Money moves only by rule or by family. Free, on PayPal, and built to plug into any wallet." |
