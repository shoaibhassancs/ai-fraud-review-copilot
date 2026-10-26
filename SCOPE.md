# Scope

## Solution (one-liner)
An agent that, given a flagged transaction, retrieves fraud-pattern knowledge, pulls customer/merchant context via tool calls, and drafts a structured case note with a recommendation — always routed to a human for the final call.

## In Scope
- Synthetic data
- Rule-based flagging
- A small RAG knowledge base
- Two tool calls: customer history, merchant info
- The case-note-drafting agent
- One guardrail: no definitive fraud claims + PII redactio
- A 15–20 case eval set
- Containerized/deployed API with CI running evals on push

## Out of Scope
- Real financial data/PII
- Training an actual fraud-detection model
- Any frontend beyond a bare API
- Multi-analyst auth/collaboration