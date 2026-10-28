"""
Guardrail for AI Fraud-Review Copilot.

SCOPE.md's one committed guardrail: no definitive fraud claims + PII
redaction. Two functions, two different correct responses to a violation:

  - redact_pii(case_note, customer_name): PII (the customer's name) found ->
    redact and return the cleaned note. Safe to auto-fix — a name is a
    swappable noun, replacing it doesn't risk mangling a sentence's meaning.

  - check_fraud_language(case_note): definitive fraud language found ->
    raise GuardrailViolation, don't try to auto-rewrite. Regex-patching an
    arbitrary matched phrase into "compliant" language is unreliable and
    could quietly change meaning in a way nobody reviews — a loud failure
    is more auditable than a silently-patched one.

Code-level checks, not prompt instructions — prompts get ignored under
pressure, a code-level check doesn't.

Redaction target is the customer's name, not card numbers: this project
has no card-number field anywhere in its schema (no real financial data,
per SCOPE.md) — the PII that actually appears in every case note is the
customer's name. Location strings and customer/transaction ids are
deliberately NOT redacted: locations are what geo-anomaly reasoning is
about, and ids are synthetic internal identifiers needed for audit trail.
"""

import re


class GuardrailViolation(Exception):
    """Raised when generated text asserts fraud as settled fact rather than
    recommending escalate/clear for a human to decide."""
    pass


# Patterns that assert fraud as a settled conclusion, not a recommendation
# or a hedged possibility. Deliberately narrow: "potential fraud", "fraud
# risk", "suspected fraud", "evidence of fraud" are all fine — those
# describe evidence or risk, they don't declare the verdict.
#
# _SAFE_CONTINUATION guards every pattern below that ends in a bare
# fraud(?:ulent)?\b: \b only checks a word/non-word character transition,
# not a clause boundary, so fraud(?:ulent)?\b alone matches just as readily
# inside "there is fraud risk associated with..." as it does in a real
# standalone assertion — the space before "risk" satisfies \b exactly like
# a period would. Confirmed concretely: without this guard, "There is
# fraud risk associated with this merchant category" raised
# GuardrailViolation, directly contradicting "fraud risk" being named as
# allowed two lines up. The lookahead excludes the specific noun
# continuations that turn "fraud" into a hedge/descriptor rather than a
# verdict. Pattern 4 (fraud (is) confirmed) doesn't need it: "confirmed"
# is already the final token there, so a trailing word can't undercut a
# completed assertion the way it can for the other 8.
_SAFE_CONTINUATION = r"(?!\s+(?:risk|pattern|indicator|score|rate|signal|alert))"
_FRAUD_ASSERTION_PATTERNS = [
    rf"\bthis (?:is|was) (?:definitely |certainly |clearly )?fraud(?:ulent)?\b{_SAFE_CONTINUATION}",
    rf"\b(?:the )?(?:transaction|customer|account) (?:is|was) (?:definitely |certainly |clearly )?fraud(?:ulent)?\b{_SAFE_CONTINUATION}",
    rf"\bconfirmed (?:as )?fraud(?:ulent)?\b{_SAFE_CONTINUATION}",
    r"\bfraud(?:ulent)? (?:is )?confirmed\b",
    rf"\bconstitutes fraud\b{_SAFE_CONTINUATION}",
    rf"\b(?:committed|committing) fraud\b{_SAFE_CONTINUATION}",
    rf"\bdefinitely fraud(?:ulent)?\b{_SAFE_CONTINUATION}",
    rf"\bcertainly fraud(?:ulent)?\b{_SAFE_CONTINUATION}",
    rf"\bis (?:clearly |definitely |certainly )?fraud(?:ulent)?\b{_SAFE_CONTINUATION}",
]
_FRAUD_ASSERTION_REGEX = re.compile("|".join(_FRAUD_ASSERTION_PATTERNS), re.IGNORECASE)


def check_fraud_language(case_note):
    """
    Raise GuardrailViolation if the case note asserts fraud as fact,
    anywhere in its free-text fields (evidence, risk_factors).
    """
    text_fields = [case_note.evidence] + list(case_note.risk_factors)
    for text in text_fields:
        match = _FRAUD_ASSERTION_REGEX.search(text)
        if match:
            raise GuardrailViolation(
                f"Definitive fraud language found: '{match.group(0)}' in: {text!r}"
            )


def redact_pii(case_note, customer_name):
    """
    Replace occurrences of the customer's name (full name and individual
    name parts) with '[CUSTOMER]' across the case note's free-text fields.
    Returns a new CaseNote — doesn't mutate the input.
    """
    # Longest-first so the full name is replaced before its individual
    # parts get a chance to match the leftovers.
    name_parts = sorted(
        {customer_name, *[p for p in customer_name.split() if len(p) > 1]},
        key=len,
        reverse=True,
    )

    def _redact(text):
        for part in name_parts:
            text = re.sub(
                rf"\b{re.escape(part)}\b", "[CUSTOMER]", text, flags=re.IGNORECASE
            )
        return text

    return case_note.model_copy(
        update={
            "evidence": _redact(case_note.evidence),
            "risk_factors": [_redact(rf) for rf in case_note.risk_factors],
        }
    )