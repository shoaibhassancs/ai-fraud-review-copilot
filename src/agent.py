"""
Agent orchestration for AI Fraud-Review Copilot.

Straight-line sequence, per the spec: retrieve -> call both tools -> generate.
No branching, no retry logic — every flagged transaction needs both tools,
so the loop assumes both calls happen.

Two-phase design, deliberately not one combined call:
  Phase 1 (tool-calling): model requests lookup_customer_history and
    lookup_merchant_info, we execute them from tools.py, results go back
    into the conversation. No response_schema set in this phase.
  Phase 2 (generation): a fresh call with response_schema=CaseNote set,
    no tools declared. The model produces the final structured case note
    from everything gathered in Phase 1.
  Split because combining `tools` with structured JSON output is reported
  inconsistent across Gemini model versions — this sidesteps that
  uncertainty rather than betting on it working for whichever model string
  ends up in use.

Manual function-calling loop, not the SDK's automatic mode — each step
(model requests a call, we execute it, we send the result back) is
explicit and visible, because being able to describe the mechanism is
the point of this project, not just getting an answer out of it.

Run directly for a quick manual check against one transaction. This file
imports from other src/ modules (schemas, retrieval, tools), so it must be
run as a module from the project root, not as a direct script path:
    python -m src.agent <transaction_id>
"""

import os
import sys
import csv
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError

from src.schemas import CaseNote
from src.retrieval import query_knowledge_base
from src.tools import lookup_customer_history, lookup_merchant_info
from src.guardrail import check_fraud_language, redact_pii

load_dotenv()

MODEL_NAME = "gemini-3.5-flash-lite"  # Switched from gemini-3.8-flash after Action 13: that model's
# free tier has a 20 requests/day cap, which real testing hit (429 RESOURCE_EXHAUSTED). flash-lite
# ran successfully for all 4 of Action 13's real transactions and draws from a separate quota pool,
# so it isn't affected by 3.8-flash's exhaustion.

DATA_DIR = Path(__file__).parent.parent / "data"
TRANSACTIONS_PATH = DATA_DIR / "transactions.csv"

_client = None


def get_client():
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            # Explicit timeout (ms) so a slow/stuck call fails with a clear
            # error instead of hanging indefinitely. Gemini 3.8 Flash's
            # "thinking" mode plus function declarations can genuinely take
            # a while — 120s gives it room without waiting forever.
            http_options=types.HttpOptions(timeout=120_000),
        )
    return _client


# ---- Tool declarations: told to Gemini in Phase 1 only ----

LOOKUP_CUSTOMER_HISTORY_DECL = types.FunctionDeclaration(
    name="lookup_customer_history",
    description="Look up a customer's profile and recent transaction history by customer ID.",
    parameters={
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "The customer's ID, e.g. 'C001'."},
        },
        "required": ["customer_id"],
    },
)

LOOKUP_MERCHANT_INFO_DECL = types.FunctionDeclaration(
    name="lookup_merchant_info",
    description="Look up a merchant's name, category, and risk tier by merchant ID.",
    parameters={
        "type": "object",
        "properties": {
            "merchant_id": {"type": "string", "description": "The merchant's ID, e.g. 'M001'."},
        },
        "required": ["merchant_id"],
    },
)

TOOLS = types.Tool(function_declarations=[LOOKUP_CUSTOMER_HISTORY_DECL, LOOKUP_MERCHANT_INFO_DECL])

# Maps the function name Gemini requests to the real Python function that runs it.
TOOL_DISPATCH = {
    "lookup_customer_history": lookup_customer_history,
    "lookup_merchant_info": lookup_merchant_info,
}

# Natural-language phrasing per flag reason — per Action 9's finding, the raw
# flag_reason string (e.g. "amount_spike") retrieves the WRONG knowledge base
# doc for at least one flag type. Never pass flag_reason directly as the query.
FLAG_REASON_QUERIES = {
    "velocity_spike": "Multiple transactions happened within a short time window",
    "geo_anomaly": "The transaction occurred somewhere far from the customer's home location",
    "amount_spike": "The transaction amount is much higher than this customer normally spends",
    "new_merchant_category": "The customer made a purchase in a merchant category they've never used before",
}


