import base64
import re
import unicodedata

REFUND_AUTO_APPROVE_LIMIT = 50.00

_CARD_RE = re.compile(r"(?<!\d)(?:\d[ .-]?){12,}\d(?!\d)")
_DIGIT_WORDS_RE = re.compile(
    r"(?i)\b(?:(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)\b[\s,-]*){12,}")
_CVV_RE = re.compile(
    r"(?i)((?:\bcvv2?\b|\bcvc2?\b|\bsecurity code\b)(?:\s*\b(?:is|number|code|no)\b)*[\s:=-]*)\d{3,4}\b"
)

_INJECTION_RES = [
    re.compile(p)
    for p in (
        r"\b(?:ignore|disregard|forget|skip|override|bypass)\s+(?:(?:all|the|any|your|my|of)\s+)*"
        r"(?:(?:previous|prior|above|earlier|preceding|existing)\s+)?"
        r"(?:instructions|directions|rules|guidelines|prompts?|everything above)\b",
        r"\bdisregard the above\b",
        r"\byou are now (?:a|an)\b",
        r"\bnew instructions:",
        r"\bact as (?:a|an|if|my|the|though)\b",
        r"\bpretend (?:you(?:'re| are)|to be)\b",
    )
]
# applied to the letters-only form, so spaced-out attacks ("i g n o r e ...") are caught
_COMPACT_RES = [
    re.compile(p)
    for p in (
        r"(?:ignore|disregard|forget)(?:all|the|any|your|my)?(?:previous|prior|above|earlier)?instructions",
        r"disregardtheabove",
    )
]
_LOOKALIKES = str.maketrans("аеорсухіјѕοαιν", "aeopcyxijsoaiv")
_B64_RE = re.compile(r"[A-Za-z0-9+/=]{16,}")


def requires_human_approval(cumulative_refund_amount: float) -> bool:
    return cumulative_refund_amount > REFUND_AUTO_APPROVE_LIMIT


def redact_payment_details(text: str) -> str:
    text = _DIGIT_WORDS_RE.sub("[REDACTED] ", text)
    text = _CARD_RE.sub("[REDACTED]", text)
    return _CVV_RE.sub(r"\1[REDACTED]", text)


# ponytail: keyword heuristic (layer 1); the intent classifier is layer 2, swap for a trained detector if evals show bypasses that slip past both
def detect_prompt_injection(message: str, _depth: int = 0) -> bool:
    n = unicodedata.normalize("NFKC", message)
    n = "".join(c for c in n if unicodedata.category(c) != "Cf").translate(_LOOKALIKES)
    n = " ".join(n.lower().split())
    if any(r.search(n) for r in _INJECTION_RES) or any(r.search(re.sub(r"[^a-z]", "", n)) for r in _COMPACT_RES):
        return True
    if _depth:
        return False
    for tok in _B64_RE.findall(message):
        try:
            decoded = base64.b64decode(tok, validate=True).decode("utf-8")
        except ValueError:  # binascii.Error and UnicodeDecodeError are both ValueErrors
            continue
        if detect_prompt_injection(decoded, 1):
            return True
    return False
