# AI Fraud-Review Copilot — Action Log

Oct 27, 2026 · @Shoaib

This is a running log of the AI Fraud-Review Copilot build, one Action Plan step at a time. Each entry captures what the action was, the reasoning and alternatives behind the choices made, and any questions raised and answered along the way — written so each entry could be said out loud in an interview. A new entry is added only once an action is actually finished and confirmed.

## Day 1 — Topics to revise before Actions 1–4

Pulled from the framework doc's own "Concept Check Before Each Action" table, narrowed to today's four actions.

**Applies throughout today's actions:**

- Prompting techniques
- Plan mode
- Debugging with AI
- Where you rely on AI code vs. step in

**Tied to specific actions:**

- Action 2 (Set up the repo and CLAUDE.md): Context files (CLAUDE.md/AGENT.md); Git/GitHub workflow
- Action 4 (Sketch the architecture decisions): Transformer/LLM basics; RAG: the retrieve-then-generate loop

Actions 1 and 3 have no tied topics in the framework — Action 1 needs no prior knowledge, and Action 3 is the reading itself.

## Action 1 — Scope the project to the exact MVP

Scoped the MVP by moving the project spec's existing one-line solution and in/out-of-scope lists into a standalone `SCOPE.md` file at the repo root, so scope is checked against a fixed reference instead of re-decided daily.

**What MVP means here.** Minimum Viable Product — the smallest version that's complete on a narrow slice, not partial on a wide slice. The one claim this project needs to prove: an agent can take a flagged transaction, pull context, and draft a defensible case note. Everything else serves that claim for the interview, not production-readiness.

**What in-scope/out-of-scope means.** The explicit, written boundary of what will and won't be built — so mid-week impulses (add a login, try real data, build a frontend) have something concrete to check against instead of relying on willpower.

**Why `SCOPE.md` as its own file, not README or a scratch note.** README will get diluted with setup instructions as the week goes on; a scratch note outside the repo isn't versioned or visible to an AI coding tool. `SCOPE.md` stays untouched and is referenced by `CLAUDE.md` in Action 2, so the AI tool respects the same boundary.

**The mindset.** Scope doesn't die in one big decision — it erodes through small "sure, why not" moments, and an AI coding tool makes this worse because it optimizes toward "complete and polished," not toward the stated boundary. The fix: write the boundary down as a file before writing any code, turning it from something held in your head (negotiable, forgettable) into something you check against (a fact). Reusable for any time-boxed build, not just this one.

**`SCOPE.md` contents** (pulled from the project spec, nothing invented):

- One-line solution: an agent that, given a flagged transaction, retrieves fraud-pattern knowledge, pulls customer/merchant context via tool calls, and drafts a structured case note with a recommendation — always routed to a human for the final call.
- In scope: synthetic data, rule-based flagging, a small RAG knowledge base, two tool calls (customer history, merchant info), the case-note-drafting agent, one guardrail (no definitive fraud claims + PII redaction), a 15–20 case eval set, containerized/deployed API with CI running evals on push.
- Out of scope: real financial data or PII, training an actual fraud-detection model, any frontend beyond a bare API, multi-analyst auth/collaboration.

**The Kaggle detour — synthetic vs. real data.** Considered using a real Kaggle fraud dataset instead of generating synthetic data. Decided to keep synthetic, as originally scoped, because:

- *Schema fit:* the well-known Kaggle credit card fraud dataset is PCA-anonymized (columns V1–V28) precisely because the real fields were too sensitive to release — unusable for tool calls like `lookup_customer_history()` that need actual customer/merchant fields.
- *Label control:* real fraud data is usually under 1% positive with no control over which cases are ambiguous; the 15–20 case eval set needs deliberately planted borderline cases to mean anything.
- *Consistency of story:* a tool about PII-safe, auditable decisions shouldn't be prototyped on real transaction data, even anonymized.

**Interview defense, refined version:**

> This project is testing agent orchestration — retrieval, tool calls, structured generation — not fraud classification. The data's job is to exercise that pipeline realistically, and for that I needed control over two things a public dataset wouldn't give me: a schema the tool calls could actually query — customer IDs, merchant categories, account age, not PCA-anonymized columns — and the ability to plant a few deliberately borderline cases, since real fraud data is under 1% positive and I don't get to choose which cases are ambiguous.

Honest trade-off to volunteer unprompted: synthetic data can't prove the agent generalizes to messy real-world noise (inconsistent timestamps, mismatched names) — accepted for a one-week project, and would be addressed in a longer build by validating against real anonymized data or shaping the generator's noise off it.

## Action 2 — Set up the repo and CLAUDE.md

**1. Git initialized locally, not cloned from a fresh GitHub repo.** *Why:* `SCOPE.md` already existed in the folder — cloning an empty repo on top would've meant shuffling that file around for nothing. *Alternative considered:* create the repo on GitHub first, clone it down, then add files — fine for a genuinely empty folder, not this one. *Mindset:* don't let tooling order dictate workflow — pick the direction that fits the state you're actually in, not the "textbook" order.

**2. `.venv`, not conda — and the plain system Python, not Anaconda's base interpreter.** *Why:* this project is pure Python making API calls, with no compiled or binary dependencies (CUDA, C libraries) anywhere in the stack — the one thing conda exists to manage well. `.venv` is built into Python itself and matches what the project's own package list already assumes. *Alternative considered:* conda (common in data-science work generally) and Poetry (nicer dependency locking, but its own config system on top of a project that already commits to plain pip). *Mindset:* match the tool to what the project actually needs, not to what's popular in the broader field it belongs to — "data science uses conda" is a generalization, the real question is what this project's dependencies require.

**3. `.gitignore` written before the first commit, not after.** *Why:* `.env` will hold a real Anthropic API key from Day 4 onward; if `.gitignore` exists before that file does, the key can never leak by accident — the protection is structural, not something to remember under time pressure. *Alternative considered:* add `.gitignore` whenever it becomes relevant — rejected, since "whenever relevant" is exactly the kind of thing that gets forgotten mid-build. *Mindset:* put safety rails in place before the thing they protect against exists, not after — prevention beats remembering.

**4. A virtual environment at all.** *Why:* without isolation, every `pip install` lands in one global Python environment shared by every project on the machine — a version bump for one project can silently break another, often without noticing until much later. *Mindset:* make dependencies explicit and self-contained rather than implicit and shared — the same instinct that later justifies Docker on Day 5 and `.env` for config. Isolate state at every layer of the stack, not just the code.

