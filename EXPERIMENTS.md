# Experiments

Keep this log honest and dated. Record every run you cite, every change you made after looking at results, and what failed. **All numbers here must come from real runs** in `eval/results/` (Threws disqualifies fabricated results). Everything here is free to run on a laptop.

## Research questions

1. **RQ1. Detection:** can scam pressure be detected from the payer's *own words* plus payment context, better than the context rules banks already use, without bothering people on normal payments?
2. **RQ2. Clarifying questions:** does asking one or two yes/no questions before money leaves help? How much, when the victim has been coached to lie?
3. **RQ3. Generalisation and robustness:** does a classifier trained only on template-generated scam scripts generalise to independently written requests, and to Hindi, Hinglish and speech-recognition errors?

## Data

**Benchmark v1** (`eval/scenarios/build_v1.py` → `v1.jsonl`, sha256 in `MANIFEST.json`):
- 112 hand-written scenarios: 58 scams, 54 legitimate.
- 9 scam types, following public descriptions from:
  - the [FBI IC3](https://www.ic3.gov)
  - the [US FTC](https://reportfraud.ftc.gov)
  - Indian government "digital arrest" advisories (CERT-In; [cybercrime.gov.in](https://cybercrime.gov.in))
- **Hard cases on purpose:**
  - 10 *coached* victims who give the reassuring answer to every question;
  - repeat payments to a scammer already saved as a payee;
  - small-fee scams (parcel, toll texts);
  - legitimate payments that look scary.
- Languages: 80 English, 20 Hinglish, 12 Hindi.
- **Splits:** 37 dev and 75 test. **Tune only on dev; run test once per frozen configuration.**
- **Simulated payer:** answers to questions follow each scenario's ground truth. Coached victims answer every question reassuringly.

**Classifier training data** (`src/pauseline/risk/training_data.py`):
- 2,806 sentences after decontamination, from templates and phrase lists (about 1,500 scam, 1,300 benign; English, Hinglish, Hindi). Seeded and deterministic.
- **Decontamination:** generated sentences with character n-gram cosine ≥ 0.8 to any benchmark statement are dropped (25 removed). `eval/check_leakage.py`: 0 exact duplicates, mean nearest-match similarity 0.49.
- **Leakage found and fixed (7 Nov):** the first check found 7 exact copies and 20 near-duplicates, because both sets were written in the same session. We rephrased the copied training phrases and added the decontamination step. This happened before any test-split run.

## Conditions (all free)

| Id | Context rules | Lexicon | ML classifier | Questions | LLM |
|---|---|---|---|---|---|
| A_rules_context (classic bank rules) | ✓ | | | | |
| B_rules_lexicon | ✓ | ✓ | | | |
| C_ml_text_only | | | ✓ | | |
| D_rules_lexicon_ml | ✓ | ✓ | ✓ | | |
| **F_pauseline** | ✓ | ✓ | ✓ | ✓ | |
| G_rules_plus_questions | ✓ | ✓ | | ✓ | |
| L_llm_only | | | | | ✓ |
| **M_pauseline_full** (deployed) | ✓ | ✓ | ✓ | ✓ | ✓ |

The LLM is an open-weight model on Groq's free tier: **gpt-oss-120b** by default; we also compare gpt-oss-20b and Qwen 3.8 27B. It runs with temperature 0 and a JSON response, and its answers are cached by request hash, so re-runs and sweeps cost no quota. Measured free limits (Groq response headers, 7 Nov): 1,000 requests/day and 8,000 tokens/min per model. One payment check uses about 1,000 tokens.

How the decision is made:
- risk ≥ 0.40 → cooling-off;
- risk ≥ 0.70 → hold for the family member;
- context-only risk is capped, except in A: at 0.69 without the LLM (context alone can at most cool off, never hold), and at 0.35 with the LLM (context alone only triggers questions). Both values were chosen on dev; see the methodology note under the final results;
- a blocked payee → block.

## Metrics

- **Scam recall:** share of scams where Pauseline intervened (cooling-off, hold or block). 95% Wilson CI.
- **False alarms:** share of legitimate payments where it intervened.
- **Hard-stop recall / hard-stop false alarms:** the same, counting only holds and blocks. A cooling-off false alarm costs a delay; a hard-stop false alarm needs a human.
- Coached-victim recall, recall per scam type and per language, share of legitimate payments that got questions.

Prevalence note: scams are about half of this benchmark but rare in real payments, so read the false-alarm rate per 100 legitimate payments.

## Log

### 2026-11-07: free conditions, dev split (run `free-dev-v3`)

`uv run python eval/run.py --split dev --out free-dev-v3`

| Condition | Scam recall (95% CI) | False alarms (95% CI) | Hard-stop recall | Hard-stop false alarms | Coached recall |
|---|---|---|---|---|---|
| A_rules_context | 0.74 (0.51–0.88) | 0.17 (0.06–0.39) | 0.00 | 0.00 | 0.67 |
| B_rules_lexicon | 0.90 (0.69–0.97) | 0.17 (0.06–0.39) | 0.10 | 0.00 | 0.67 |
| C_ml_text_only | 0.58 (0.36–0.77) | 0.06 (0.01–0.26) | 0.32 | 0.00 | 0.00 |
| D_rules_lexicon_ml | 0.95 (0.75–0.99) | 0.28 (0.12–0.51) | 0.68 | 0.00 | 0.67 |
| **F_pauseline** | 0.95 (0.75–0.99) | 0.28 (0.12–0.51) | 0.63 | 0.00 | 0.67 |
| G_rules_plus_questions | 0.90 (0.69–0.97) | 0.17 (0.06–0.39) | 0.42 | 0.00 | 0.67 |

**What we learned (dev only; 19 scams and 18 legitimate payments, so the intervals are wide)**
- Classic bank rules (A) catch 74% of scams but **never hold one for the family** (hard-stop recall 0.00). They can only cool off.
- Language evidence is what turns a delay into a hold: lexicon + ML (D) reach **hard-stop recall 0.68**.
- **No legitimate payment was hard-stopped in any condition.** Every false alarm is a cooling-off.
- The ML model alone (C) is precise (6% false alarms) but misses scams with bland wording. It is strongest combined with rules.
- Questions (F vs D) left recall unchanged and slightly lowered hard-stop recall (0.68 → 0.63). Coached victims' reassuring answers lower the risk a little, which is the realistic cost of asking. Benign payments that got questions: 44%. **Open issue:** questions are asked too often. Raise the ask threshold or ask only when language evidence is present, and measure that on dev.
- Hinglish dev recall is 0.50 for the rule conditions (2 scenarios). Check this on test.

**Tuning done on dev (in order)**
1. Added a context cap after seeing false alarms on tuition, a contractor and a dentist (large payments to new payees, nothing in the words). The sweep (`eval/sweep.py`) showed:

   | Context cap | Scam recall | False alarms | Hard-stop false alarms | Coached recall |
   |---|---|---|---|---|
   | 0.35 | 0.79 | 0.11 | 0.00 | 0.00 |
   | 0.45 | 0.84 | 0.17 | 0.00 | 0.00 |
   | 0.69 | 0.95 | 0.28 | 0.00 | 0.67 |

   A low cap drops coached victims to 0, because for them context is the only evidence. We chose **0.69: context alone can cool off but never hold**. A cooling-off false alarm costs a delay; a missed coached victim costs their savings.
2. Added legitimate refund sentences to the classifier's training data (wording different from the benchmark). The model had learned "refund" = scam after decontamination removed the only legitimate example.

**Speech-recognition noise (dev, `--perturb asr:0.15` and `asr:0.30`):** F_pauseline recall 0.95 at both noise levels, false alarms 0.22. Character n-grams and lowercase-insensitive patterns hold up; homophones such as "save account" are handled by the other signals.

**Known misses**
- `v1-054`, "Monthly payment.": a coached victim paying a romance scammer they already saved. There's nothing in the words or the context. This is a structural limitation; the honest fix is a periodic family review of recurring payees.

### 2026-11-07: LLM layer, dev split (runs `llm-dev-gptoss120b`, `eval/sweep_llm.py`)

`uv run python eval/run.py --split dev --llm --conditions L_llm_only,M_pauseline_full`

| Condition | Scam recall (95% CI) | False alarms (95% CI) | Hard-stop recall | Hard-stop false alarms | Coached recall | Benign asked questions |
|---|---|---|---|---|---|---|
| F_pauseline (no LLM, from `free-dev-v3`) | 0.95 (0.75–0.99) | 0.28 (0.12–0.51) | 0.63 | 0.00 | 0.67 | 0.28 |
| L_llm_only (gpt-oss-120b) | 0.90 (0.69–0.97) | 0.22 (0.09–0.45) | 0.90 | 0.00 | 0.33 | 0.00 |
| **M_pauseline_full** (gpt-oss-120b) | 0.95 (0.75–0.99) | **0.17** (0.06–0.39) | **0.79** | 0.00 | 0.67 | 0.61 |

**What we learned**
- Adding the LLM to the ML + rules engine **cuts false alarms (0.28 → 0.17) and raises hard-stop recall (0.63 → 0.79)**, with still no legitimate payment held.
- On its own the LLM holds many scams, but it misses 2 of 3 coached victims. The combination keeps what each part is good at.
- In a quick check on 4 payments, all three Groq models over-flagged a legitimate tuition payment (risk 0.60–0.85). The fix is not to down-weight the LLM:
  - the calibration sweep (floor / max weight) showed every stricter mapping *lost* recall and coached victims, and none reduced false alarms;
  - the questions do the correcting: after reassuring answers, the LLM re-assesses with the answers in context and lowers its score.

  **The default remains the raw LLM score.**
- **Question policy trade-off:** a "strict" policy (the LLM's suspicion alone doesn't trigger questions) halves how often legitimate payments get questions (0.61 → 0.33), but raises false alarms (0.17 → 0.28). Two yes/no taps cost less than a cooling-off delay plus a family alert, so we keep the "evidence" policy. **Questions are the cheap friction that prevents the expensive friction.**
- The calibration sweep and the policy comparison used 0 new API calls (591 cache hits).

### 2026-11-07: model comparison, dev split (runs `llm-dev-*`)

The full engine (M) with each free Groq model:

| Model | Scam recall | False alarms | Hard-stop recall | Hard-stop false alarms | Coached recall |
|---|---|---|---|---|---|
| **gpt-oss-120b** | 0.95 | **0.17** | 0.79 | 0.00 | **0.67** |
| gpt-oss-20b | 0.95 | 0.28 | 0.79 | 0.00 | 0.67 |
| Qwen 3.8 27B | 0.90 | 0.22 | 0.90 | 0.00 | 0.33 |

**Chosen: gpt-oss-120b.** It has the fewest false alarms, holds no legitimate payment, and does best on coached victims. On its own, Qwen was the strongest LLM (recall 0.95, false alarms 0.06), but it held one legitimate payment. All differences are within the 95% intervals at this sample size.

### 2026-11-07: FINAL, held-out test split (75 scenarios: 39 scams, 36 legitimate)

Free conditions: run `free-test`. LLM conditions: run `llm-test-v2` (gpt-oss-120b).

| Condition | Scam recall (95% CI) | False alarms (95% CI) | Hard-stop recall | Hard-stop false alarms | Coached recall |
|---|---|---|---|---|---|
| A Bank-style rules | 0.56 (0.41–0.71) | 0.39 (0.25–0.55) | 0.00 | 0.00 | 0.57 |
| B Rules + phrases | 0.82 (0.67–0.91) | 0.44 (0.29–0.60) | 0.26 | 0.00 | 0.57 |
| C ML model alone | 0.69 (0.54–0.81) | 0.00 (0.00–0.10) | 0.26 | 0.00 | 0.00 |
| D Rules + phrases + ML | 0.90 (0.76–0.96) | 0.44 (0.29–0.60) | 0.69 | 0.00 | 0.57 |
| G Rules + phrases + questions | 0.82 (0.67–0.91) | 0.39 (0.25–0.55) | 0.41 | 0.00 | 0.57 |
| F Pauseline, no LLM (the site's fallback mode) | 0.87 (0.73–0.94) | 0.39 (0.25–0.55) | 0.62 | 0.00 | 0.57 |
| L LLM alone | 0.95 (0.83–0.99) | 0.08 (0.03–0.22) | 0.87 | **0.03** | 0.71 |
| **M Pauseline (deployed)** | **0.95** (0.83–0.99) | **0.17** (0.08–0.32) | **0.74** | **0.00** | **0.71** |

Chart: `docs/figures/results-test.png`.

**Robustness to speech-recognition noise** (`--perturb asr:0.15`, runs `free-test-asr15`, `llm-test-asr15-v2`):

| Condition | Clean recall / false alarms | With speech noise recall / false alarms |
|---|---|---|
| B Rules + phrases | 0.82 / 0.44 | 0.77 / 0.44 |
| C ML model alone | 0.69 / 0.00 | 0.64 / 0.00 |
| F Pauseline, no LLM | 0.87 / 0.39 | 0.82 / 0.39 |
| **M Pauseline (deployed)** | 0.95 / 0.17 | **0.95 / 0.11** (hard-stop recall 0.77, hard-stop false alarms 0.00) |

**By language (M):** recall is 0.92 in English and 1.00 in both Hindi and Hinglish. False alarms are 0.15 in English, 0.00 in Hindi and 0.29 in Hinglish; the Hinglish figure is 2 of 7 payments, both cooling-offs.

**Answers to the research questions**
- **RQ1 (detection):** reading the payer's words beats bank-style context rules by a wide margin. Recall goes from 0.56 to 0.95, false alarms from 0.39 to 0.17, and hard-stop recall from 0.00 to 0.74. Context rules alone can never tell a scary-but-legitimate payment (hospital deposit, funeral home, car deposit) from a scam.
- **RQ2 (questions):** questions are what let the LLM-based engine avoid the LLM's over-suspicion: the LLM re-assesses with the answers and lowers its score. Coached victims answer "no", yet 71% are still caught, because the words and the LLM carry the signal.
- **RQ3 (generalisation and robustness):**
  - The ML model, trained only on template-generated data, generalises to hand-written requests: 0 false alarms and 0.69 recall on test.
  - It fails on bland wording ("Monthly payment.", "Paying an administration fee.").
  - The deployed engine is unaffected by 15% speech-recognition noise.
- **The combination is better than the LLM alone where it matters most.** On its own the LLM had fewer false alarms (0.08 vs 0.17), but it *held* a legitimate payment for the family (bail paid in person at a courthouse); the combined engine held none. The combined engine also keeps working at a reduced level (row F) if the free LLM quota runs out.

**Remaining misses (M, test):**
- `v1-023` "Paying for my computer security subscription." and `v1-049` "Paying for training materials for my new job.": coached victims with bland wording and modest amounts.
- These are the structural limit of word-based detection. The mitigation is a family review of new recurring payees.

**Methodology note: one re-tuning after the first test run (please read).**
- The first test run (`llm-test`) used the context cap of 0.69 for M too. That cap had been chosen on dev for the engine *without* the LLM, then reused unchanged. On test, M had false alarms of 0.42, mostly cooling-offs on large first payments to new payees, where the LLM itself scored 0.02–0.15.
- We then swept the cap **for the LLM engine on the dev split** (no test data used). Dev favoured 0.35: false alarms 0.17 → 0.06 with no loss in recall, hard-stop recall or coached victims.
- We adopted 0.35 when the LLM is available. The engine falls back to 0.69 automatically when the LLM is unavailable, and that fallback is tested.
- The table above is the **second** evaluation on the test split. The first was:

  | Run | Scam recall | False alarms | Hard-stop recall | Hard-stop false alarms | Coached recall |
  |---|---|---|---|---|---|
  | M, first test run (`llm-test`, cap 0.69) | 0.95 | 0.42 | 0.77 | 0.03 | 0.71 |

  We report both, because the test split influenced *when* we noticed the gap, even though the fix was chosen on dev.
- **For a clean future evaluation:** write new held-out scenarios (benchmark v2) and evaluate the frozen configuration once.

**Cost:** every run above, including 3 models × 2 splits, sweeps and robustness, cost $0. It used about 700 Groq free-tier requests over the day, and most sweeps were answered entirely from the cache.

### Future work
- Benchmark v2: new held-out scenarios written by someone who has not seen v1, for a single clean evaluation of the frozen configuration.
- Real conversations: partner with a scam-awareness group to collect (consented, anonymised) descriptions.
- Family review of new recurring payees, for the coached-and-bland cases word-based detection cannot catch.
