# AI Fraud-Review Copilot Project — Each Phase Explained

## Phase 0 — Foundations / mindset

### Concept 1 — Context files (CLAUDE.md) and the externalize-it mindset

You created two files to keep your project on track:
- **SCOPE.md** reminds you what the project should and shouldn't include. It helps prevent the project from slowly growing beyond your plan.
- **CLAUDE.md** gives Claude Code your project rules and setup. Claude Code reads it automatically when you start a session in that folder.

Both files put important instructions in writing, so you don't have to remember or repeat them.

They're separate from the README because the README is mainly for people exploring the project, while CLAUDE.md is meant to guide the AI tool.

**In short:** SCOPE.md guides you; CLAUDE.md guides Claude Code.

---

## Phase 1 — Data & Flag — Creating and checking the data

### 1. `generate_data.py` creates test data

This script creates three CSV files: customers, merchants, and transactions. It uses:

- **Python's `random` module** to choose customer profiles, merchants, categories, locations, and dates.
- **NumPy** to generate transaction amounts.
- **Faker** to create realistic names, company names, and city names.
- Python's built-in **CSV, date/time, and file-path tools** to write the files and handle dates and paths.

The script fixes the random seeds, so running it again creates the same data. The data includes ordinary purchases, borderline amounts, and unusually large amounts, giving the flagger a more useful test. Customers are also assigned preferred shopping categories, so most of their purchases feel normal and a new category can be a meaningful warning.

You chose synthetic data instead of a real Kaggle fraud dataset because its fields were anonymized, you couldn't control how many borderline cases it contained, and synthetic data fit your privacy goals better.

### 2. `flagger.py` checks transactions for warning signs

The flagger uses **Python's built-in tools only** — no external packages:

- **CSV tools** to read and update the data files.
- **Date and time tools** to check whether transactions happened within 24 hours.
- **File-path tools** to locate the files.
- **`defaultdict`** to keep each customer's history and count the results.

It checks four things: multiple transactions within 24 hours, a purchase outside the customer's home location, an amount above their usual maximum, and a merchant category the customer hasn't used before. If several rules match, it chooses one reason according to a priority order.

Transactions are checked in time order, using only that customer's past transactions. You also tested the common "three transactions in 24 hours" rule, found it never triggered in your data, and set the minimum to two so the rule could actually be evaluated.

**In short:** `generate_data.py` makes repeatable, realistic test data; `flagger.py` checks it for suspicious patterns using simple rules.

---

## Phase 2 — Finding useful reference information (RAG)

file: `src/retrieval.py`

**RAG** means the system first finds relevant information, then gives it to the AI as background for its answer. The AI is less likely to rely on a guess—but only if the search finds the right information.

Your project uses **ChromaDB**, a tool that stores documents as number-based representations called *embeddings*. Similar meanings end up close together, so ChromaDB can find documents related to a question.

- `get_collection()` opens a **persistent** collection, so the stored information remains on disk between runs.
- `embed_knowledge_base()` reads the four Markdown files and stores them in the collection.
- `query_knowledge_base()` searches for the documents closest in meaning to your query.
- ChromaDB uses the `all-MiniLM-L6-v2` embedding model locally through ONNX, without an API key or a network call during searching. The model does need to download the first time it's set up.
- ChromaDB ranks results using **L2 (Euclidean) distance** here: a smaller distance means a closer match.
- Each document is stored whole, as one piece. You deliberately left chunking for later, until you had evidence that document size was causing a problem.

### The retrieval problem you found

Searching for the short label `amount_spike` returned the wrong document first. But a natural-language description of the same pattern found the correct document clearly.

That showed the problem was **how the query was written**, not a bad embedding model or document size: the right document was already stored and ranked second. You kept the documents intact and made natural-language queries a project rule. Those queries are now in `src/agent.py`'s `FLAG_REASON_QUERIES`.

**In short:** ChromaDB stores and searches your project's reference documents. Your testing showed that describing a fraud pattern in everyday language works better than searching with a short code label, so the system uses natural-language queries.

**Answers to the two checks:** The failing search still found the correct document, but ranked it second; the same idea in natural language ranked it first. That points to query wording as the issue. A near-tie between two documents is expected because their content can be similar, and their distances can be almost the same.

---

## Phase 3 — Backend lookup tools

**File: `src/tools.py`**

