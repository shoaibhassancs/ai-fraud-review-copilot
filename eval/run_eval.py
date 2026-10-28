"""
Eval script for AI Fraud-Review Copilot.

Runs the agent against the 18 hand-labeled cases in eval_set.json and
reports how it scored -- turning "I built an eval set" into "here's the
number."

Primary metric: recommendation-direction accuracy -- exact match between
case_note.recommendation.value and expected_recommendation. SCOPE.md's
bar is >=80% on this (at most 3 misses out of 18).

Secondary, informational-only check: does the risk_factors/evidence text
actually discuss evidence relevant to the case's flag_reason? Comparing
flag_reason itself to expected_flag_reason doesn't work -- flag_reason is
handed to the model directly in the prompt ("Flag reason: {flag_reason}"
in agent.py), not derived by it, so the model always echoes it back
regardless of whether it reasoned about it. Comparing it to itself would
almost always "pass" and test nothing. This keyword check is a shallow
signal instead -- not real comprehension-checking -- intentionally kept
that simple per the spec's "don't over-engineer the scoring logic"
guidance. It does NOT affect the accuracy number or the exit code.

Error handling deliberately differs from agent.py/api.py: those let a
genuine failure propagate uncaught, on purpose (one clear failure beats
one silently smoothed over). This script's job is different -- produce
one complete scorecard across 18 cases -- so a single case's failure
(an exhausted retry, a real GuardrailViolation, a transaction lookup
miss) is caught and recorded per-case, not allowed to take down the
other 17 results.

Accuracy is computed over cases that actually got SCORED (completed
without error or guardrail violation), not over all 18 -- an API quota
error isn't a judgment failure, so it shouldn't dilute a quality metric.
Error and violation counts are reported prominently alongside, never
hidden, so a low scored-count is visible even if the accuracy number
itself still looks fine.

Run a cheap sanity check on 2-3 cases before burning quota on the full
18 (each case is ~2-3 Gemini calls; the full run is roughly 40-55 calls
against gemini-3.5-flash-lite, a model only ever confirmed working 4
times so far):
    python -m eval.run_eval --limit 3
Then the full set:
    python -m eval.run_eval

Must run as a module, not a direct script path -- it imports from src/,
same reasoning documented in agent.py's own docstring:
    python -m eval.run_eval
"""

import argparse
import json
import sys
import time
from pathlib import Path

from src.agent import draft_case_note
from src.guardrail import GuardrailViolation

EVAL_SET_PATH = Path(__file__).parent / "eval_set.json"
ACCURACY_THRESHOLD = 0.80

# gemini-3.5-flash-lite's free tier caps at 15 requests/minute. Each case
# makes ~3 calls (2 in the tool-calling phase, 1 in generation).
#
# A real run with no delay hit 429 RESOURCE_EXHAUSTED starting at case 3.
# A real run with a 15s delay between cases got further (5 cases, i.e.
# ~15 calls, succeeded) but still hit 429 on the 6th case's first call --
# meaning 15s wasn't enough headroom in practice, even though the naive
# "3 calls/case, 15 cap/min" math suggested it should be. Worth being
# honest about this: that naive math doesn't cleanly explain the exact
# failure point observed, which suggests something about how the
# per-minute window is actually enforced isn't fully understood here.
# Rather than guess at a mechanism that can't be verified, the fix is
# empirical -- a much larger safety margin (30s) than the math implied
# was needed.
DEFAULT_CASE_DELAY_SECONDS = 30.0

# Shallow keyword check per flag_reason -- "did the model's free text talk
# about something in the right ballpark," not real comprehension-testing.
FLAG_REASON_KEYWORDS = {
    "velocity_spike": [
        "time", "window", "quick", "short period", "multiple transaction",
        "frequency", "minute", "hour", "velocity", "succession",
    ],
    "geo_anomaly": [
        "location", "home", "away", "distance", "travel", "address", "differ",
    ],
    "amount_spike": [
        "amount", "spend", "typical", "exceed", "higher", "spike",
        "maximum", "above", "outsiz",
    ],
    "new_merchant_category": [
        "category", "new", "first time", "never", "unfamiliar",
    ],
}


def check_risk_factor_relevance(case_note, flag_reason):
    """
    Shallow check: does the evidence + risk_factors text contain at least
    one keyword relevant to this flag_reason? See module docstring for
    why flag_reason itself can't be compared directly (it's circular).
    """
    keywords = FLAG_REASON_KEYWORDS.get(flag_reason, [])
    text = (case_note.evidence + " " + " ".join(case_note.risk_factors)).lower()
    return any(kw in text for kw in keywords)


