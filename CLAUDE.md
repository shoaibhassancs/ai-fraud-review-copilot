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
├── data/ # synthetic data generator + generated CSVs
├── knowledge_base/ # fraud-pattern markdown docs (source for RAG)
├── src/
│ ├── schemas.py # CaseNote model + Recommendation enum
│ ├── flagger.py # rule-based flagging
│ ├── retrieval.py # embeddings + Chroma lookup
│ ├── tools.py # lookup_customer_history, lookup_merchant_info
│ ├── agent.py # orchestration: retrieve → call tools → generate
│ ├── guardrail.py # PII redaction + language constraints
│ └── api.py # FastAPI app
├── eval/
│ ├── eval_set.json # 15–20 labeled cases
│ └── run_eval.py # scores the agent against eval_set.json
└── tests/

## How to run it locally
```bash
# install deps
pip install -r requirements.txt

# generate synthetic data (first run only)
python data/generate_data.py

# run the API
uvicorn src.api:app --reload

# call it
curl -X POST localhost:8000/review/{transaction_id}
```

## Conventions to keep
- Always run `python eval/run_eval.py` before committing a prompt or retrieval change — a prompt change that tanks eval accuracy should be caught before it's pushed.
- Guardrail checks are code-level (regex/rule), not just prompt instructions — never remove or weaken this in favor of a prompt-only fix.
- Keep tool calls (`tools.py`) deterministic and boring — they simulate backend systems, not model logic.
- No real financial data or real PII enters this repo at any point — synthetic data only.
- Branch + PR for every change, even solo — real PR descriptions, not placeholders.