This file has two simple Python functions that look up information in CSV files:

- `lookup_customer_history(customer_id)` returns a customer's profile and up to 10 recent transactions.
- `lookup_merchant_info(merchant_id)` returns information about a merchant.

They act like small, predictable backend systems an analyst could check. They don't use AI to make decisions.

If a customer or merchant ID is missing, the function returns an error message as data instead of crashing. That lets the agent continue the case and explain what information it couldn't find. Later, `api.py` can turn the same missing-ID situation into an HTTP 404 response. Each layer handles the error in the way its caller expects.

The customer lookup returns recent transactions so the agent can consider the customer's actual spending history—not just repeat the flagger's warning. It returns at most 10, sorted newest first. Your sample data doesn't have any customer with more than 10 transactions, so the truncation part wasn't exercised.

### How tool calling works

The model doesn't run the Python function itself. It asks your code to call a function with specific details; your code runs it and sends the result back to the model. The code that manages those steps is called **orchestration**.

You used native function calling instead of **MCP**. MCP is a standard way to make tools available to different AI clients; native function calling was enough for this project's goal of showing an agent retrieve information and reason about it.

**Quick check answer:** If `lookup_merchant_info("M999")` can't find the merchant, `tools.py` returns an error as data so the agent can continue. If that missing merchant becomes an API-level error, `api.py` can respond with HTTP 404.

---

## Phase 4 — The agent's work loop

**Files: `src/agent.py` and `src/schemas.py`**

`src/agent.py` coordinates the AI and your Python tools. The AI requests a tool, your code runs it and sends back the result, and the AI can then request another tool or finish. This is the **think → act → observe** loop.

### Tool-calling loop

In `run_tool_calling_phase()`, you turned off the Gemini SDK's automatic tool calling and wrote the loop yourself. `TOOL_DISPATCH` maps each tool name requested by the model to the Python function that runs it.

You chose to make the loop visible so you could explain how tool calling works. Although the SDK logs a message that can make it look like automatic calling is enabled, your `tools_called` tracking confirms your own loop is running.

### Two phases for the answer

The agent makes two Gemini calls:

1. **Tool phase:** the model can request tools and gather information.
2. **Answer phase:** the model receives the gathered conversation and produces a structured case note, with no tools available.

You split the calls because Gemini's support for tool calls and structured JSON output together wasn't consistent across model versions. In Phase 2, `src/schemas.py`'s `CaseNote` schema guides the output. It ensures fields such as the recommendation use a known value, which also makes results easier to score later.

Phase 2 needs the full Phase 1 conversation because that includes the tool results. In other words, the conversation is the agent's **context**: if the results weren't included, the model would have to answer without the information it just retrieved.

### Model and retry handling

`src/agent.py` uses the Gemini model named in `MODEL_NAME`. You switched models after a real `429 RESOURCE_EXHAUSTED` quota error showed the original model's actual daily limit was lower than the dashboard indicated.

The `generate_with_retry()` function adds waits of 20, 40, then 80 seconds before retrying. That gives temporary Gemini service errors more time to clear than the SDK's own quick retries.

**In short:** `src/agent.py` runs the tool loop, keeps the results in the conversation, and asks Gemini for a structured final note. The schema in `src/schemas.py` shapes that note.

---

## Phase 5 — Safety checks on the case note

**File: `src/guardrail.py`**

A guardrail is a check in code that enforces rules around the AI's answer. A prompt can ask the AI not to make a definite fraud claim, but the AI might still do it. A code check can catch that before the note is used.

This file has two checks with different responses:

- **`check_fraud_language()`** looks for claims that state fraud as a fact. If it finds one, it raises a `GuardrailViolation` so a person can review the note. It doesn't try to rewrite the claim.
- **`redact_pii()`** removes the customer's name from the note. This is safe to fix automatically because replacing a name doesn't change the point being made.

The project doesn't contain real card numbers, so the guardrail focuses on customer names instead. It keeps locations and synthetic IDs because they help explain location-based warnings and trace the case.

### The bug you caught

At first, the fraud check also flagged cautious phrases such as "fraud risk" and "potential fraud." You tested a phrase the code was supposed to allow and saw that it failed. You then updated the regular expression to allow those hedged phrases while still catching definite fraud claims.