def run_eval(cases, case_delay=DEFAULT_CASE_DELAY_SECONDS):
    """Run the agent against each case, catching failures per-case so one
    bad case doesn't take down the whole batch. Paces calls between cases
    to stay under the model's free-tier requests-per-minute cap -- see
    DEFAULT_CASE_DELAY_SECONDS above for why this exists."""
    results = []
    total = len(cases)
    for i, case in enumerate(cases):
        if i > 0 and case_delay > 0:
            print(f"  (waiting {case_delay:.0f}s before next case...)", flush=True)
            time.sleep(case_delay)

        txn_id = case["transaction_id"]
        expected_rec = case["expected_recommendation"]
        expected_reason = case["expected_flag_reason"]

        # Printed immediately, not buffered until the final report -- a
        # silent terminal for 7-12+ minutes (18 cases x ~30s pacing) looks
        # identical to a genuine hang otherwise. Learned this the hard way:
        # a real run with no progress output got mistaken for stuck.
        print(f"[{i + 1}/{total}] Running {txn_id}...", end=" ", flush=True)

        try:
            result = draft_case_note(txn_id)
        except GuardrailViolation as e:
            print("GUARDRAIL VIOLATION")
            results.append({
                "transaction_id": txn_id,
                "status": "guardrail_violation",
                "detail": str(e),
            })
            continue
        except Exception as e:
            print(f"ERROR ({type(e).__name__})")
            results.append({
                "transaction_id": txn_id,
                "status": "error",
                "detail": f"{type(e).__name__}: {e}",
            })
            continue

        if "error" in result:
            # draft_case_note's own not-found path returns a dict rather
            # than raising -- treat it the same as any other failure to
            # complete the case.
            print("ERROR (not found)")
            results.append({
                "transaction_id": txn_id,
                "status": "error",
                "detail": result["error"],
            })
            continue

        case_note = result["case_note"]
        actual_rec = case_note.recommendation.value
        match = actual_rec == expected_rec
        print("PASS" if match else "FAIL")
        results.append({
            "transaction_id": txn_id,
            "status": "scored",
            "expected_recommendation": expected_rec,
            "actual_recommendation": actual_rec,
            "recommendation_match": match,
            "risk_factor_relevant": check_risk_factor_relevance(case_note, expected_reason),
        })

    return results


def print_report(results):
    print()
    print("=" * 70)
    print("EVAL REPORT")
    print("=" * 70)

    for r in results:
        tid = r["transaction_id"]
        if r["status"] == "scored":
            mark = "PASS" if r["recommendation_match"] else "FAIL"
            rel = "yes" if r["risk_factor_relevant"] else "no"
            print(
                f"  [{mark}] {tid}: expected={r['expected_recommendation']:<9} "
                f"actual={r['actual_recommendation']:<9} risk_factor_relevant={rel}"
            )
        elif r["status"] == "guardrail_violation":
            print(f"  [GUARDRAIL] {tid}: {r['detail']}")
        else:
            print(f"  [ERROR] {tid}: {r['detail']}")

    scored = [r for r in results if r["status"] == "scored"]
    violations = [r for r in results if r["status"] == "guardrail_violation"]
    errors = [r for r in results if r["status"] == "error"]
    correct = sum(1 for r in scored if r["recommendation_match"])
    relevant_count = sum(1 for r in scored if r["risk_factor_relevant"])
    accuracy = correct / len(scored) if scored else 0.0

    print()
    print(f"Attempted: {len(results)}   Scored: {len(scored)}   "
          f"Guardrail violations: {len(violations)}   Errors: {len(errors)}")
    print()
    if scored:
        print(f"Recommendation accuracy (of scored cases): {correct}/{len(scored)} = {accuracy:.1%}")
        print(f"Risk-factor relevance, shallow keyword check (of scored cases): "
              f"{relevant_count}/{len(scored)}")
    else:
        print("Recommendation accuracy: n/a -- no cases completed scoring")

    if scored and len(scored) < len(results):
        missed = len(results) - len(scored)
        print()
        print(f"NOTE: {missed} of {len(results)} case(s) did not complete scoring "
              f"(guardrail violations + errors above). The accuracy figure only "
              f"reflects the {len(scored)} case(s) that did -- treat it with that "
              f"in mind, it is not a score across the full set.")

    print("=" * 70)

    return accuracy, len(scored)


def main():
    parser = argparse.ArgumentParser(description="Run the eval set against the agent.")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Only run the first N cases -- for a cheap sanity check before the full run.",
    )
    parser.add_argument(
        "--delay", type=float, default=DEFAULT_CASE_DELAY_SECONDS,
        help=f"Seconds to pace between cases, to stay under the model's "
             f"requests-per-minute cap (default: {DEFAULT_CASE_DELAY_SECONDS}).",
    )
    parser.add_argument(
        "--only", type=str, default=None,
        help="Comma-separated transaction_ids to re-run (e.g. T0078,T0112) -- "
             "for retrying just the cases that errored last time without "
             "re-spending quota on ones that already completed.",
    )
    args = parser.parse_args()

    with open(EVAL_SET_PATH) as f:
        cases = json.load(f)

    if args.only is not None:
        wanted = {tid.strip() for tid in args.only.split(",") if tid.strip()}
        cases = [c for c in cases if c["transaction_id"] in wanted]
        missing = wanted - {c["transaction_id"] for c in cases}
        if missing:
            print(f"WARNING: these --only ids were not found in eval_set.json: {sorted(missing)}")

    if args.limit is not None:
        cases = cases[: args.limit]

    print(f"Running {len(cases)} case(s) against the agent (delay={args.delay}s between cases)...")
    results = run_eval(cases, case_delay=args.delay)
    accuracy, scored_count = print_report(results)

    if scored_count == 0:
        print("\nFAILED: no cases completed scoring.")
        sys.exit(1)
    elif accuracy < ACCURACY_THRESHOLD:
        print(f"\nFAILED: accuracy {accuracy:.1%} is below the {ACCURACY_THRESHOLD:.0%} threshold.")
        sys.exit(1)
    else:
        print(f"\nPASSED: accuracy {accuracy:.1%} meets the {ACCURACY_THRESHOLD:.0%} threshold.")
        sys.exit(0)


if __name__ == "__main__":
    main()