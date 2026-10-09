import re

REFUND_AUTO_APPROVE_LIMIT = 50.00

_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_CVV_RE = re.compile(
    r"(?i)((?:\bcvv2?\b|\bcvc2?\b|\bsecurity code\b)(?:\s*\b(?:is|number|code)\b)?[\s:=-]*)\d{3,4}\b"
)

_INJECTION_RES = [
    re.compile(p)
    for p in (
        r"\b(?:ignore|disregard|forget)\s+(?:(?:all|the|any|your|my)\s+)?(?:(?:previous|prior|above|earlier)\s+)?instructions\b",
        r"\bdisregard the above\b",
        r"\byou are now (?:a|an)\b",
        r"\bnew instructions:",
        r"\bsystem prompt\b",
        r"\bact as\b",
    )
]


def requires_human_approval(cumulative_refund_amount: float) -> bool:
    return cumulative_refund_amount > REFUND_AUTO_APPROVE_LIMIT


def redact_payment_details(text: str) -> str:
    text = _CARD_RE.sub("[REDACTED]", text)
    return _CVV_RE.sub(r"\1[REDACTED]", text)


# ponytail: keyword heuristic, upgrade to a classifier if adversarial eval false-negatives show up
def detect_prompt_injection(message: str) -> bool:
    normalized = " ".join(message.split()).lower()
    return any(r.search(normalized) for r in _INJECTION_RES)