You checked the fix with direct tests of the guardrail function: a phrase that should pass, a definite claim that should fail, and a phrase that matched overlapping patterns. Testing the function directly makes it easier to tell whether the guardrail works without relying on what the AI happens to say in a particular run.

### Why the checks run in this order

`draft_case_note()` checks for definite fraud language **before** redacting the customer's name. That way the fraud check reviews the AI's original wording. After that wording passes, the system removes the name before returning the note. If redaction happened first, the fraud check would inspect text that had already been changed.

The fraud check uses regular expressions, which look for specified text patterns. This method can miss a novel way of claiming fraud as fact. The project also doesn't check for prompt injection in retrieved content; the four reference documents are written by you, rather than coming from an untrusted source.

**In short:** `src/guardrail.py` blocks definite fraud claims for human review and removes customer names from accepted notes. You tested the checks directly and fixed a real bug where cautious language was being blocked.

---

## Phase 6 — The API

**File: `src/api.py`**

This file uses **FastAPI** to provide one endpoint: `POST /review/{transaction_id}`. You kept the API small to match the "bare API" boundary in `SCOPE.md`, rather than adding routes just because they might be useful later.

The endpoint uses a regular `def`, not `async def`. That fits because the work underneath it—Gemini requests, ChromaDB searches, and CSV reads—runs synchronously. FastAPI runs a regular route function in a thread pool. Putting blocking work inside `async def` could tie up the event loop when several requests arrive at once.

The API also translates errors for the layer that needs them:

- The agent can receive an error result from a lookup and continue reasoning about missing information.
- The API turns a missing transaction into an **HTTP 404**, so the caller receives the proper "not found" status.

You tested both the successful API path and the 404 path. If the agent's retry logic runs out, the exception currently passes through the API and becomes an **HTTP 500** response.

### Quick check: `GuardrailViolation`

A `GuardrailViolation` that escapes `draft_case_note()` also currently reaches the caller as an **HTTP 500**, because `api.py` doesn't translate it into a more specific response. That is a **known gap**: the code could handle this kind of expected guardrail rejection separately from an unexpected server failure.

---

## Phase 7 — Checking how well the agent performs

**Files: `eval/eval_set.json` and `eval/run_eval.py`**

An **evaluation set** is a list of examples with expected answers. An **eval harness** is the script that runs those examples through the agent and measures the results. Yours has **18 hand-labeled transactions**.

### What the expected answers mean

The expected answer is based on what a reasonable analyst would decide after seeing the full context—not automatically on what the rule-based flagger decided. That matters because the flagger is simple, and its result is already shown to the agent.

The set expects **6 "escalate"** decisions and **12 "clear"** decisions. So an agent that escalates every case won't do well.

### How the script scores answers

`run_eval.py` checks whether the agent's recommendation exactly matches the expected recommendation. A separate keyword check looks at whether the explanation mentions relevant evidence, but that check is informational; it doesn't change the score.

You chose not to score whether the agent repeated the flag reason. Since the agent is given that reason in its prompt, checking whether it repeats it wouldn't show whether it made a good judgment.

If a case fails because of an API or quota problem, the script records that failure separately instead of treating it as a wrong decision. The report makes clear how many cases were actually scored, so a percentage based on only a few cases doesn't look like a complete result.

### Handling rate limits and the result

Running all 18 cases quickly hit a **15 requests-per-minute** limit. `run_eval.py` now waits **30 seconds between cases**. The wait is in the evaluation script because the limit affects batch testing, not the agent's normal single-case workflow.

The final score was **61.1% (11 out of 18)**, below the project's 80% target. You reported the result as it was and noted patterns in the mistakes for further investigation.

### Tools used

- **`eval_set.json`** stores the examples and expected answers in JSON format.
- **`run_eval.py`** is a Python script that runs the cases, compares results, reports failures, and calculates accuracy.
- The script also uses a **30-second delay** to stay under the API request limit.

**Quick check answer:** These components have different jobs. The evaluation script catches errors per case so it can report results for the rest of the batch, while the agent and API let real request failures surface to the caller.

---

## Phase 8 — Packaging and shipping the app

**Files: `Dockerfile`, `.github/workflows/ci.yml`, and `.env.example`**

### Docker packages the app

**Docker** builds a container image: a package containing the app and what it needs to run. The project uses the `python:3.12-slim` base image. It installs dependencies before copying the code, so Docker can reuse the slow dependency-install step when only the code changes.

