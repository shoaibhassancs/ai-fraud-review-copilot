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
├── .github/
│ └── workflows/
│     └── ci.yml # runs the eval subset on every push
└── tests/

Note: `card_not_present.md` and `account_takeover.md` are named for their standard fraud-ops meaning but written to ground `amount_spike` and `new_merchant_category` evidence respectively, since those two flag reasons had no directly-named pattern doc. Retrieval matches on content, not filename, so this is intentional — not a mismatch to fix.

## How to run it locally
```bash
# set up your API key (first run only)
cp .env.example .env
# then edit .env and add your real GEMINI_API_KEY

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

## CI
`.github/workflows/ci.yml` runs on every push: installs deps, embeds the knowledge base into Chroma (fresh each run — `chroma_db/` is git-ignored), then runs `eval/run_eval.py` against a fixed 6-case subset, not the full 18. Requires a `GEMINI_API_KEY` secret set in the repo's GitHub Actions settings — not read from `.env`, which never reaches CI.

The full 18-case set is deliberately never run in CI: at ~3 calls/case and ~60-110s/call, it would cost 20-35+ minutes and ~50+ Gemini calls per push, risking the day's entire free-tier quota on CI alone. The 6-case subset (2x `geo_anomaly`, 2x `amount_spike`, 1x `velocity_spike`, 1x `new_merchant_category`) was sized specifically so the gate's real tolerance matches `SCOPE.md`'s actual 80% bar — a 4-case version was tried first and found to silently enforce ~100% (one flip in 4 always fails), confirmed by two real, logged CI failures before being widened.

## Logging
`src/api.py` logs a structured JSON line to stdout for every request (Action 22). Three different
shapes depending on outcome, not one universal one — all share `transaction_id` and `latency_seconds`:
- **Success**: `flag_reason`, `recommendation`, `confidence`, `total_tokens`, `guardrail_triggered: false`
- **Not found**: `status: "not_found"` (no flag/recommendation/tokens — the transaction never existed)
- **Guardrail violation**: `guardrail_triggered: true`, `guardrail_detail`, `total_tokens`

Lives in `api.py`, not `agent.py` — a deliberately different call than where the guardrail itself
lives. The guardrail is inside `agent.py` so every call path (API, direct script, eval) is protected
equally, a correctness concern. Logging is specifically about production request handling, and
Render only ever runs `api.py` in production, so that's the one place it needs to be — a manual
`python -m src.agent` run or `eval/run_eval.py`'s batch scoring aren't production traffic, and
logging them the same way would just be noise in the log you'd scan under pressure.

`total_tokens` is accumulated inside `agent.py`'s `draft_case_note()` across every Gemini call in a
request (the tool-calling loop plus the separate generation phase), not read off just the last
response — a single request can make 2-4 calls, and reading only the final one would understate the
real cost.

A `GuardrailViolation` is logged (with the matched detail) before being re-raised in `api.py` —
logging is visibility, not a safety net; the violation still surfaces as a loud, unhandled failure
to the caller exactly as before this action. `agent.py` attaches the request's already-accumulated
`total_tokens` onto the exception before re-raising, so a guardrail-violating request's real token
cost still gets logged — without this, that cost would silently disappear from the log the one time
it's most worth tracking.

**Note:** you may see `"AFC is enabled with max remote calls: 10."` in the raw logs — that's the
SDK itself, not this project's logging, and it fires regardless of the manual-loop setting (a known
upstream quirk, not a sign the design broke). See `agent.py`'s module docstring for the full
explanation; `tools_called` being populated correctly on every real run is the actual evidence the
manual loop — not AFC — is what executes.

## Conventions to keep
- Always run `python -m eval.run_eval` before committing a prompt or retrieval change — a prompt change that tanks eval accuracy should be caught before it's pushed.
- Guardrail checks are code-level (regex/rule), not just prompt instructions — never remove or weaken this in favor of a prompt-only fix.
- Keep tool calls (`tools.py`) deterministic and boring — they simulate backend systems, not model logic.
- No real financial data or real PII enters this repo at any point — synthetic data only.
- Branch + PR for every change, even solo — real PR descriptions, not placeholders.
- Flagger thresholds are tuned against the actual generated data's trigger rates, not picked abstractly — re-check counts after any regeneration (e.g. after editing `generate_data.py`, flag distribution can shift even with the same rule logic).
- Retrieval queries must be natural-language phrasings built from the flag reason, not the raw `flag_reason` string — confirmed via manual testing (Day 2) that enum strings retrieve incorrectly for at least one flag type.
- Scripts that import from other `src/` modules (`agent.py` and beyond) must be run with `python -m src.<name>`, not `python src/<name>.py` — only standalone scripts with no cross-module imports (`flagger.py`, `retrieval.py`, `tools.py`) support the direct form. This applies to `eval/run_eval.py` too: run as `python -m eval.run_eval`.
- A failed CI run is not automatically a code regression — Gemini's own non-determinism can fail the eval gate on an unchanged push (see Known gaps). Check which case(s) failed against known-borderline ids before assuming the code broke something.

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
- **CI gate non-determinism as of Action 20 (Day 5): confirmed directly, not theoretical.** `T0014` flipped escalate→clear→clear across three separate live CI runs with zero code changes between them; `T0078` flipped escalate→clear→escalate across two. Both are real Gemini non-determinism on genuinely borderline cases (both already flagged in Action 13/17 as cases where the model weighs mitigating context, not threshold-matching), not a bug in the pipeline or the labels. A red CI run needs human triage before assuming something broke — check whether the failing case is one of these two known-borderline ones before investigating the code.
- **Eval accuracy as of Action 17 (Day 4): 61.1% (11/18) — below SCOPE.md's 80% bar. Investigated and partially fixed as of Action 23 (Day 6); full 18-case re-run not yet done.**
  The original by-flag-type breakdown: `geo_anomaly` 4/5 (80%), `velocity_spike` 3/4 (75%),
  `amount_spike` 3/5 (60%), `new_merchant_category` 1/4 (25%).

  Action 23 pulled the real `case_note` text for all five original misses (T0071, T0091, T0133,
  T0078, T0143) via `python -m src.agent <id>` — `run_eval.py` deliberately doesn't print case-note
  text (by design, to keep the CI gate fast), so this needed the direct script, not the eval runner.
  Findings, from real reasoning text, not inferred from pass/fail labels:

  - **T0078 (amount_spike): a genuine bug, confirmed.** The model cited a prior transaction at the
    same merchant as mitigating ($481.84) without checking whether that prior amount was itself
    comparable in size to the flagged one ($1855.45, ~2.76x the customer's ceiling). Merchant
    familiarity was treated as sufficient on its own.
  - **T0133 (new_merchant_category): a genuine bug, confirmed, different in kind from T0078.** The
    model correctly retrieved and paraphrased `account_takeover.md`'s actual signature, named the
    28-day account age as a risk factor — then recommended `clear` anyway. The right signal was
    identified and then didn't drive the verdict.
  - **T0071: inconclusive — non-determinism, not a new finding.** Manual re-run produced the correct
    `clear`, meaning the original `escalate` that failed in eval was a different, non-matching sample
    of the same per-request variance already confirmed with T0014/T0078 in CI (see the CI entry
    below). No fix targets this; there's nothing here to fix.
  - **T0143 (amount_spike): not an agent bug — the ground-truth label was wrong.** The agent's own
    evidence surfaced two prior transactions for this same customer already above the stated $89.12
    ceiling ($164.50 / T0063, larger than this transaction; $116.31 / T0125) — a real behavioral
    pattern the original static-ceiling labeling never cross-referenced. Relabeled
    `escalate` → `clear`. `eval_set.json` is now 6 escalate / 12 clear (was 7/11).
  - **The original hypothesis ("anchoring on low merchant risk tag") did not hold up against any of
    the four real texts** — none of them name merchant risk tier as the deciding factor. Replaced
    with the two specific, text-confirmed patterns above.

  **Fix:** `agent.py`'s grounding instruction now explicitly addresses both confirmed patterns —
  prior-merchant history only mitigates when prior amounts were comparable in size, and a risk
  factor matching the retrieved reference material must meaningfully influence the recommendation.
  Verified with two targeted manual re-runs: both T0078 and T0133 flipped to the correct
  recommendation, with visibly different reasoning in the evidence text, not just a different
  verdict — see git history for the before/after text.

  **Watch item, not yet confirmed:** the CI non-determinism entry below logs T0078 flipping across
  past CI runs, attributed to variance alone. It's possible some of those flips were actually this
  reasoning bug firing stochastically rather than pure randomness — worth checking whether T0078
  stabilizes on the next few CI runs now that the bug's addressed. Not stated as fact until there's
  real post-fix CI evidence either way.

  **Not yet done:** a full 18-case re-run to get an updated overall accuracy number. Deferred
  deliberately (Action 23, late-night judgment-quality call) rather than run at the time the fix
  landed — next natural opportunity is the next full CI run or a dedicated Day 7 check.