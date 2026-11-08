---
version: 1
slug: "frontend-src-app-tsx"
primary_target: "frontend/src/App.tsx"
related_targets: []
---

Scope: the whole Pauseline web app (home, send flow, outcome, family, setup). Mode: operate.
Audience and job: judges watching the demo first; older payers and their family contact completing a payment or a decision.
Constraints: backend, PayPal flow, family PIN and benchmark unchanged. PayPal button must render in the flow. English and Hindi on payer screens.
Unresolved: real family alerts need email credentials.

## Direction contract

THESIS: A payment app that feels kind, and stops you gently. It refuses the grey fintech dashboard and the scary red warning screen.

OWN-WORLD: Warm peach ground (#FFEFE2), white soft cards at large radii, cocoa ink (#2B1A12), Baloo 2 for Latin and Devanagari. Deep orange (#D0400A) appears only on things you can press. State colours carry meaning only: amber held, green sent, red stopped.

STORY: Kamla pays as usual. If something is wrong, the screen changes once, tells her calmly why, and her money stays put. Asha sees exactly why and decides.

FIRST VIEWPORT: Phone-width column on peach with brand top left, one big heading, the payment in a white card, the reason in a second card, one orange button, a quiet secondary button, and a bottom tab bar. On laptop the phone column sits beside a live story rail naming the current step. Family view is full-width: decisions lead, recent payments and activity alongside.

FORM: Friendly Wallet, warm consumer app surface, challenger chosen by the user. seed:bece3195e62f703d. Raises: from Vertical Feed, a held payment owns the whole phone screen. From Datamatics, one full-screen colour change marks the hold and nothing else animates on its own. From Boarding Pass, a new hold stays lit in the family view until it is acted on. From Timetable Slide Rack, payment states use one fixed vocabulary in one fixed position.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