The Dockerfile also builds the **ChromaDB** collection while creating the image. Without that step, the app could start with an empty collection and quietly answer without its reference material. It runs the app with **Uvicorn**, a server for Python web apps, bound to `0.0.0.0` so it can receive requests from outside the container. You checked that it worked with a real **`curl`** request.

The base image choice matters because ChromaDB uses **ONNX Runtime** for local text embeddings. The notes say ONNX Runtime's prebuilt packages suit the image's Linux setup better than Alpine's, avoiding a potentially slow and fragile build. The production image also includes `faker` and `pytest`, which are mainly development tools; keeping one requirements setup was considered simpler for this project.

### Render hosts the app

**Render** runs the deployed container and makes the API available online. The notes say it was chosen after checking the available hosting options at the time.

Requests took around 63–108 seconds. You tested whether the host's computing power was the cause by timing a request locally too. It took a similar amount of time, which pointed to the several sequential calls to **Gemini** as the main source of the delay—not the hosting location.

### GitHub Actions checks code changes

**GitHub Actions** runs the CI workflow in `.github/workflows/ci.yml`. Running the full evaluation set on every push would use too much Gemini quota and take too long, so the workflow runs six specific cases instead.

The cases are named explicitly with `--only`. That keeps the same test group from run to run and includes a case known to sometimes change its result. The six-case check passed at **83.3%** even when that case failed, showing the CI gate can tolerate a miss and still meet the 80% target. Taking the first six rows could change which cases are included if the eval file's order changes.

### `.env.example` documents configuration

**`.env.example`** lists the settings an engineer needs to provide. It was created to close a gap in the project setup. `PORT` isn't listed because Render provides it to its own routing system, and this code doesn't read it.

**Quick check:** `--only` keeps the CI test group fixed and includes the known flip case. If CI just took the first six rows, it might test a different group and wouldn't prove that the gate can pass when that known case fails.

---

## Phase 9 — Logging and tracking request costs

**Files: `src/api.py` and `src/agent.py`**

Logging happens in `src/api.py` because it records production API requests. The guardrail stays in `src/agent.py` so it protects every way the agent can be used, including the API, direct runs, and evaluations.

The agent may make **2–4 Gemini calls** to gather information and write a case note. `src/agent.py` adds up the token counts from all those calls, so the log reflects the whole request's cost.

### The bug you found and fixed

When the fraud-language guardrail raised an error, the agent stopped before returning its result. That meant the token count disappeared—even though the Gemini calls had already happened.

You fixed this by attaching the token count to the guardrail error before re-raising it. Then `src/api.py` can log the count when it catches that error. The API still sends the error onward; it doesn't turn it into a successful response.

The API response leaves out the token count because the analyst needs the case note, while the operations log is where request cost and system behavior belong.

### Tools and packages

- **Python's built-in `logging` package** writes request details to the application log.
- **Python's built-in `json` package** formats each log entry as structured data.
- **Python's built-in `time` package** measures request duration.
- **Gemini's usage metadata** supplies the token counts for the model calls. The notes don't specify the Gemini SDK package name.

The code records three different situations: a successful review, a transaction that wasn't found, and a guardrail violation. Each has its own log details.

**Quick check:** Logging makes the guardrail violation visible to operations, but it doesn't make the generated claim safe to show as a normal answer. That matches Phase 5: a definite fraud claim should stop for human review, not be quietly rewritten or passed off as a successful case note.

---

## Phase 10 — Finding and fixing the reasons behind low accuracy

**Files: `eval/eval_set.json`, `src/agent.py`, and `CLAUDE.md`**

The first full evaluation scored **61.1% (11/18)**, below the project's 80% target. You looked at the results by flag type and then investigated the cases that failed.

### Tools used

- **`eval/run_eval.py`** runs the cases and reports pass/fail counts. It didn't show the agent's explanation text, so it wasn't enough for diagnosing the failures.
- **`python -m src.agent <transaction_id>`** runs an individual case and shows the case note, including the agent's reasoning.
- **`eval/eval_set.json`** holds the expected answers and explanations for the test cases.
- The fixes were made to the **grounding instruction** in `src/agent.py`, which guides Gemini when it writes its final recommendation.

### What the investigation found

A theory in `CLAUDE.md` said amount-spike mistakes happened because the agent trusted low-risk merchant labels too much. You checked the actual case notes, found no evidence for that explanation, and discarded it.

