import json
import sqlite3
import time

import anthropic

from app.agent import tools
from app.agent.classify import MODEL, classify_intent
from app.agent.guardrails import detect_prompt_injection, redact_payment_details, requires_human_approval
from app.data.store import get_order, save_trace
from app.models import Ticket, Trace
from app.policy.kb import PolicyKB

MAX_TOOL_ITERATIONS = 6
INPUT_USD_PER_TOKEN = 3 / 1_000_000
OUTPUT_USD_PER_TOKEN = 15 / 1_000_000
BLOCKED_REPLY = "Sorry, I can't help with that request."
ESCALATED_REPLY = "I've passed your ticket to a human agent who will follow up with you."
SYSTEM = (
    "You are a customer support agent for an online store. The customer_id and order_id are given. "
    "Look up the order and search policy before acting. Use issue_refund only when policy allows it. "
    "Escalate when unsure."
)


class AgentLoop:
    def __init__(self, conn: sqlite3.Connection, kb: PolicyKB, client: anthropic.Anthropic):
        self.conn, self.kb, self.client = conn, kb, client

    def resolve_ticket(self, ticket: Ticket) -> Trace:
        start = time.perf_counter()
        message = redact_payment_details(ticket.message)
        steps, cost, text, escalated, refunded, category = [], 0.0, "", False, 0.0, "other"
        if detect_prompt_injection(message):
            steps, text, escalated = [{"type": "blocked_injection"}], BLOCKED_REPLY, None
        else:
            category = classify_intent(self.client, message)
            steps.append({"type": "classify", "category": category})
            messages = [{"role": "user", "content": (
                f"customer_id: {ticket.customer_id}\norder_id: {ticket.order_id}\n\n{message}")}]
            for _ in range(MAX_TOOL_ITERATIONS):
                r = self.client.messages.create(model=MODEL, max_tokens=1024, system=SYSTEM,
                                                tools=tools.TOOL_SCHEMAS, messages=messages)
                cost += r.usage.input_tokens * INPUT_USD_PER_TOKEN + r.usage.output_tokens * OUTPUT_USD_PER_TOKEN
                if r.stop_reason != "tool_use":
                    text = "".join(b.text for b in r.content if b.type == "text")
                    break
                results = []
                for b in (b for b in r.content if b.type == "tool_use"):
                    result, why, refunded = self._run(ticket, b.name, b.input, refunded, steps)
                    steps.append({"type": "tool_call", "name": b.name, "input": b.input, "result": result})
                    if why is not None:
                        why = why or "Escalated by agent."
                        escalated = why
                        if b.name != "escalate":
                            self._escalate(ticket, why, steps)
                        break
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(result)})
                if escalated:
                    break
                messages += [{"role": "assistant", "content": r.content}, {"role": "user", "content": results}]
            else:
                escalated = "Agent did not converge within the tool-call limit."
            if escalated and not any(x.get("name") == "escalate" for x in steps):
                self._escalate(ticket, escalated, steps)
        resolution = ("blocked" if escalated is None else "escalated" if escalated
                      else "refunded" if refunded else "answered")
        trace = Trace(ticket.id, category, steps, resolution,
                      redact_payment_details(ESCALATED_REPLY if escalated else text),
                      cost, time.perf_counter() - start)
        save_trace(self.conn, trace)
        return trace

    def _escalate(self, ticket, summary, steps):
        steps.append({"type": "tool_call", "name": "escalate", "input": {"summary": summary},
                      "result": tools.escalate(self.conn, ticket.id, summary)})

    def _run(self, ticket, name, args, refunded, steps):
        """Returns (result, escalation_reason_or_None, cumulative_refund)."""
        try:
            if name == "lookup_order":
                result = tools.lookup_order(self.conn, args["order_id"])
                o = result["order"]
                if not result["found"] or o["customer_id"] != ticket.customer_id:
                    return {"found": False}, "Order not found or not owned by this customer.", refunded
                return result, None, refunded
            if name == "lookup_customer_history":
                return tools.lookup_customer_history(self.conn, ticket.customer_id), None, refunded
            if name == "search_policy":
                return tools.search_policy(self.kb, args["query"]), None, refunded
            if name == "escalate":
                return tools.escalate(self.conn, ticket.id, args["summary"]), args["summary"], refunded
            if name == "issue_refund":
                order, amount = get_order(self.conn, args["order_id"]), float(args["amount"])
                if not order or order.customer_id != ticket.customer_id or not 0 < amount <= order.total:
                    return {"error": "invalid refund"}, "Invalid refund proposal.", refunded
                total = round(refunded + amount, 2)
                if requires_human_approval(total):
                    steps.append({"type": "guardrail", "rule": "refund_limit", "decision": "escalate", "amount": total})
                    return ({"status": "blocked"},
                            f"Refund total ${total:.2f} exceeds the $50 human-approval threshold.", refunded)
                return tools.issue_refund(self.conn, order.id, amount, args["reason"]), None, total
        except (KeyError, TypeError, ValueError):
            return {"error": "bad arguments"}, f"Malformed arguments for {name}.", refunded
        return {"error": "unknown tool"}, f"Unknown tool {name}.", refunded
