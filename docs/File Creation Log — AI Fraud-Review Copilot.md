# File Creation Log — AI Fraud-Review Copilot

Nov 3, 2026 · @Shoaib

Every file in the repo, in the order it was actually created, action by action — grounded in the real Action Log, not the architecture diagram.

| Day | Action | File(s) | Created / Edited | Note |
| --- | --- | --- | --- | --- |
| 1 | 1 | `SCOPE.md` | Created | First file in the repo, written before git even existed. |
| 1 | 2 | `.gitignore`, `CLAUDE.md` | Created | `.gitignore` written before any secret-holding file existed; `.venv` set up same action. |
| 1 | \~2 | `requirements.txt` | Created (inferred) | Not explicitly logged — Action 4 says it was "swapped" and "re-frozen" for google-genai, meaning it already existed by then; most likely created here, alongside `.venv`. |
| 1 | \~2 | `tests/` (empty), `.vscode/settings.json`, `.python-version`, `ai-fraud-review-copilot.code-workspace` | Created (inferred) | Standard repo/IDE scaffolding, never logged. `tests/` is worth flagging on its own: Actions 15 and 22 both describe writing a real "unit test," but no test file is ever logged as created, and the folder stays empty — a real gap, not just an unlogged one. |
| 1 | 3 | `docs/AI_ML_Engineer_Guide.md` | Created | Day 1 reference-table notes. |
| 1 | 4 | `src/schemas.py` | Created | `requirements.txt`, `CLAUDE.md` edited same action (Claude → Gemini switch). |
| 2 | 5 | `data/generate_data.py`, `customers.csv`, `merchants.csv`, `transactions.csv` | Created | `CLAUDE.md` edited. |
| 2 | 6 | `src/flagger.py` | Created | `generate_data.py` reopened (category-affinity), CSVs regenerated, `CLAUDE.md` edited. |
| 2 | 7 | `knowledge_base/card_not_present.md`, `account_takeover.md`, `velocity_fraud.md`, `geo_anomaly.md` | Created | All four together; `CLAUDE.md` edited. |
| 2 | 8 | `src/retrieval.py` (embed half) | Created | `.gitignore` edited to add `chroma_db/`. |
| 2 | 9 | `src/retrieval.py` (query half) | Edited | `CLAUDE.md` edited. |
| 3 | 10 | `src/tools.py` | Created | — |
| 3 | 11 | `src/agent.py` | Created | Retrieval + the two-phase tool-calling/generation loop. |
| 3 | 12 | — | Pass-through | `schemas.py` already existed from Action 4; nothing new built. |
| 3 | 13 | `src/agent.py` | Edited | `MODEL_NAME` switched to `gemini-3.5-flash-lite`; `CLAUDE.md` edited. |
| 4 | 14 | `src/api.py` | Created | — |
| 4 | 15 | `src/guardrail.py` | Created | `agent.py` edited same action to wire the guardrail in. |
| 4 | 16 | `eval/eval_set.json` | Created | 18 hand-labeled cases. |
| 4 | 17 | `eval/run_eval.py`, `eval/__init__.py` | Created | `CLAUDE.md` edited. |
| 5 | 18 | `Dockerfile`, `.dockerignore` | Created | — |
| 5 | 19 | — | Deployed (Render) | No new files; `CLAUDE.md` edited (latency finding). |
| 5 | 20 | `.github/workflows/ci.yml` | Created | `CLAUDE.md` edited. |
| 5 | 21 | `.env.example` | Created | Named in the file tree since Day 1, never actually created until now. |
| 6 | 22 | `src/api.py`, `src/agent.py` | Edited | Structured logging, token accumulation. |
| 6 | 23 | `src/agent.py`, `eval/eval_set.json` | Edited | Grounding-instruction fix; T0143 relabeled. |
| 7 | 25 | — | Written | Pitch narrative — the log names no specific file. Actions 24/26/27 skipped at your direction. |
| 7 | \~25 | `README.md` | Created (inferred) | The log never names a file for Action 25's narrative. README is the natural fit for a polished, public-facing summary — but Day 1 scaffolding is equally plausible, and the log simply doesn't say. |