Five cases revealed different things:

- **T0078 — a confirmed reasoning problem:** the agent treated shopping at a familiar merchant as reassuring, without comparing the previous purchase amount to the much larger flagged amount.
- **T0133 — another reasoning problem:** the agent recognized a new account as a risk and found the matching pattern in the reference material, but still recommended "clear."
- **T0071 — inconclusive:** it passed when you reran it, so you didn't invent a fix for a failure that might have been ordinary variation.
- **T0143 — an incorrect expected answer:** the customer had previous purchases above their usual spending ceiling. You corrected the label from "escalate" to "clear" based on that evidence.

### The targeted fix and what remains unknown

You added two instructions to `src/agent.py`: compare the size of previous purchases before treating a familiar merchant as reassuring, and let a risk factor that matches a reference pattern meaningfully affect the recommendation. When you reran T0078 and T0133, both the answers and the reasoning changed in the expected ways.

That is encouraging, but you can't yet say the accuracy problem is fully fixed. T0078 has passed three times since the change, but that's not conclusive. T0018, which had always passed before, failed once; it's not clear whether that was ordinary variation or an unintended effect of the prompt change. A new run of all 18 cases is still needed for an updated accuracy score.

**Interview answer:** "I fixed two specific reasoning failures and verified that the agent's explanations changed in the expected way. But I haven't rerun the full evaluation set, and one previously reliable case has failed once, so I can't yet claim the overall accuracy problem is fixed."

---

## Packages and tools used across the project

| Phase | Package or tool | Simple definition | Where it's used |
|---|---|---|---|
| 0 | `SCOPE.md` | A note that sets the project's boundaries. | Helps prevent the project from growing beyond its intended purpose. |
| 0 | `CLAUDE.md` | Project instructions that Claude Code reads at the start of a session in the repo. | Records conventions and context for the AI coding tool. |
| 1 | Python `random` | Python's built-in random-choice tools. | Chooses customer profiles, merchants, categories, and other synthetic data. |
| 1 | NumPy | A Python package for numerical operations. | Generates transaction amounts. |
| 1 | Faker | A Python package for creating realistic sample details. | Makes customer names, company names, and city names. |
| 1, 3 | Python `csv` | Python's built-in CSV reader and writer. | Saves generated data and reads customer, merchant, and transaction files. |
| 1, 3 | Python `datetime` and `timedelta` | Python's built-in date and time tools. | Creates transaction timestamps and supports time-window checks. |
| 1, 3 | Python `pathlib` | Python's built-in file-path tool. | Locates the data files and output folders. |
| 1 | Python `defaultdict` | A dictionary that supplies a default value for a missing key. | Keeps transaction history and flag counts in `src/flagger.py`. |
| 2, 8 | ChromaDB | A vector database that stores and searches text by meaning. | Stores the knowledge-base documents for retrieval; the collection is built when Docker creates the image. |
| 2, 8 | `all-MiniLM-L6-v2` with ONNX Runtime | A local text-embedding model and runtime; embeddings represent text as numbers for similarity search. | ChromaDB uses it to find relevant reference documents. ONNX Runtime runs the embedding model locally. |
| 2 | Markdown files in `knowledge_base/` | Plain text files with headings and formatting. | Provide fraud-pattern references that retrieval can find and give to the agent. |
| 3 | Native Gemini function calling | A way for the model to request a named function with structured inputs. | The model requests customer or merchant lookups; your Python code runs the function and returns the result. No MCP server is used. |
| 4, 10 | Gemini API/SDK | A hosted AI service accessed by the app. | Requests tool calls and generates structured case notes; the agent also retries temporary failures. The exact SDK package name isn't shown in the pasted code. |
| 4, 5, 6 | Pydantic | A Python package for defining and checking data shapes. | Defines `CaseNote` and API response models, including allowed recommendation values and confidence range. |
| 4 | Python `enum` | A built-in way to define a fixed set of named choices. | Limits recommendations to `escalate` or `clear`. |
| 5 | Python `re` | Python's built-in regular-expression tool for matching text patterns. | Detects definitive fraud claims and redacts customer names. |
| 5, 9 | `pytest` | A Python testing package. | Used for targeted tests of guardrail behavior. It is listed as a development dependency. |
| 6, 9 | FastAPI | A Python package for building HTTP APIs. | Provides the `POST /review/{transaction_id}` endpoint and handles HTTP errors such as 404. |
| 6, 8 | Uvicorn | A server that runs Python web apps. | Starts the FastAPI app locally or inside the Docker container. |
| 6, 9 | Python `json` | Python's built-in JSON reader/writer. | Formats structured log entries; also used by the tools script for its manual output. |
| 9 | Python `logging` | Python's built-in logging system. | Records successful reviews, missing transactions, and guardrail violations for operations. |
| 9 | Python `time` | Python's built-in time utilities. | Measures how long an API request takes. |
| 7, 10 | `eval/eval_set.json` | A JSON file containing test cases and expected answers. | Supplies the 18 labeled cases used to measure agent performance. |
| 7, 10 | Python `argparse` | Python's built-in command-line argument parser. | Adds evaluation options such as `--limit`, `--only`, and `--delay`. |
| 7–8, 10 | Python `sys` | Python's built-in access to system-level functions. | Lets the evaluation script exit with a pass or fail status. |
| 7–8 | `eval/run_eval.py` | A custom Python evaluation script. | Runs cases, records errors, calculates accuracy, and enforces the CI threshold. |
| 8 | Docker | A tool for packaging an app and its dependencies into a container image. | Builds the production image, installs dependencies, and prepares ChromaDB data. |
| 8 | `pip` and `requirements.txt` | `pip` installs Python packages; the requirements file lists them. | Installs the project's dependencies locally, in Docker, and in CI. |
| 8 | Render | A hosting platform. | Runs the deployed Docker image and exposes the API. |
| 8 | GitHub Actions | GitHub's automation service. | Runs the CI workflow on pushes: installs dependencies, builds ChromaDB, then evaluates six named cases. |
| 8 | GitHub Secrets | GitHub's secure storage for sensitive values. | Supplies `GEMINI_API_KEY` to the CI run without putting the key in the workflow file. |
| 8 | `curl` | A command-line tool for making web requests. | Sends a real request to check that the running container is reachable and responds. |
| 8 | `EXPOSE 8000` / `0.0.0.0` | Docker port metadata and a network bind address. | Documents the app's port and lets requests reach Uvicorn from outside the container. |