**5. `CLAUDE.md` as a dedicated file, not folded into README, not skipped.** *Why:* Claude Code auto-loads `CLAUDE.md` into context at the start of every session — confirmed in Anthropic's own docs, not assumed — so architecture and conventions don't need re-explaining each time a session opens. *Alternatives considered:* no context file (works, but costs time daily and the explanation subtly drifts each time it's retyped); folding it into README (README is written for a human skimming the repo — a context file is written to be re-read by a model every session, and mixing those two audiences tends to weaken both). *Mindset:* the same move as `SCOPE.md` from Action 1, aimed at a different reader — `SCOPE.md` keeps you from drifting on scope by giving you something to check against instead of holding it in memory; `CLAUDE.md` does the same for the AI tool, stopping it from re-guessing the architecture or suggesting patterns that don't match what's already there. The general rule underneath both: externalize the constraints you want respected — write them down once, don't rely on remembering or re-explaining them.

## Action 3 — Read and note every reference-table topic

**1. Notes saved as a repo file (`docs/AI_ML_Engineer_Guide.md`), not kept in chat or in memory.** *Why:* Day 6 of the framework requires rereading these notes — that only works if they're durable and versioned, not reconstructed from memory under time pressure. *Alternative considered:* keep the notes inside this Action Log doc itself — rejected, since this doc is for the reasoning behind decisions, not raw topic definitions; mixing the two would make both harder to scan later. *Mindset:* the same externalize-it idea as `SCOPE.md` and `CLAUDE.md`, now applied to knowledge instead of rules — write it down once, don't trust memory to hold it until the interview.

**2. Effort split by priority tier (Build vs. Know), not uniform depth across every topic.** *Why:* Build-tier topics (RAG, tool calling, chunking, etc.) get real understanding from actually building them over the next few days — today's note is a placeholder, not the learning itself. Know-tier topics (quantization, fine-tuning landscape, data governance, SQL) won't be revisited until Day 6, so today's one-liner is the only prep standing between freezing and not freezing on them in the interview. *Alternative considered:* spend equal time on all \~27 topics — rejected as inefficient, since several are about to be learned by doing regardless of how much gets read today. *Mindset:* match study depth to when recall will actually be needed without practice versus recall after hands-on building — don't over-invest in things the project itself will teach.

**3. One correction made during review — Chroma's default distance metric.** Initially noted as "usually cosine similarity," generalizing from vector DBs broadly. Checked against the actual behavior rather than left as-is: Chroma defaults to L2 distance, not cosine, unless cosine is explicitly set at collection creation — though cosine is still the more common choice for text embeddings specifically, so the instinct wasn't wrong, just imprecise for this tool's default. *Mindset:* a plausible-sounding generalization and a verified fact aren't the same thing — worth checking anything about to become an interview answer, since the gap only shows up when someone who actually knows the tool pushes on it.

## Action 4 — Sketch the architecture decisions

**1. Vector DB — Chroma.** Not really a decision, a confirmation: the spec itself already named Chroma ("use one free option rather than reading theory first") — free, local, no infra, fits a project about proving RAG mechanics rather than evaluating vendors.

**2. LLM — reversed mid-action, from Claude to Google Gemini.** *Initial call:* Claude API, on the reasoning that tool calling and structured output are first-class there, and Claude Pro was assumed to cover it. *What changed it:* Claude Pro and API access turned out to be separate, independently billed products — Pro covers claude.ai/Claude Code, not programmatic calls via the `anthropic` package. Checked rather than assumed, since this was about to become a real cost decision. *Alternative considered and ruled out on fit, not preference:* OpenAI's free tier — doesn't support function calling or structured output on the free tier, which breaks the "structured output makes the eval set scorable" reasoning this whole architecture depends on. *Why Gemini specifically:* Google AI Studio's free tier is genuinely free (no card), with native function calling and structured JSON output included at no cost, and a daily quota well past what a week of iteration plus a 15–20 case eval run needs — confirmed, not assumed, given how much this decision mattered. *One technical correction caught in the same pass:* `google-generativeai`, the package most tutorials still reference, was deprecated and reached end-of-life in late 2025 — `google-genai` is the current, maintained package. Installing the wrong one would've looked fine until it quietly didn't work. *Mindset:* "free" isn't one property to optimize for — it has to be checked against what the architecture actually needs (tool calling, structured output), the same way the original Claude-vs-OpenAI call was checked against project constraints, not picked by popularity. A decision already "locked" isn't sacred if new information shows the premise was wrong — reverse it deliberately and say why, not quietly.

**3. Case-note schema — `src/schemas.py`.** A Pydantic model (`CaseNote`) with `flag_reason`, `risk_factors`, `evidence`, `recommendation` (a str `Enum` of "escalate"/"clear"), `confidence` (float, 0–1). Sized to exactly what the spec's eval harness needs to score — recommendation-direction accuracy and risk-factor citation — nothing added for show. Provider-agnostic by design, so it needed no changes when the LLM choice flipped.

**Files touched this action, and why:**

- `requirements.txt` — `anthropic` swapped for `google-genai`, re-frozen.
- `CLAUDE.md` — file tree updated for `schemas.py`; architecture section now names Gemini (`google-genai`) as the generation provider.
- `src/schemas.py` — created; no further edit needed.
- `SCOPE.md` — untouched; this stayed an implementation detail inside the already-scoped agent, not a scope change.

## Day 2 — Topics to revise before Actions 5–9

Pulled from the framework doc's own "Concept Check Before Each Action" table, narrowed to tomorrow's five actions.

- Action 7 (Write the fraud-pattern knowledge base): RAG: the retrieve-then-generate loop
- Action 8 (Set up Chroma and embed the docs): Embeddings & vector databases
- Action 9 (Tune chunking and test retrieval manually): Chunking & retrieval strategy

Actions 5 and 6 have no tied topics in the framework — straightforward data generation and rule-writing, no prerequisite concept.

## Action 5 — Write the synthetic data generator

**1. Format — CSV, not SQLite.** The spec's "Suggested tech" column left this open, but its own Project Files tree already named `transactions.csv`, `customers.csv`, `merchants.csv` explicitly. Not a new decision — following what the doc had already settled elsewhere rather than re-opening it. CSV also keeps things simple for this size of project: readable directly, trivial to load with `pandas`, no schema migrations.

**2. Dataset size — 30 customers, 20 merchants, 150 transactions.** Sized to be hand-inspectable (these rows get read directly building the Day 4 eval set) while still producing enough flagged cases for real variance. Much larger would look more "production-like" but adds nothing to the interview story and makes hand-labeling painful; much smaller risks too few flaggable cases.

**3. Seeded generation — `random.seed(42)`, `np.random.seed(42)`, `Faker.seed(42)`.** *Why it matters:* once Day 4's eval labels are tied to specific transaction rows, an unseeded re-run would silently regenerate different data and break every label's connection to its row. *Alternative:* unseeded, regenerate freely — rejected, contradicts `CLAUDE.md`'s own "first run only" convention. *Mindset:* reproducibility isn't a nice-to-have here, it's what keeps a later action (the eval set) from silently breaking because of a decision made days earlier.

**4. Scope boundary respected — `flag_reason` left blank.** Even though it's a Transaction field in the spec's Data Design table, assigning it is Action 6's job (`flagger.py`). Generating it here would've quietly done tomorrow's work early and duplicated logic once the real flagger exists.

**5. Deliberately not-too-clean amounts.** 80% of transactions land within the customer's own typical spend range, 13% in a believable gray zone (1.1×–2× their max), 7% genuinely unusual (2.5×–6× their max) — a smooth spread rather than an "obviously fine vs. obviously fraud" split. *Why:* a cleanly separable dataset would make the rule-based flagger trivially correct and the eval set pointless — it wouldn't test judgment, just thresholds. Verified on the actual output, not just the code: spot-checked the largest transactions against their customer's range and confirmed they land in the intended tier.

**One design choice made independently, worth keeping:** splitting `typical_spend_range` into two numeric columns (`typical_spend_min`, `typical_spend_max`) instead of one range-string field — avoids downstream code having to parse a range back out of a string.

**Files touched this action:**

- `data/generate_data.py` — created.
- `data/customers.csv`, `data/merchants.csv`, `data/transactions.csv` — generated and committed (correctly *not* git-ignored, unlike `.env` — synthetic data needs to stay fixed and shared across the week, not hidden).
- `CLAUDE.md` — `data/` section itemized to list the generator and the three CSVs individually, matching how `src/` is already listed.
- `SCOPE.md` — untouched; nothing here changed scope.

## Action 6 — Write the rule-based flagger

**1. Root-cause fix to the generator, not a workaround in the flagger (reopens Action 5).** Finding 2 showed "new merchant category" would over-trigger because the generator assigned merchants purely at random, with no concept of a customer's usual categories. Rather than patch around that in `flagger.py`, fixed it at the source: `generate_customers()` now assigns each customer 1–2 preferred categories, and `generate_transactions()` biases merchant selection \~85% toward those — the same mostly-normal/occasionally-not shape already used for amount and location, so the generator reads as one consistent design rather than each field inventing its own pattern.

**2. Let the regeneration reshuffle the whole dataset rather than isolate the RNG.** Adding category-affinity calls earlier in the script shifts every later draw in the shared seeded sequence — a real alternative existed (a separate `random.Random(42)` instance just for category picks, to keep the rest of the data byte-identical), but it was rejected as solving a problem the project doesn't have yet: nothing downstream (no eval labels, no flagger) depended on the old values yet. *Mindset:* that line moves once Day 4's eval set hand-labels specific transaction IDs — from that point, regenerating data would warrant RNG isolation or just treating the CSVs as frozen. Worth remembering, not worth building for today.

**3. Velocity threshold set from the actual data, not a textbook default.** A common "≥3 in 24h" rule was checked against the real 150-row dataset first and found to be dead code — no customer had three transactions that close together. Set to ≥2 in 24h instead, confirmed to actually fire on real cases. *Mindset:* a rule that sounds reasonable and a rule that does anything on your actual data are different things — check before trusting.

**4. Chronological, backward-only processing.** Transactions sorted by `(customer_id, timestamp)` and walked forward, so "new category" and "velocity" only ever compare a transaction against that customer's past — never transactions that happen later. Checking against full history including future rows would be a subtle form of data leakage no real-time flagging system could actually have.

**5. One `flag_reason` per transaction, priority-ordered on conflict.** When multiple rules match, priority is velocity → geo anomaly → amount spike → new category — strongest/rarest signal wins, category (still the noisiest, even post-fix) loses every tiebreak. Matches the CSV's single-column schema and Day 4's eval scoring, which checks one cited risk factor.

**6. Verified by hand-tracing actual output, not just reading the code.** Walked customer C014's full transaction history against the real CSV and confirmed every boundary case landed correctly — a 24h12m gap correctly unflagged, a 15h35m gap correctly flagged, `new_merchant_category` correctly suppressed on the first two transactions and correctly firing on the third category switch. Final tally: 53.3% unflagged, 20.0% geo anomaly, 17.3% amount spike, 6.0% velocity, 3.3% new category.

**Two things named honestly rather than left unexplained:** zero `utilities`-category merchants exists by pure chance in this merchant set (harmless — the fallback-to-random-merchant branch already covers it); and the 47% overall flag rate is far higher than a real fraud system's typical low-single-digits — a deliberate scoping choice to guarantee enough flagged variety in a 150-row synthetic set, not a claim about real-world base rates.

**Files touched this action:**

- `data/generate_data.py` — category-affinity logic added (reopening Action 5's design).
- `src/flagger.py` — created: four rules, chronological processing, priority tie-break.
- `data/customers.csv`, `data/merchants.csv`, `data/transactions.csv` — regenerated and re-flagged.
- `CLAUDE.md` — updated.
- `SCOPE.md` — untouched; nothing here changed scope.

## Action 7 — Write the fraud-pattern knowledge base

**1. Four separate files, not one combined doc.** Already fixed by the spec's own file tree, but worth the reasoning, not just compliance: RAG retrieval pulls the single most relevant chunk for a query — one large combined document would force retrieval to return a blended, diluted chunk no matter which pattern actually matched. Four single-topic files are what makes retrieval precise; the file structure is part of the RAG design, not incidental organization.

**2. Consistent three-part structure across all four** (What it is / How it typically shows up / Evidence signals), matching the project's "read like one hand" principle rather than letting each file invent its own shape.

**3. Real gap found and closed — two flag reasons had no directly-named doc.** Checked the four filenames against the flagger's actual four `flag_reason` values rather than assume they'd line up: `velocity_fraud.md` and `geo_anomaly.md` matched directly, but `amount_spike` and `new_merchant_category` had nothing. Rather than leave two of four flag types ungrounded, repurposed `card_not_present.md` to explicitly describe atypically large purchases as a CNP evidence signal, and `account_takeover.md` to describe merchant-category deviation as an ATO evidence signal — both are real, standard fraud-ops associations, not invented for convenience.

**4. Kept the original filenames rather than renaming for 1:1 clarity.** Considered `unusual_amount.md` / `category_deviation.md` instead. Rejected: these four names are specified verbatim in the project spec's own file tree, so renaming would be an unprompted scope/architecture deviation rather than a neutral tidy-up; and functionally irrelevant, since Chroma retrieval matches on embedded content, not filename — the repurposing works regardless of what the files are called. Documented the mapping explicitly in `CLAUDE.md` instead, so the reasoning is visible rather than silently embedded in file content only.

**5. One precision worth keeping separate from the content itself:** card-not-present fraud is technically defined by channel (no physical card presented), not by amount — the amount-anomaly connection used here is a real, commonly-cited correlate, not the term's actual definition. Worth stating precisely if asked, rather than conflating "accurate enough to use" with "the textbook definition."

**Files touched this action:**

- `knowledge_base/card_not_present.md`, `account_takeover.md`, `velocity_fraud.md`, `geo_anomaly.md` — created.
- `CLAUDE.md` — `knowledge_base/` itemized in the file tree; repurposing note added explaining the CNP/ATO mapping; new convention line added about re-checking flagger trigger rates after any data regeneration.
- `SCOPE.md` — untouched; nothing here changed scope.

## Action 8 — Set up Chroma and embed the docs

**1. Embedding function — Chroma's local default, not Gemini's embedding API.** Checked against the actual installed `chromadb==1.5.9` rather than assumed: it defaults to `all-MiniLM-L6-v2` run locally via ONNX automatically when no embedding function is specified — meaning "do nothing extra" and "free, local, no setup" are the same path here, and `onnxruntime` was already a transitive dependency, nothing new to install. *Alternative considered:* Gemini's embedding API, for provider consistency with generation — rejected on scale, not principle: for four short documents embedded once, a network call per embed adds latency and another quota to track for no real benefit; that tradeoff flips at production scale, not here. *Limitation named honestly:* `all-MiniLM-L6-v2` isn't state-of-the-art, but the retrieval task here is coarse (1-of-4 pattern matching), so it doesn't need to be.

**2. Persistent client, not ephemeral.** `PersistentClient` writing to `chroma_db/` rather than an in-memory client that loses state on restart — matching the "embed/generate once, reuse" convention already established for the synthetic data, applied consistently rather than invented fresh for this file.

**3. No chunking — each doc embedded whole as a single chunk.** Deliberately deferred; chunking strategy is explicitly Action 9's job, to be driven by observed retrieval failures, not pre-optimized before any failure exists to fix.

**4. Source metadata attached per entry.** Costs nothing extra now, pays off on Day 3 and beyond — retrieval results can show which file grounded them, supporting the project's own "auditable reasoning" goal.

**5. `upsert()` instead of the originally planned `add()` — a deviation flagged, reviewed, and accepted.** `add()` throws on a duplicate id; `upsert()` overwrites, matching `generate_data.py`'s re-runnable philosophy — safe to re-run after editing a doc, no manual cleanup first. Identical behavior to `add()` on a fresh id, strictly better on a re-run. No downside found, so no reason to force the literal original plan over it.

**6. Self-verification built into the script, not left as a separate manual step.** `collection.get(ids=ids)` checked against the expected id set, raising on any mismatch — catches a silent partial write that a naive "count what we intended to send" success message would have missed entirely.

**Files touched this action:**

- `src/retrieval.py` — created (embedding/setup half; querying is Day 3's addition to the same file).
- `.gitignore` — `chroma_db/` added; fully regenerable from the committed `.md` sources, same category as `.venv/`.
- `CLAUDE.md` — no edit needed; `chroma_db/` is derived runtime state, not part of the conceptual architecture, same reason `.venv/` isn't listed there either.
- `SCOPE.md` — untouched; nothing here changed scope.

## Action 9 — Tune chunking and test retrieval manually

**1. Two-tier testing, not one — and the gap between the tiers was the actual point.** Naive `flag_reason` enum strings were tested first as a deliberate worst case, then realistic natural-language phrasings as what `agent.py` would plausibly construct. Testing only one tier would've either missed the real finding (testing only Tier 2) or wrongly concluded retrieval was broken (testing only Tier 1).

**2. Real finding: not a chunking problem — a query-construction problem.** `amount_spike` (naive) retrieved `velocity_fraud` first and the correct doc (`card_not_present`) second — a genuine miss, confirmed by actual distances, not assumed. The same concept phrased naturally retrieved `card_not_present` correctly at a clear margin. Diagnosed precisely: `card_not_present.md` was already present and ranked second in the failing case, meaning the document content was never the problem — re-chunking wouldn't have fixed a query-side failure. Chunking left alone as a result, correctly, because the data showed it wasn't the actual cause.

**3. A real, evidence-backed requirement surfaced for Day 3, not a guess.** `agent.py` must build natural-language retrieval queries from the flag reason rather than passing the raw enum string to Chroma — proven by this test, not speculated. Written into `CLAUDE.md` now, before `agent.py` exists, so the constraint isn't rediscovered the hard way later.

**4. A near-tie noted honestly rather than treated as a failure.** The fourth Tier 2 query returned `account_takeover` and `card_not_present` within a 0.0001 distance margin — functionally noise. Top-1 was still correct, so nothing failed the action's bar, but connected explicitly to the embedding-model limitation already named in Action 8 (`all-MiniLM-L6-v2` isn't high-precision) rather than left unexplained or quietly ignored.

**5. `n_results=2` used throughout, not just top-1.** Per the plan — catching cases where the top two results sit suspiciously close together, which is a preview of how much the agent can trust retrieval on a genuinely borderline real case, not something a top-1-only check would reveal.

**Files touched this action:**

- `src/retrieval.py` — query half added (`query_knowledge_base`, `_print_query_result`); embed half from Action 8 unchanged.
- `CLAUDE.md` — new convention line added: retrieval queries must be natural-language, not raw flag-reason strings.
- `SCOPE.md` — untouched; nothing here changed scope.

## Day 3 — Topics to revise before Actions 10–13

Pulled from the framework doc's own "Concept Check Before Each Action" table, narrowed to Day 3's four actions.

- Action 10 (Write the two tool-call functions): Tool calling & agent orchestration; MCP (if you use it)
- Action 11 (Wire the agent loop): Tool calling & agent orchestration; Context window & memory
- Action 12 (Design the case-note output format): Evaluation metrics
- Action 13 (Run the agent end-to-end by hand): LLM evaluation (hallucination)

One heads-up worth flagging now rather than when we get there: Action 12's topic — the case-note schema — was already completed in Action 4 (`schemas.py`). The spec lists this task in two places (once under Day 1's architecture sketch, once again as its own Day 3 action). Nothing new to build when Action 12 comes up; we'll just confirm the existing schema still fits and move on.

## Action 10 — Write the two tool-call functions

**1. Native function calling, not an MCP server.** The spec explicitly left this open, naming MCP as "a differentiator, not a deep dive." *Why native won:* the interview story ("an agent that retrieves context through tool calls and reasons over it") is identical either way — the transport layer underneath isn't what's being evaluated — and Day 3 still has to fit wiring the full agent loop and a manual end-to-end run into the same day. MCP stayed a real, spec-named option, not something quietly skipped; just not worth the added server/client wiring for no change in what the agent actually does.

**2. Dicts always, exceptions never.** Both functions return `{"error": "..."}` on a missing id rather than raising — verified by tracing both failure paths against real output, not just trusting the design intent. Keeps a missing-data case something the agent reasons about as part of normal flow, not a crashed request — consistent with `CLAUDE.md`'s existing "deterministic and boring" convention for this file.

**3. `lookup_customer_history` returns transaction history, not just the static profile.** A judgment call beyond the spec's literal field list: returning up to 10 recent transactions lets the agent judge whether a flagged transaction looks unusual for that specific customer, rather than just echoing what the flagger already decided. Verified against the real CSV, not just the printed output — all 5 of C001's returned transactions cross-checked against `transactions.csv` directly, including a correct same-day, different-hour sort order (Sep 27 14:08 before Sep 27 02:13).

**4. The 10-transaction limit — a specified judgment call, and its untested path was characterized precisely, not just flagged.** Chosen as "enough to show a pattern, not enough to bloat the response" — not specified anywhere in the plan. Initially flagged as "this test didn't exercise truncation"; checked further against all 150 transactions and found the real shape of the gap: no customer in the dataset has more than 10 transactions, so the branch is untested by the data structurally, not just by this one run. Left as-is deliberately — `list[:10]` is well-defined standard-library behavior with no real failure mode to catch, so fabricating an 11+-transaction test customer would cost effort against near-zero actual risk. *Mindset:* flagging an untested path is the right instinct, but the next step is sizing the actual risk before deciding whether it's worth closing — not every gap needs to be filled, but every gap should be named accurately.

**Files touched this action:**

- `src/tools.py` — created.
- `CLAUDE.md` — no edit needed; `tools.py` was already itemized in the file tree since Day 1, nothing about structure or usage changed.
- `SCOPE.md` — untouched; nothing here changed scope.

## Action 11 — Wire the agent loop

**1. Native function calling, not MCP — same call as Action 10, applied consistently.** The spec's "Tools" column named Anthropic/OpenAI's native tool-calling specifically; translated faithfully to Gemini's actual API shape (`FunctionDeclaration`, `types.Tool`, `FunctionResponse`) rather than assuming the SDKs are interchangeable.

**2. Two-phase call structure — tool-calling phase, then a separate generation phase.** Checked whether Gemini can combine `tools` and `response_schema` in one call before building around either assumption, rather than discovering a conflict mid-build: found this genuinely inconsistent across model versions (confirmed broken on 2.5 models in an official forum thread, reportedly working on at least one newer model). Splitting into two calls sidesteps the question entirely — whether or not `gemini-3.8-flash` specifically could combine them stopped mattering, since the design never attempts it.

**3. Manual function-calling loop, not the SDK's automatic mode.** Deliberate: the project's goal is being able to explain the mechanism in an interview, not just get an answer out of it — each step (model requests a call, code executes it, result goes back) stays explicit and visible in the code rather than hidden inside SDK automation.

**4. Straight-line assumption, no branching — matching the spec's own instruction.** The loop assumes both tools get called every time, with no retry or defensive handling if the model skips one. Deliberately left for Action 13's real test to surface, rather than coded around speculatively.

**5. Model choice checked twice, not once — capability first, then actual account capacity.** `gemini-3.8-flash` verified as a real, GA model supporting both function calling and structured output. A second, more consequential check followed: two independent sources reported this model's free-tier daily cap as low as 20 requests — checked directly against the real account rather than trusted either the model's marketing or an unverified forum number. Actual quota came back at 100 RPD / 60 RPM / 100K TPM — comfortable for today's test, worth watching specifically on Day 4's larger eval run, with the project's own already-budgeted "few dollars of API credit" as the fallback if free-tier capacity becomes the actual bottleneck then.

**6. One version-specific detail surfaced, not acted on — correctly, pending real evidence.** Gemini 3-era models attach a unique id to each function call for correlating parallel calls to their responses; documentation suggests the official SDK handles this automatically. Noted as the first thing to check if Action 13's real run ever shows the model confusing which result belongs to which tool — not treated as a bug to fix preemptively without evidence it's actually a problem.

**Files touched this action:**

- `src/agent.py` — created: retrieval + two-phase tool-calling/generation loop.
- `CLAUDE.md` — no edit needed yet; `agent.py` was already itemized in the file tree since Day 1.
- `SCOPE.md` — untouched; nothing here changed scope.

**Action 12 note:** stays a pass-through, as flagged in the Day 3 topics note — the case-note schema was already built in Action 4, nothing new to do here.

## Action 12 — Design the case-note output format

Pass-through — already completed in Action 4 (see that entry above), where the case-note schema (`src/schemas.py`, the `CaseNote` Pydantic model) was built as part of sketching the architecture decisions. The spec lists this task in two places — once inside Action 4's "sketch the architecture decisions," once again here as its own standalone action. Nothing new was built; the existing schema was confirmed to still fit before moving on, per the Day 3 topics note flagged in advance.

## Action 13 — Run the agent end-to-end by hand

**1. Four transactions run, one per flag type — matching the spec's own suggested scope.** `T0002` (geo\_anomaly), `T0014` (amount\_spike), `T0055` (new\_merchant\_category), `T0018` (velocity\_spike). Every run verified against the actual CSVs, not just read for plausibility — customer profiles, spend ranges, merchant data, and specific factual claims in the generated reasoning all cross-checked against real rows.

**2. Both tools called, correct document retrieved, numbers accurate — on all four runs, no exceptions.** Confirms Actions 9–11's design decisions actually hold under real execution, not just in reviewed code: natural-language retrieval queries (Action 9) correctly grounded every case in the right knowledge base doc, and the two-phase tool-calling/generation split (Action 11) reliably executed both tools every time.

**3. Genuine judgment observed, not just threshold-matching — the strongest single finding.** On `T0014`, the model independently found a mitigating data point in the customer's own transaction history (a comparable prior purchase) and lowered its confidence score accordingly (0.65 vs. 0.85 on a cleaner case) — reasoning from evidence, not pattern-matching a fixed template. Verified as a real, specific, checkable claim, not vague filler.

**4. One reasoning gap found and precisely diagnosed, not smoothed over.** On `T0018`, one of two cited risk factors ("repeated visits to the same merchant") actually contradicts `velocity_fraud.md`'s own evidence signals, which frame cross-merchant bursts as the suspicious pattern — not same-merchant repeats. The model retrieved the correct document but cited a risk factor inconsistent with it. The final recommendation still held up on other grounds, but this is a real, specific weakness in grounding, not assumed away because the outcome looked fine.

**5. Deliberately not patched based on one observed case.** A single run isn't enough signal to safely tune a prompt against — doing so risks overfitting to one example. Logged as a specific thing to watch for once Day 4's 15–20 case eval set provides enough volume to tell whether this recurs systematically or was a one-off. Matches the project's own Day 6 philosophy: fix what the eval actually exposes, not what one anecdote suggests.

**6. Infrastructure findings along the way, not just agent-quality findings.** A real `ModuleNotFoundError` traced to its actual cause (cross-module imports requiring `python -m src.agent`, not a direct script path) — fixed in both the code and its own docstring, plus a new `CLAUDE.md` convention so this isn't rediscovered on `eval/run_eval.py` later. Also the free-tier model swap from `gemini-3.8-flash` to `gemini-3.5-flash-lite`, and the lesson behind it: a quota error from the API itself outranks a dashboard reading — the console showed 100 RPD, the actual enforced limit was 20, discovered only when the real quota-exceeded error arrived mid-run.

**Files touched this action:**

- `src/agent.py` — `MODEL_NAME` switched to `gemini-3.5-flash-lite`; docstring corrected to the module-run command.
- `CLAUDE.md` — new convention added: cross-module `src/` scripts must run as `python -m src.<name>`.
- `SCOPE.md` — untouched; nothing here changed scope.

## Day 4 — Topics to revise before Actions 14–17

Pulled from the framework doc's own "Concept Check Before Each Action" table, narrowed to Day 4's four actions.

- Action 15 (Write the guardrail): Guardrails
- Action 16 (Build the eval set): Evaluation metrics; LLM evaluation
- Action 17 (Write and run the eval script): LLM evaluation

Action 14 has no tied topic in the framework — wrapping the agent in FastAPI is integration work, not a new concept.

## Action 14 — Wrap the agent in FastAPI

**1. Scope stayed exactly where the spec and `SCOPE.md` drew it.** One endpoint, `POST /review/{transaction_id}`, nothing else — no health check, no extra routes, even though a deployment platform might eventually want one. Deliberately not added now; that's a one-line addition to make later, with a real reason, not preemptively.

**2. Sync `def`, not `async def` — checked rather than defaulted to whichever looked more "modern."** Everything `agent.py` does (Gemini SDK calls, Chroma, CSV reads) is blocking, not async. FastAPI runs a sync `def` path function in its own thread pool automatically; an `async def` wrapping blocking calls would silently block the event loop instead — a mistake a single curl test under no load would never reveal.

**3. A typed Pydantic response model mirroring `draft_case_note()`'s exact proven shape, not a bare dict.** Extends the same Pydantic-everywhere convention `schemas.py` already established, one layer outward — gets automatic request/response validation and interactive docs for free, without reshaping anything that was already proven correct in Action 13.

**4. The `{"error": ...}` convention deliberately translated at the HTTP boundary, not carried through unchanged.** `tools.py`/`agent.py`'s "return a dict, never raise" exists so the agent can reason about missing data as part of its normal flow — that reasoning doesn't apply the same way one layer up, where an HTTP API signaling "not found" is supposed to mean a status code. Not a contradiction of the earlier convention, the equivalent convention at a different layer.

**5. No defensive handling around a genuine agent failure.** An exhausted retry in `generate_with_retry` propagates into an honest 500, not caught and smoothed over — same "straight line first, handle what testing actually reveals" philosophy as every action since Action 11.

**6. Both paths verified for real, not just reviewed as code.** The success path reproduced T0002's exact facts (home location, spend ceiling, the same T0102 same-day cross-check) through a completely different code path than Action 13's direct script call — confirms the API layer adds nothing that breaks what was already proven. The 404 path was initially untested — flagged as a real gap, since this was the first `HTTPException` anywhere in the codebase and reviewed code isn't confirmed behavior — then explicitly tested and confirmed correct.

**7. `CLAUDE.md` needed no edit, which is itself a genuine confirmation.** The "How to run it locally" section already documented this exact `uvicorn`/`curl` usage before `api.py` existed, written as a forward-looking placeholder back on Day 1. It turned out to already be true — a sign the plan and the build stayed in sync, not something to take for granted.

**Files touched this action:**

- `src/api.py` — created.
- `CLAUDE.md` — no edit needed; already accurate from Day 1.
- `SCOPE.md` — untouched; nothing here changed scope.

## Action 15 — Write the guardrail

**1. Redaction target corrected from the spec's literal example to this project's actual data.** The spec named "card numbers"; this schema has none (no real financial data, per `SCOPE.md`). The PII that actually appears in every case note — the customer's name — is what gets redacted instead. Honors the spec's intent (protect PII) over an example that assumed data this project deliberately never collected.

**2. Two violation types, two deliberately different responses.** PII found → silently redact and return (safe: a name is a swappable noun). Fraud-assertion language found → raise `GuardrailViolation`, never auto-rewrite (unsafe: regex-patching an arbitrary matched phrase into "compliant" wording could silently change meaning no one reviews). A loud failure is more auditable than a silent patch — consistent with the project's whole "human makes the final call" premise.

**3. Runs inside `agent.py`, not `api.py` — so every call path is protected, not just the HTTP one.** Matches both the architecture's own Generate → Guardrail stage ordering and a practical concern: a guardrail that only lives in the API layer would let Action 13-style direct script runs bypass it entirely.

**4. A real false-positive bug found through adversarial testing, then fixed and re-verified.** The initial regex matched `fraud` at any word boundary, with no check for what followed — meaning hedged, explicitly-permitted language like "fraud risk" would have wrongly triggered a violation, directly contradicting the guardrail's own stated intent. Caught by testing the exact phrase the docstring claimed should pass, not just testing phrases expected to fail. Fixed with a negative lookahead excluding specific safe continuations, then verified with three targeted test cases — the original false positive, a clean true positive, and a case overlapping two patterns at once.

**5. Testing methodology itself was a deliberate choice, not incidental.** Direct unit tests against the guardrail function, rather than relying on live model output, isolate the regex's correctness from the model's nondeterminism — stronger evidence than "I ran it and it happened to work today."

**6. One limitation named honestly, not hidden.** Regex-based detection can only catch phrasings someone anticipated; a sufficiently novel assertion could still slip through. Inherent to the method, not a defect in this implementation — worth being able to state precisely rather than imply the guardrail is complete.

**Files touched this action:**

- `src/guardrail.py` — created: `check_fraud_language`, `redact_pii`, `GuardrailViolation`.
- `src/agent.py` — guardrail wired into `draft_case_note()` right before return; `MODEL_NAME` comment corrected to properly attribute the model-switch decision to Action 13.
- `CLAUDE.md` — no edit needed; the guardrail convention ("code-level, never prompt-only") was already written down back on Day 1, and this action is exactly that promise being fulfilled.
- `SCOPE.md` — untouched; this is precisely the one committed guardrail it already named.

## Action 16 — Build the eval set

**1. JSON over a spreadsheet — already settled by the project's own file tree, not re-decided.** `eval/eval_set.json` fits the codebase's grain: everything downstream is Python, Action 17's scorer loads it with one `json.load()` call, no conversion step.

**2. The central decision: ground truth ≠ "the flagger was right."** The flagger was deliberately built dumb on purpose (Action 6); treating its output as automatically correct would make the eval set test whether the agent parrots a rule already in its prompt, not whether it exercises real judgment. Ground truth is what a reasonable analyst would conclude after reading full context — explicitly allowed to diverge from the flag, same as the agent's own real Action 13 output already did on 2 of 4 cases.

**3. Selection deliberately spread, not arbitrary.** All four flag types represented (5/10/4/4 split across geo\_anomaly, amount\_spike, velocity\_spike, new\_merchant\_category), only flagged transactions considered, and a real mix of clear-cut and genuinely ambiguous cases — directly cashing in Action 5's "deliberately not-too-clean" data design.

**4. A real inconsistency caught mid-process, then resolved by deriving a general rule — not by picking a side.** T0086 and T0023 were initially called opposite ways despite sharing the same underlying shape (normal amount, one binary flag-type anomaly, a static high-risk merchant tag as the only other signal). Re-traced from scratch rather than defended either original call, arriving at an explicit, falsifiable standard: a static merchant risk tier only justifies escalation when it reinforces a genuine behavioral anomaly, not when it's the sole signal next to otherwise-normal activity. T0086 flipped to `clear` to match. The rule was then checked against the rest of the set (T0014, T0079, T0112, T0133) and held consistently — confirming it's a real principle, not a patch for two cases.

**5. Quantified reasoning preserved in the file itself, not compressed into vague restatements.** Every entry cites the actual ratio, dollar amount, or account-age figure behind the call (e.g., "about 55% over typical max," "28 days old") rather than qualitative impressions — makes any future agent/label disagreement during Action 17 actually debuggable instead of a bare assertion to take on faith.

**6. One ungrounded claim caught and corrected before the file was finalized.** T0011's reasoning initially asserted the flagged location was "close to home" — a plausible-sounding inference with no basis in the data, since `flagger.py`'s `geo_anomaly` rule is a flat string mismatch with no distance modeling anywhere in the system. The verdict (clear) was already correct for the right reason; only the stated justification needed fixing to not claim something the system doesn't actually know. Same standard already applied to the model's own output in Actions 13 and 15, now applied to this file too.

**7. The finished set isn't escalation-biased.** 7 escalate / 11 clear — an agent that reflexively escalated every case would score poorly against this file, confirming it tests judgment rather than rewarding caution.

**Files touched this action:**

- `eval/eval_set.json` — created, 18 labeled cases.
- `CLAUDE.md` — no edit needed; already documents the eval set's existence and purpose from Day 1.
- `SCOPE.md` — untouched; nothing here changed scope.

## Action 17 — Write and run the eval script

**1. Scoring metric kept exactly as simple as the spec asked.** Recommendation-direction accuracy, exact string match — no weighted scoring, no partial credit, matching "don't over-engineer the scoring logic, a simple match is enough for a project this size."

**2. A circular-metric trap caught before it was built, not after.** The obvious secondary check — comparing `case_note.flag_reason` to `expected_flag_reason` — doesn't test anything: `flag_reason` is handed to the model directly in the prompt, so it always echoes back correctly regardless of actual reasoning. Replaced with a shallow keyword-presence check against `risk_factors`/`evidence` instead, explicitly labeled informational-only and kept deliberately unsophisticated, consistent with the spec's own scope boundary.

**3. Error handling deliberately broke from every prior component's pattern, for a stated, specific reason.** `agent.py`/`api.py` let genuine failures propagate uncaught, on purpose, since each handles one case and a clean failure beats a smoothed-over one. `run_eval.py` inverts this deliberately: its job is one complete scorecard across 18 cases, so failures are caught and recorded per-case instead. Not an inconsistency — a different component with a genuinely different contract.

**4. Accuracy computed over scored cases only, with the exclusion made impossible to miss, not buried.** An API quota error isn't a judgment failure and shouldn't dilute a quality metric — but a results count below the total is now flagged explicitly in the report's own output, closing a real gap where an early partial run printed a misleadingly clean "PASSED: 100%" at 2 of 18 cases scored.

**5. Two separate, real infrastructure limits discovered only by running at the batch volume this script is first to reach.** A daily cap (confirmed in Action 13) and a previously-unknown per-minute cap (15 RPM) — the second only surfaces under batch calling, which no single-transaction run had ever produced before. The fix (pacing between calls) was deliberately kept script-local rather than pushed into `agent.py`, since single-transaction calls never approach 15 RPM — solving it in the shared component would have fixed a problem that component doesn't have.

**6. The pacing fix was tuned empirically against what was actually observed, with the mismatch between theory and reality stated plainly rather than papered over.** Naive math (3 calls/case, 15/minute cap) suggested a 15s delay should hold; a real run showed it didn't — failing on case 6, not where the math predicted. Rather than invent an explanation for the discrepancy, the fix was pushed to a larger empirical margin (30s) and the gap in understanding was written down as a gap, not hidden behind a plausible-sounding guess.

**7. A `--only` flag built specifically in response to the quota constraints this action kept running into.** Lets a future run retry just the cases that failed without re-spending quota on everything that already scored — directly useful for Day 6's planned investigation, not a speculative feature.

**8. The honest result: 61.1% (11/18), below `SCOPE.md`'s 80% bar — reported as the real finding it is, not treated as something to fix before calling the action done.** Two specific, non-overlapping patterns identified from the pass/fail breakdown alone: `new_merchant_category` failing in both directions (not a single systematic bias), and `amount_spike`'s two misses sharing a specific shape (low-risk merchant, escalated on amount magnitude alone, agent cleared both). Both are real, numbers-backed findings, not vague impressions.

**9. A deliberate decision not to investigate further tonight, reasoned rather than just asserted.** The plan itself separates measurement (Day 4) from investigation/fixing (Day 6) on purpose; reasoning-quality work (judging whether five pieces of model reasoning were sound) is exactly the kind of task that degrades quietly with fatigue, unlike mechanical work; and nothing is actually lost by waiting, since the finding — plus the exact command to resume investigating it — is already durably written into `CLAUDE.md`.

**Files touched this action:**

- `eval/run_eval.py` — created: scoring, per-case error handling, request pacing, `--only`/`--limit`/`--delay` flags, live progress output.
- `eval/__init__.py` — created, enabling reliable `python -m eval.run_eval` module resolution.
- `CLAUDE.md` — run commands updated for `flagger.py`/`retrieval.py`/`run_eval.py`; new "Known gaps (dated)" section added with the full eval finding and the exact re-investigation command.
- `SCOPE.md` — untouched; the eval set's existence and its 80% bar were already named here from Action 1.

## Day 5 — Topics to revise before Actions 18–21

Pulled from the framework doc's own "Concept Check Before Each Action" table, narrowed to Day 5's four actions. Unlike prior days, all four actions have a tied topic — no pass-throughs today.

- Action 18 (Write the Dockerfile and build locally): Containerization & deployment
- Action 19 (Deploy to a free-tier host): Containerization & deployment; One cloud platform
- Action 20 (Set up CI): CI/CD
- Action 21 (Split dev/prod config): Environments (dev/staging/UAT/prod)

## Action 18 — Write the Dockerfile and build locally

**1. Base image — `python:3.12-slim`, matched deliberately to the real `.venv` version, not assumed.** Confirmed via the `.venv` path visible in prior tracebacks, not guessed. `alpine` was considered and rejected on a concrete, dependency-specific basis: `onnxruntime` (pulled in by `chromadb`) ships prebuilt wheels for `glibc`, not `musl`, so alpine would likely force a slow, fragile source build instead of a normal install.

**2. Layer order — dependencies installed before code is copied, for a measured reason, not just convention.** The build log's own timing proves the point: `pip install` took 135.9s, the single slowest step by far. Caching that layer separately from code means future code-only rebuilds skip it entirely.

**3. The real decision of this action: bake the knowledge base into the image at build time.** Left as a runtime-only step, `chroma_db/` being git-ignored would have meant `get_or_create_collection()` silently creating an empty collection in a fresh container — no error, no warning, just an ungrounded agent. `RUN python src/retrieval.py` inside the Dockerfile closes that gap, and the real curl response against the running container (correct `fraud_pattern_source`, correct retrieved content) confirms it worked, not just that the step ran.

**4. `.dockerignore` written as a parallel structural safeguard to `.gitignore`, for the same underlying reason.** Without it, `COPY . .` would have copied `.env` — the real API key — directly into the image. Same instinct as Action 2, applied to a second place secrets can leak into, not just the one already covered.

**5. Explicit `0.0.0.0` binding — a failure mode that would have looked identical to success otherwise.** Uvicorn's default (`127.0.0.1`) only accepts connections from inside the container; the container would have built cleanly and run with no errors, while being completely unreachable from outside. The real curl request succeeding confirms this specific, easy-to-miss default was actually overridden, not just written as an intention.

**6. A real architectural dependency surfaced and flagged for Day 5, not discovered after the fact.** The build log's own 37.4s timing on the embedding step confirms Chroma's embedding model downloads over the network during the build — meaning this Dockerfile has an internet-access requirement at build time, not just at runtime. Worth remembering specifically when Day 5 runs this same build inside GitHub Actions' CI environment, which may behave differently than a local Docker Desktop build.

**7. Dev-only dependencies (`faker`, `pytest`) left in the production image — a deliberate choice, not an oversight.** A split prod/dev requirements file is the "more correct" pattern in isolation, but for a project this size, two files to keep in sync is real complexity for a trivial image-size saving. Worth being able to name as a conscious tradeoff if asked, not something overlooked.

**8. Verified at every level the plan called for, not just one.** Build succeeded (log), container ran (startup log), and the actual HTTP response was correct — right data, right redaction, right grounding, matching every fact already verified in Actions 13–15. "The build succeeded" and "the app actually works in the container" were treated as separate claims requiring separate evidence, not assumed to imply each other.

**Files touched this action:**

- `Dockerfile` — created.
- `.dockerignore` — created.
- `CLAUDE.md` — no edit made yet; worth a line noting the build's network dependency for Day 5, flagged for when Action 19/20 actually hits it.
- `SCOPE.md` — untouched; containerization was already named in scope from Action 1.

## Action 19 — Deploy to a free-tier host

**1. Host choice checked against current reality, not the spec's phrasing taken at face value.** All three spec-named options (Render, Fly.io, Railway) were verified rather than assumed interchangeable — Fly.io no longer offers a free tier for new accounts at all; Railway's "free" is a one-time $5 trial credit then $1/month, not an ongoing tier. Render was the only one of the three still genuinely free, confirmed against current sources rather than trusted from memory — the same discipline the Gemini quota saga forced earlier this week, applied proactively this time instead of reactively.

**2. Deployed via Docker, reusing Action 18's exact validated build rather than introducing a second build path.** No new Dockerfile, no buildpack configuration — Render builds directly from the existing, already-proven `Dockerfile`.

**3. The `0.0.0.0` vs. port-number question checked specifically, given Action 18's binding mistake was exactly this category of error.** Confirmed from Render's own docs that it auto-detects whatever port the server binds to, as long as it's `0.0.0.0` — already correct from Action 18. No Dockerfile change needed; avoided fixing a problem that didn't exist.

**4. A deliberate, explained deviation from the spec's literal "deploy hello-world first" instruction.** Reasoned that "my app is wrong" was no longer a live unknown — `agent.py` and the Docker image were both already thoroughly tested — so the real remaining risks were platform-specific (build-time network access, env var injection, port detection), none of which a hello-world endpoint would have exercised differently than the real app. Deployed the real app directly; flagged the deviation rather than silently following or silently skipping the spec.

**5. Every platform-specific risk named in advance was individually confirmed, not assumed to have worked because the overall deploy succeeded.** The build-time network dependency (the \~83MB ONNX model download) held up on Render's infrastructure — confirmed indirectly but validly, since a `RUN` step failure would have killed the build outright, and `fraud_pattern_source` came back correct. Env var injection via Render's dashboard worked, confirmed by a successful real Gemini call with no `.env` file anywhere in the deployed image.

**6. An apparent anomaly (two byte-identical responses, including a shared typo) was investigated rather than waved past.** Re-tested with `-w "%{time_total}s"` and genuinely independent follow-up calls; the resulting responses differed in wording, reasoning, and confidence score (0.85 vs. 0.65), correctly ruling out caching or duplication — confirming the first pair was coincidence on a short, simple case, not a bug.

**7. A real, significant latency finding — properly diagnosed, not just measured.** Per-request latency on Render measured at 63–108 seconds. Initial hypothesis (free-tier compute being slow) was tested and ruled out directly: a local run via `time python -m src.agent T0002` showed near-identical wall-clock time (64.55s) despite running on full dev hardware with only 1.45s of actual CPU time (2% utilization) — proving the bottleneck is inherent to the architecture's 3–4 sequential Gemini round-trips per request, not where it's deployed. A wrong-but-plausible explanation was tested and discarded before the real one was written down.

**8. The finding's practical implication was traced through to its actual consequence, not left as a standalone fact.** At this per-request cost, pointing any batch process (the eval script, a future CI job) at the live HTTP endpoint would take 20–35+ minutes for an 18-case run. Confirmed `eval/run_eval.py` already avoids this by calling `draft_case_note()` directly rather than through HTTP — Action 17's design held up as the right call for a reason that wasn't even known at the time it was made.

**Files touched this action:**

- `Dockerfile` — unchanged; confirmed to work as-is, no edit needed.
- `CLAUDE.md` — new "Known gaps" entry added documenting the measured latency, its diagnosed cause, and the resulting guidance to never batch-call the live endpoint.
- `SCOPE.md` — untouched; deployment was already named in scope from Action 1.

## Action 20 — Set up CI

**1. The spec's literal instruction ("run your eval script on every push") was checked against real cost before being followed, and found non-viable as written.** A full 18-case run would burn \~50+ calls and 20–35+ minutes per push — a single day of normal iteration could exhaust the day's entire Gemini quota on CI alone. Action 17's `--only` flag — built two actions earlier for a different purpose — was reused for its actual intended situation: a small, representative subset instead of the full set.

**2. A real branch + PR workflow was used for the first time in the project, not just documented as a convention.** `CLAUDE.md` has said "branch + PR for every change, even solo" since Day 1; `ci-eval-gate` is the first commit sequence to actually follow it rather than going straight to the main line.

**3. A real, iterative debugging process, not a one-shot success — four distinct failures, each correctly diagnosed before being acted on:**

- **Missing `GEMINI_API_KEY` secret** — diagnosed from a 2m15s total duration being too short for any real Gemini call to have occurred, confirmed by checking GitHub's secrets settings directly rather than guessing.
- **A genuine YAML syntax bug** (an unquoted colon-space sequence inside a step name) — diagnosed precisely as a real parser-level ambiguity, not just "a typo," and fixed by moving the detail into a comment instead of the string.
- **Two consecutive live case flips** (T0014, then T0078) — each initially investigated as a possible case-selection mistake, correctly re-diagnosed as genuine Gemini non-determinism once the pattern repeated on a second, independently-chosen "safer" case.

**4. A case-selection fix was tried first, discovered to be the wrong level of fix, and escalated to a structural one — reasoning that held up under its own result.** Swapping `T0014` for a presumed-more-decisive `T0078` didn't resolve the flakiness — it relocated it. That outcome was treated as a real signal, not as a reason to keep guessing at a third case: recognized that a 4-case, "all-must-pass" gate was silently enforcing \~100% rather than the spec's actual 80% threshold, and that no case-swap could fix that mismatch, only widening the sample could.

**5. Widened to 6 cases, deliberately not to a round 8 — reusing confirmed evidence rather than introducing new untested cases.** The second `geo_anomaly` and `amount_spike` picks both had real prior data behind them; `velocity_spike` and `new_merchant_category` were left at one case each specifically because padding them further would have meant blind guesses with zero supporting history — trading a known, understood problem for a new, unknown one.

**6. The fix was proven, not assumed — a passing run that absorbed a real, live flip is stronger evidence than a clean pass would have been.** The final run showed T0014 failing again (its third real flip in three attempts) while the overall gate still correctly passed at 83.3% — direct confirmation the threshold now does what it's supposed to, under the exact condition that broke it twice before, not just in the absence of that condition.

**Files touched this action:**

- `.github/workflows/ci.yml` — created, debugged through four real failures, and widened from an initial 4-case design to 6 cases based on live evidence.
- `CLAUDE.md` — new "CI" section documenting the workflow and the 4→6 case-count decision; new "Known gaps" entry recording the confirmed non-determinism (T0014's three flips, T0078's two); new convention added — a red CI run needs human triage against known-borderline cases, not an assumption something broke.
- `SCOPE.md` — untouched; CI/CD was already named in scope from Action 1.

## Action 21 — Split dev/prod config

**1. Framed honestly as closing gaps in an already-emergent split, not building one from scratch.** The real dev/prod separation — `.env` locally, Render's dashboard, a GitHub Actions secret — had already been happening reactively since Actions 18–20, each piece built when its action demanded it rather than planned as one step. Today's job was named precisely: confirm the mechanism is sound, close what was never actually done, document it clearly.

**2. The one genuine gap: `.env.example` had been named in the project's own file tree since the original spec, but never actually created, across 20 prior actions.** Closed with a minimal placeholder file — no real values, just the expected shape.

**3. The underlying mechanism was verified using evidence already in hand, not a fresh assumption.** Whether `load_dotenv()` breaks when no `.env` file exists (the exact situation in the deployed container, where `.dockerignore` correctly excludes it) was confirmed by recognizing that Action 19's successful Render deployment already proved this — real evidence repurposed and named explicitly, rather than treated as a new claim needing its own separate test.

**4. A second, smaller gap closed alongside the first: `CLAUDE.md`'s "How to run it locally" never told a new developer to create `.env` or what to put in it.** Added as a genuine first step before `pip install`, not tacked onto the end as an afterthought.

**5. A deliberate scope boundary, named rather than silently respected.** Considered and explicitly rejected inventing new environment-conditional behavior (different logging per environment, etc.) just to make the action feel more substantial — that's Action 22's explicit territory on Day 6, and doing it today would duplicate effort once that action actually arrives, the same over-eager-scope mistake already caught and corrected back in Action 5.

**6. One precise distinction worth keeping, surfaced by actually checking rather than assuming the file was complete:** `PORT` is a real, environment-specific value in this system, but it's provided by Render to Render's own routing layer — never read by this codebase — so it correctly requires no entry in `.env.example`. The split documents what an engineer must supply; it correctly excludes what the platform supplies to itself.

**Files touched this action:**

- `.env.example` — created.
- `CLAUDE.md` — "How to run it locally" section gained a first-run `.env` setup step.
- `SCOPE.md` — untouched; nothing here changed scope.

## Day 6 — Topics to revise before Actions 22–24

Pulled from the framework doc's own "Concept Check Before Each Action" table, narrowed to Day 6's three actions.

- Action 22 (Add logging): Observability
- Action 23 (Fix what the eval and guardrail testing exposed): Debugging with AI — already one of the four "applies throughout the week" topics flagged back on Day 1, not a new one to skim
- Action 24 (Reread Day 1 notes on the Know-tier topics): Quantization & vLLM; Inference optimization (Triton, ONNX); Fine-tuning landscape; Data governance; Basic SQL — this action *is* the reading itself, same situation as Day 1's Action 3

## Action 22 — Add logging

**1. Logging placed in `api.py`, not `agent.py` — a different call than Action 15's guardrail placement, and deliberately distinguished rather than copied.** The guardrail is a correctness concern needing protection on every call path; logging is specifically about production request handling, and Render only ever runs `api.py` in production — so that's the one place it needs to live.

**2. Token cost required accumulating across multiple Gemini calls, not reading one response.** `draft_case_note()` makes 2–4 calls per request across its two-phase design; `total_tokens` sums `usage_metadata` from each one as it happens, following the same incremental-return pattern already used for `tools_called` and `fraud_pattern_source`.

**3. A real, concerning-looking log line (`AFC is enabled...`) was investigated rather than either ignored or treated as broken.** Checked against Action 11's explicit manual-loop design, found a documented upstream SDK quirk (the message fires regardless of `disable=True`), then verified independently using first-party evidence already in the code — `tools_called` is only ever populated inside the manual loop itself, so its correct population on every real run is direct proof the manual loop executes, not an inference from an unreliable log line. Documented in both `agent.py` and `CLAUDE.md` so this doesn't cause false alarm later, including to someone watching raw logs without ever opening the source.

**4. A real, verified gap found by tracing the actual control flow, not just reading the code for plausibility: token cost silently disappeared on the guardrail-violation path.** `check_fraud_language()` raising `GuardrailViolation` means `draft_case_note()` exits via exception before reaching its `return` — `total_tokens`, a local variable, dies with the stack frame. The exact failure mode most worth tracking cost on (real Gemini calls already spent before the violation) was the one case where cost went untracked.

**5. The fix was scoped narrowly and verified directly, not assumed correct because the code compiled.** `total_tokens` attached to the exception object itself before re-raising, read back via `getattr` in `api.py`. Confirmed with an isolated unit test against `check_fraud_language()` directly — same methodology as Action 15's guardrail false-positive test — rather than waiting for a live model response to happen to trigger a violation.

**6. A real design choice — excluding `total_tokens` from the HTTP response — was made deliberately and recommended, not left as an accidental oversight.** Reasoned from who actually consumes each surface: the response serves the reviewing analyst, for whom token cost is irrelevant to the escalate/clear decision; the log serves ops, which is exactly what it's for. Extends `CaseReviewResponse`'s existing Action 14 boundary (a deliberate subset of the full return shape) rather than quietly expanding it just because a new field existed.

**7. All three real paths — success, 404, guardrail violation — verified independently with live or isolated tests, not assumed from code review alone.** Matches this project's standing rule: reviewed code and confirmed behavior are different claims, and every action gets both before being called done.

**8. The `CLAUDE.md` write-up itself was caught overclaiming and corrected before being logged.** An initial draft described one universal set of logged fields; checked against the three actually-different log shapes the code produces (success, not-found, guardrail violation) and rewritten to describe each precisely — worth noting as a small instance of the same discipline applied to documentation, not just code.

**Files touched this action:**

- `src/api.py` — structured JSON logging added across all three response paths; `CaseReviewResponse` docstring updated to state the `total_tokens` exclusion is deliberate.
- `src/agent.py` — token accumulation added across both phases; `GuardrailViolation` now carries `total_tokens` as an attribute before re-raising; new note documenting the AFC log-line quirk.
- `CLAUDE.md` — new "Logging" section added, describing all three log shapes precisely and cross-referencing the AFC quirk.
- `SCOPE.md` — untouched; observability was already named in scope from Action 1.

## Action 23 — Fix what the eval and guardrail testing exposed

**1. A real gap in the action's own tooling was caught before it caused wasted effort, not after.** The investigation started by running `eval/run_eval.py --only <5 ids>` — the exact command `CLAUDE.md` had been pointing at since Action 17. It confirmed the failure counts (1/5) but produced no case-note text, because Action 20 deliberately built that script to stay minimal for CI. Caught before drawing any conclusions from it, and redirected to `python -m src.agent <id>` — a tool that already existed, reused rather than building something new.

**2. Diagnosis was done from real reasoning text across all five misses together, not from one case or from the pre-written hypothesis.** `CLAUDE.md`'s own standing theory ("anchoring on low merchant risk tag") was checked against the actual evidence text from all four genuine failures and didn't hold up against any of them — no case named merchant risk tier as the deciding factor. The theory was replaced, not patched.

**3. Two genuinely different bugs were found and correctly distinguished, rather than treated as one shared cause.** T0078: merchant familiarity treated as mitigating without checking whether prior amounts were actually comparable in size. T0133: the correct signal (account-takeover pattern, 28-day account age) was identified and named, then didn't influence the verdict. Different failure shapes, both confirmed from real text, both addressed with their own targeted sentence in the prompt fix — not a single generic patch applied to both.

**4. One case was correctly identified as not a bug at all, and the eval set itself was corrected instead.** T0143's original `escalate` label came from a static per-customer ceiling comparison; the agent's own evidence surfaced two real prior transactions for that same customer already above that ceiling — a genuine behavioral pattern the original labeling pass couldn't have caught by eye. Relabeled rather than forcing the agent to match a label that was itself wrong. Same category of correction as the T0086/T0023 flip back in Action 16 — re-derived under better evidence, not adjusted for convenience.

**5. One case was correctly left alone as inconclusive, rather than stretched into a finding.** T0071's manual re-run produced the correct answer, meaning the original failure was simply a different, non-matching sample of the same non-determinism already confirmed elsewhere (T0014, T0078 in CI). No fix was invented to explain it, because there wasn't a real pattern there to explain.

**6. The fix was scoped to exactly what was confirmed, not expanded speculatively.** Two sentences added to `agent.py`'s grounding instruction, each mapping to exactly one confirmed failure. Nothing broader added "while we're in there" — consistent with this project's running discipline against fixing more than what was actually observed.

**7. The fix was verified by re-running the two specific cases it targeted, and the verification looked at reasoning, not just the verdict.** Both T0078 and T0133 flipped to correct — but more importantly, the evidence text itself changed in the exact way predicted (T0078 now explicitly compares prior-amount size; T0133 now lets the named signal drive the recommendation). Verdict-only confirmation would have been weaker evidence than this.

**8. A late-night cost/benefit decision was made deliberately, with the tradeoff stated plainly rather than defaulted into.** A full 18-case re-run was considered and explicitly deferred — not skipped silently — in favor of the cheaper, already-proven 6-case CI subset, reasoning that judgment-quality interpretation of a potentially-surprising full result deserved fresh eyes rather than 3am eyes. The option to run the full set later wasn't lost, just correctly sequenced.

**9. A plausible connected finding was named but deliberately not overclaimed.** T0078's past CI flips, originally attributed purely to non-determinism, might actually have been this exact bug firing stochastically — but that's written into `CLAUDE.md` as an explicit watch-item pending real post-fix CI evidence, not asserted as fact. Same discipline that caught the original hypothesis being wrong is now applied to avoid introducing a new unconfirmed one.

**Files touched this action:**

- `src/agent.py` — grounding instruction updated with two targeted additions addressing the T0078 and T0133 failure patterns.
- `eval/eval_set.json` — T0143 relabeled `escalate` → `clear`, with full reasoning recorded; set is now 6 escalate / 12 clear.
- `CLAUDE.md` — "Known gaps" eval-accuracy entry fully rewritten with the real investigation findings, the fix, and the T0078/CI watch-item.
- `SCOPE.md` — untouched; nothing here changed scope.

**9. The CI run confirmed, with one new finding properly handled rather than either ignored or over-interpreted.** Final result: 5/6, 83.3%, passed. T0078 passed for a third consecutive time since the fix (two manual re-runs plus this CI run) — real, if not yet conclusive, evidence the earlier CI flakiness may have been this exact bug, not pure variance; logged as strengthened but still not stated as proven fact. T0018 failed for the first time ever in this project's recorded history — previously clean across Action 13, every reached Action 17 run, and all three Action 20 CI runs. Logged as a genuine open question (ordinary variance finally landing wrong, versus an unintended side effect of the prompt change) rather than forced into a premature conclusion either way — consistent with the same discipline that caught the original wrong hypothesis in point 2.

## Action 25 — Write the project narrative

Actions 24, 26, and 27 (reread Know-tier notes, prep Know-tier answers, rehearse out loud) were skipped at the user's direction — pure recall/rehearsal, no new project content to log. This entry is the Action 25 deliverable itself: the actual narrative, built from the Pitch template's five beats, using only what's documented and verified elsewhere in this log — no unverified claims, no stale numbers presented as current.

**Problem & domain.** Fraud and risk teams at banks and fintechs flag transactions with rule-based triggers — unusual amount, new merchant category, geographic anomaly, velocity spikes. Every flag then lands on an analyst's desk, who manually pulls the customer's transaction history, checks the merchant's reputation, and writes a case note recommending escalation or clearance. That's slow, inconsistent in format, and doesn't scale with flag volume — a real, well-documented bottleneck in fraud operations, not a hypothetical one.

**Why AI.** The flagging itself is already rule-based — deliberately dumb, on purpose. What a rule engine can't do is weigh multiple pieces of context against each other the way a human analyst does: is a $1,855 charge actually unusual for this customer, given their history at this merchant? Does a new merchant category on a 28-day-old account mean something different than the same category shift on a 2,000-day account? That's synthesis and judgment, not threshold-checking — which is exactly where an LLM earns its place over a simpler system, and exactly what had to be verified it was actually doing, not just assumed.

**Solution design.** Five stages: flag, retrieve, tool-call, generate, guardrail. The agent retrieves the relevant fraud-pattern doc from a Chroma knowledge base, pulls customer history and merchant info through two tool calls, and drafts a structured case note — risk factors, evidence, a recommendation, and a confidence score — that a human always makes the final call on. Synchronous, one transaction in, one case note out. Containerized with Docker, deployed on Render, with a 6-case CI gate running the eval set on every push and structured JSON logging for every request — latency, token cost, whether the guardrail fired. Success criterion: 80% recommendation-direction accuracy on an 18-case hand-labeled eval set, which also scopes CI.

**Your role & workflow.** Every real decision in this project was made deliberately and checked, not just accepted — discovering Claude Pro doesn't include API access partway through and switching providers to Gemini, picking Chroma's default embedding model after confirming it handled this project's coarse retrieval task, designing the eval set's ground truth to be allowed to disagree with the flagger, since the flagger's job was never to be right, just to flag candidates for review. The clearest concrete debugging example: the eval set surfaced two real reasoning failures — the agent was treating merchant familiarity as mitigating evidence regardless of whether the prior purchase was actually comparable in size, and separately, it would correctly name an account-takeover signal in its own evidence and then not act on it. The actual case-note text was pulled, not just the pass/fail label, both patterns were diagnosed precisely, and each was fixed with one targeted sentence in the prompt — then verified by checking that the reasoning itself changed, not just the verdict.

**Outcome & next steps.** What worked: a real, working agent — tool calls, retrieval, generation, and a code-level guardrail all genuinely exercised against live data, not just written and assumed correct. The agent shows real judgment, not pattern-matching — confidence scores that track evidence strength, and at least one case where it found a mitigating factor in a customer's own history on its own. What's left to improve: get a fresh full 18-case accuracy number now that two confirmed bugs are fixed (the 61.1% figure predates the fix); investigate a new, first-ever CI failure on a previously-stable case that surfaced right after the fix landed, to rule out an unintended side effect; and address the \~60–110 second per-request latency, which is fine for a demo but would matter in a real deployment, since it's inherent to the multi-call architecture rather than something that improves with better hosting.