def generate_with_retry(client, model, contents, config, max_attempts=4, initial_delay=20):
    """
    Call generate_content with our own retry/backoff on top of the SDK's
    internal one — the SDK's own retry (via tenacity) exhausts in seconds,
    which isn't long enough to ride out a sustained "high demand" 503 on a
    newly-launched model. Waits 20s, 40s, 80s between attempts (roughly
    2.5 minutes total) before giving up and raising the real error.
    """
    delay = initial_delay
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except ServerError as e:
            if attempt == max_attempts:
                raise
            print(f"  [attempt {attempt}/{max_attempts}] {e} — retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2


def get_transaction(transaction_id):
    with open(TRANSACTIONS_PATH, newline="") as f:
        for row in csv.DictReader(f):
            if row["id"] == transaction_id:
                return row
    return None


def retrieve_fraud_pattern(flag_reason):
    """Phase 0: retrieve the relevant fraud-pattern doc via a natural-language query."""
    query = FLAG_REASON_QUERIES.get(flag_reason, flag_reason)
    results = query_knowledge_base(query, n_results=1)
    doc_text = results["documents"][0][0]
    source = results["metadatas"][0][0]["source"]
    return doc_text, source


def run_tool_calling_phase(client, transaction):
    """
    Phase 1: model requests lookup_customer_history and lookup_merchant_info,
    we execute them, results go back into the conversation. Returns the
    full message history so Phase 2 can build on it.
    """
    prompt = (
        "A transaction has been flagged for review. Use the available tools "
        "to look up the customer's history and the merchant's information "
        "before responding.\n\n"
        f"Transaction ID: {transaction['id']}\n"
        f"Customer ID: {transaction['customer_id']}\n"
        f"Merchant ID: {transaction['merchant_id']}\n"
        f"Amount: {transaction['amount']}\n"
        f"Timestamp: {transaction['timestamp']}\n"
        f"Location: {transaction['location']}\n"
        f"Flag reason: {transaction['flag_reason']}\n"
    )

    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

    config = types.GenerateContentConfig(
        tools=[TOOLS],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    tools_called = set()

    # Loop until the model stops requesting function calls. Straight-line
    # assumption: every flagged transaction needs both tools, so we don't
    # branch on which ones get called — Action 13's manual run is what
    # would surface it if that assumption turns out wrong.
    while True:
        response = generate_with_retry(client, MODEL_NAME, contents, config)
        candidate = response.candidates[0]
        contents.append(candidate.content)

        function_calls = response.function_calls
        if not function_calls:
            break

        response_parts = []
        for call in function_calls:
            fn = TOOL_DISPATCH[call.name]
            result = fn(**call.args)
            tools_called.add(call.name)
            response_parts.append(
                types.Part(function_response=types.FunctionResponse(name=call.name, response=result))
            )
        contents.append(types.Content(role="user", parts=response_parts))

    return contents, tools_called


def run_generation_phase(client, contents, fraud_pattern_doc, fraud_pattern_source):
    """
    Phase 2: a fresh call with response_schema=CaseNote set, no tools
    declared. The model produces the final structured case note from
    everything gathered in Phase 1 plus the retrieved fraud-pattern doc.
    """
    grounding_instruction = (
        "Here is the relevant fraud-pattern reference material, retrieved "
        f"from '{fraud_pattern_source}':\n\n{fraud_pattern_doc}\n\n"
        "Using the transaction details, the customer history, the merchant "
        "info, and this reference material, draft a structured case note. "
        "Cite specific evidence from what you looked up. Never state "
        "definitively that fraud occurred — only recommend escalate or "
        "clear, with your reasoning, for a human analyst to decide."
    )
    contents = contents + [types.Content(role="user", parts=[types.Part(text=grounding_instruction)])]

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=CaseNote,
    )

    response = generate_with_retry(client, MODEL_NAME, contents, config)
    return response.parsed


def draft_case_note(transaction_id):
    """Run the full agent loop for one transaction: retrieve -> call tools -> generate."""
    transaction = get_transaction(transaction_id)
    if transaction is None:
        return {"error": f"transaction not found: {transaction_id}"}

    client = get_client()

    fraud_pattern_doc, fraud_pattern_source = retrieve_fraud_pattern(transaction["flag_reason"])
    contents, tools_called = run_tool_calling_phase(client, transaction)
    case_note = run_generation_phase(client, contents, fraud_pattern_doc, fraud_pattern_source)

    # Guardrail (Generate -> Guardrail per the architecture's stage order).
    # Runs here, not in api.py, so a direct `python -m src.agent` run goes
    # through it too — a check that only lives in the HTTP layer isn't a
    # real guardrail.
    #
    # Order matters: check first, redact second. check_fraud_language
    # raises GuardrailViolation uncaught on a genuine finding — consistent
    # with api.py's "no defensive handling for genuine failures" stance,
    # this propagates as a real failure instead of being swallowed.
    # redact_pii runs only once that check has passed.
    check_fraud_language(case_note)

    # A fresh lookup (cheap local CSV read, not an API call) rather than
    # parsing the name back out of the Phase 1 conversation history.
    customer_info = lookup_customer_history(transaction["customer_id"])
    customer_name = customer_info.get("name")
    if customer_name:
        case_note = redact_pii(case_note, customer_name)

    return {
        "transaction_id": transaction_id,
        "fraud_pattern_source": fraud_pattern_source,
        "tools_called": sorted(tools_called),
        "case_note": case_note,
    }


if __name__ == "__main__":
    txn_id = sys.argv[1] if len(sys.argv) > 1 else "T0001"
    result = draft_case_note(txn_id)
    print(result)