### Mentioned, but not used to build this project

SQL, fine-tuning, LoRA/QLoRA, quantization, vLLM, and Triton are topics to recognize for interviews. This project uses CSV files and ChromaDB rather than a relational database, and calls a hosted Gemini API rather than serving or fine-tuning model weights.

### Summary

Python and its built-in tools handle the data and app logic; Gemini writes the analysis; ChromaDB searches the reference files; FastAPI and Uvicorn serve the app; Docker and Render package and host it; GitHub Actions runs the automated check.

---

## Explain the project

This phase brings the project together into a short pitch and an architecture walkthrough.

### A simple project pitch

"I built a fraud-review assistant that helps an analyst investigate transactions. A basic rules system flags possible concerns, then the agent retrieves reference information and customer or merchant details before writing a case note. I used Gemini for reasoning, ChromaDB for document search, Python tools for the lookups, and a code-based guardrail to catch definite fraud claims and redact customer names. I packaged the app with Docker, deployed it on Render, and use GitHub Actions to run a small evaluation on each push. The first full evaluation scored 61.1%, and I've fixed two specific reasoning issues, but I still need to rerun all 18 cases to measure the updated accuracy."

### The architecture in file order

`SCOPE.md` and `CLAUDE.md` set the project boundaries → `data/generate_data.py` makes repeatable synthetic data → `src/flagger.py` adds rule-based flags → `knowledge_base/` and `src/retrieval.py` provide reference information through ChromaDB → `src/tools.py` looks up customer and merchant details → `src/agent.py` coordinates Gemini and the tools, using `src/schemas.py` to shape the case note → `src/guardrail.py` checks and redacts the note → `src/api.py` serves it through FastAPI → `eval/` measures how well the agent performs → `Dockerfile` and `.github/workflows/ci.yml` package the app and check changes.

**Tools in the story:** Python, Gemini, ChromaDB, FastAPI, Docker, Render, and GitHub Actions. In simple terms: Python runs the logic; Gemini writes the analysis; ChromaDB searches the reference documents; FastAPI exposes the app; Docker packages it; Render hosts it; and GitHub Actions checks changes.