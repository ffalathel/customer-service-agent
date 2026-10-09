import os
from typing import Literal, get_args

import anthropic

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")

IntentCategory = Literal["refund_request", "order_status", "policy_question", "other"]

_TOOL = {
    "name": "classify",
    "description": "Record the intent category of a customer support message.",
    "input_schema": {
        "type": "object",
        "properties": {"category": {"type": "string", "enum": list(get_args(IntentCategory))}},
        "required": ["category"],
    },
}

_SYSTEM = (
    "Classify the customer's support message into exactly one category: "
    "refund_request (wants money back), order_status (asks where or when an order is), "
    "policy_question (asks about rules or policies), or other. Call the classify tool."
)


def classify_intent(client: anthropic.Anthropic, message: str) -> IntentCategory:
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=100,
            system=_SYSTEM,
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "classify"},
            messages=[{"role": "user", "content": message}],
        )
    except anthropic.APIError:
        return "other"
    block = next((b for b in response.content if b.type == "tool_use"), None)
    category = block.input.get("category") if block else None
    return category if category in get_args(IntentCategory) else "other"
