from dataclasses import asdict

from app.data.store import get_customer_orders, get_order
from app.policy.kb import PolicyKB


def lookup_order(conn, order_id: str) -> dict:
    order = get_order(conn, order_id)
    return {"found": order is not None, "order": asdict(order) if order else None}


def lookup_customer_history(conn, customer_id: str) -> dict:
    return {"orders": [asdict(o) for o in get_customer_orders(conn, customer_id)]}


def search_policy(kb: PolicyKB, query: str) -> dict:
    hits = [d for d in kb.search(query) if d.score > 0]
    return {"results": [{"title": d.title, "excerpt": d.text} for d in hits]}


def issue_refund(conn, order_id: str, amount: float, reason: str) -> dict:
    # ponytail: no DB write; the trace records refunds until a refunds table exists
    return {"status": "issued", "order_id": order_id, "amount": amount}


def escalate(conn, ticket_id: str, summary: str) -> dict:
    return {"status": "escalated", "ticket_id": ticket_id, "summary": summary}


_STR = {"type": "string"}

TOOL_SCHEMAS = [
    {
        "name": "lookup_order",
        "description": "Look up an order by id. Returns whether it was found and its details.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": _STR},
            "required": ["order_id"],
        },
    },
    {
        "name": "lookup_customer_history",
        "description": "List all orders belonging to a customer.",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": _STR},
            "required": ["customer_id"],
        },
    },
    {
        "name": "search_policy",
        "description": "Search company policy documents (refunds, shipping, cancellations, "
                       "escalation, payment security) and return matching excerpts.",
        "input_schema": {
            "type": "object",
            "properties": {"query": _STR},
            "required": ["query"],
        },
    },
    {
        "name": "issue_refund",
        "description": "Issue a refund for an order. Only call after policy allows it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": _STR,
                "amount": {"type": "number"},
                "reason": _STR,
            },
            "required": ["order_id", "amount", "reason"],
        },
    },
    {
        "name": "escalate",
        "description": "Hand the ticket to a human agent with a summary of the case.",
        "input_schema": {
            "type": "object",
            "properties": {"ticket_id": _STR, "summary": _STR},
            "required": ["ticket_id", "summary"],
        },
    },
]
