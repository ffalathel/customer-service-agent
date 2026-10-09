import re

REFUND_AUTO_APPROVE_LIMIT = 50.00

_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_CVV_RE = re.compile(r"(?i)((?:cvv|cvc|security code)\W{0,3}?)\d{3,4}\b")

_INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore prior instructions",
    "disregard the above",
    "you are now",
    "new instructions:",
    "system prompt",
    "act as",
)


def requires_human_approval(cumulative_refund_amount: float) -> bool:
    return cumulative_refund_amount > REFUND_AUTO_APPROVE_LIMIT


def redact_payment_details(text: str) -> str:
    text = _CARD_RE.sub("[REDACTED]", text)
    return _CVV_RE.sub(r"\1[REDACTED]", text)


# ponytail: keyword heuristic, upgrade to a classifier if adversarial eval false-negatives show up
def detect_prompt_injection(message: str) -> bool:
    normalized = " ".join(message.split()).lower()
    return any(phrase in normalized for phrase in _INJECTION_PHRASES)
