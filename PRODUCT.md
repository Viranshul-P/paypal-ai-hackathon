# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Backend stays FastAPI with its JSON API. Frontend is being rebuilt as React and Tailwind from modular Watermelon UI components, built with Vite and served by FastAPI. Deployed on Railway from a Docker image.

## Users

- **Payer (demo persona Kamla):** an older adult in India paying family, bills and doctors, possibly with a scammer on the phone directing them. Types or speaks in English, Hindi or Hinglish.
- **Trusted contact (demo persona Asha, her daughter):** reviews held payments and approves or declines them.
- **Judges (first priority for this build):** PayPal AI Hackathon panels, watching a 3-minute video and trying the live demo. The UI must make the scam-hold story obvious and look like a real, modern fintech product, while staying readable for older users.

## Product Purpose

Pauseline stops people being talked into sending money to scammers. It checks a payment for scam pressure in the payer's own words and context, holds the money with a PayPal authorisation, and asks a trusted family member before risky payments leave. Success: a scam is held and declined with the payer never charged, while normal payments go straight through.

## Positioning

Conventional fraud checks look for stolen accounts. Pauseline targets authorised push payment scams, where the real owner pays under pressure, and puts a real PayPal hold plus a human family decision between the pressure and the money.

## Operating Context

Payment flow: choose payee, enter amount, say what it is for (voice or text), answer up to two yes/no questions if unsure, approve in PayPal, see the outcome. Outcomes: sent, cooling-off pause, held for family, or blocked. The family view lists holds with the payer's words, warning signs and answers, behind a PIN. PayPal runs in sandbox, so no real money moves.

## Capabilities and Constraints

- Real PayPal Orders v2 AUTHORIZE, capture, void, Payouts and signed webhooks; the PayPal JS button must render inside the payer flow.
- On-device ML classifier, scam-phrase rules and gpt-oss-120b on Groq's free tier, with fallback to on-device ML.
- English and Hindi on the payer screens; browser speech input in Chrome and Edge.
- The backend, benchmark and risk engine must not change as part of UI work.
- Family alerts are in-browser only.
- Currency is USD because of the PayPal sandbox.

## Brand Commitments

Name: Pauseline. Tagline: "A pause before money leaves." The user rejected the previous look as old, plain and boringly coloured.

## Evidence on Hand

Held-out benchmark in `EXPERIMENTS.md`, with the chart at `docs/figures/results-test.png`: 95% of scams caught and 74% held for family, against 56% and 0% for bank-style rules; 17% of legitimate payments flagged and 0% held. The benchmark is synthetic, and this must be stated wherever the numbers are shown. There are no real users, testimonials or customers yet, and none may be invented.

## Product Principles

- Money only moves by a fixed rule or a human decision; AI never moves it.
- The payer is never blamed or scared; warnings are calm and specific.
- Normal payments stay fast. Friction appears only when there is evidence.
- Every hold shows its reasons in plain language.

## Accessibility & Inclusion

Older users: large tap targets, high contrast, plain language, Devanagari that renders as well as Latin, voice as an equal input, and read-aloud of key messages.
