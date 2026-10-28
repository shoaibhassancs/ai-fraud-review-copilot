# CLAUDE.md

## What this project does and why
AI Fraud-Review Copilot is an agent that takes a flagged transaction, retrieves relevant fraud-pattern knowledge via RAG, pulls customer and merchant context through tool calls, and drafts a structured case note with a recommendation. It never makes the final call — every note is routed to a human analyst for decision. The goal is to cut the manual triage time fraud/risk analysts spend writing these notes by hand, while keeping the reasoning consistent and auditable for compliance.

## Architecture at a glance (five stages)
1. **Flag** — rule-based flagger tags a transaction (amount spike, new merchant category, geo anomaly, velocity).
2. **Retrieve** — RAG pulls the relevant fraud-pattern doc from the Chroma knowledge base.
3. **Tool calls** — agent calls `lookup_customer_history(customer_id)` and `lookup_merchant_info(merchant_id)`.
4. **Generate** — agent drafts a structured case note (risk factors, evidence, recommendation, confidence) via the Google Gemini API (`google-genai`).
5. **Guardrail** — output is checked before returning: no definitive fraud claims, PII redacted.

Automated end to end except the final decision — the analyst always makes the call.

## Where things live
fraud-review-copilot/
├── data/
│ ├── generate_data.py # builds the synthetic dataset
│ ├── transactions.csv
│ ├── customers.csv
│ └── merchants.csv
├── knowledge_base/
│ ├── card_not_present.md # amount-spike evidence (repurposed — see below)
│ ├── account_takeover.md # new-category evidence (repurposed — see below)
│ ├── velocity_fraud.md # velocity_spike evidence
│ └── geo_anomaly.md # geo_anomaly evidence
├── src/
│ ├── schemas.py # CaseNote model + Recommendation enum
│ ├── flagger.py # rule-based flagging
│ ├── retrieval.py # embeddings + Chroma lookup
│ ├── tools.py # lookup_customer_history, lookup_merchant_info
│ ├── agent.py # orchestration: retrieve → call tools → generate
│ ├── guardrail.py # PII redaction + language constraints
│ └── api.py # FastAPI app
├── eval/
│ ├── eval_set.json # 18 hand-labeled cases
│ └── run_eval.py # scores the agent against eval_set.json
└── tests/


Note: `card_not_present.md` and `account_takeover.md` are named for their standard fraud-ops meaning but written to ground `amount_spike` and `new_merchant_category` evidence respectively, since those two flag reasons had no directly-named pattern doc. Retrieval matches on content, not filename, so this is intentional — not a mismatch to fix.

## How to run it locally
```bash
# install deps
pip install -r requirements.txt

# generate synthetic data (first run only)
python data/generate_data.py

# run the rule-based flagger (fills in flag_reason)
python src/flagger.py

# embed the knowledge base into Chroma (first run only, or after editing a doc)
python src/retrieval.py

# draft a case note for one transaction (manual check)
python -m src.agent <transaction_id>

# run the API
uvicorn src.api:app --reload

# call it
curl -X POST localhost:8000/review/{transaction_id}

# run the eval set against the agent (paces calls to stay under the
# model's free-tier requests-per-minute cap -- see run_eval.py for why)
python -m eval.run_eval
```

## Conventions to keep
- Always run `python -m eval.run_eval` before committing a prompt or retrieval change — a prompt change that tanks eval accuracy should be caught before it's pushed.
- Guardrail checks are code-level (regex/rule), not just prompt instructions — never remove or weaken this in favor of a prompt-only fix.
- Keep tool calls (`tools.py`) deterministic and boring — they simulate backend systems, not model logic.
- No real financial data or real PII enters this repo at any point — synthetic data only.
- Branch + PR for every change, even solo — real PR descriptions, not placeholders.
- Flagger thresholds are tuned against the actual generated data's trigger rates, not picked abstractly — re-check counts after any regeneration (e.g. after editing `generate_data.py`, flag distribution can shift even with the same rule logic).
- Retrieval queries must be natural-language phrasings built from the flag reason, not the raw `flag_reason` string — confirmed via manual testing (Day 2) that enum strings retrieve incorrectly for at least one flag type.
- Scripts that import from other `src/` modules (`agent.py` and beyond) must be run with `python -m src.<name>`, not `python src/<name>.py` — only standalone scripts with no cross-module imports (`flagger.py`, `retrieval.py`, `tools.py`) support the direct form. This applies to `eval/run_eval.py` too: run as `python -m eval.run_eval`.

## Known gaps (dated)
- **Eval accuracy as of Action 17 (Day 4): 61.1% (11/18) — below SCOPE.md's 80% bar.** By flag type: `geo_anomaly` 4/5 (80%), `velocity_spike` 3/4 (75%), `amount_spike` 3/5 (60%), `new_merchant_category` 1/4 (25%). Two real patterns surfaced, not noise:
  - `new_merchant_category` fails in both directions, not just one bias: escalated two cases (T0071, T0091) where the ground truth said clear (normal amount, low/medium-risk merchant, nothing but a new category) and cleared the one case (T0133) where the ground truth said escalate specifically because of a 28-day-old account — the account-takeover signal the knowledge base describes.
  - `amount_spike`'s two misses (T0078, T0143) share a shape: both were labeled escalate purely on amount magnitude at a low-risk merchant, and the agent cleared both — possibly anchoring on the merchant's low risk tag over the raw amount deviation. Not yet confirmed against the actual `case_note` text.
  - To investigate: pull the real `case_note` text for these five misses to see the agent's actual reasoning, not just the final verdict:
    `python -m eval.run_eval --only T0071,T0091,T0133,T0078,T0143`
- **Per-request latency as of Action 19 (Day 5): ~60-110s, confirmed I/O-wait-bound, not locally-compute-bound.**
  Measured both on Render's free tier (63.4s, 88.7s, 107.7s across three calls) and locally on full
  dev hardware (`time python -m src.agent T0002`: 64.55s wall-clock, but only 1.07s user + 0.38s
  system CPU time — 2% utilization). Nearly identical wall-clock time on a fast local machine and a
  resource-constrained free-tier instance rules out local compute as the bottleneck. The remaining
  time is some combination of network round-trip latency and Gemini's own server-side inference
  ("thinking") time for `gemini-3.5-flash-lite` — both look identical from the local process's point
  of view (idle CPU), and this measurement doesn't distinguish how much is which. What's established:
  the cost is inherent to the two-phase design's 3-4 sequential Gemini API round-trips per request
  (tool-calling loop, then a separate structured-generation call), not to where the app is deployed.
  Practical implication unchanged: never point the eval script or a CI job at the live HTTP endpoint
  for batch scoring — at this per-request cost, an 18-case run would take 20-35+ minutes in request
  time alone, on top of RPM pacing. `eval/run_eval.py` correctly calls `draft_case_note()` directly
  already; keep it that way. The deployed URL is for single-request demos, not batch evaluation.