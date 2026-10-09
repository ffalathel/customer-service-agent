"""Local interactive demo: the real agent on a fresh in-memory store.

Not the production API. It has no customer auth, so only run it on localhost (see demo.sh).
"""
import dataclasses
import uuid
from pathlib import Path

import anthropic
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.agent.guardrails import redact_payment_details
from app.agent.loop import AgentLoop
from app.data.seed import seed_db
from app.data.store import get_customer_orders, init_db, refunded_total, save_ticket
from app.models import Ticket
from app.policy.kb import PolicyKB

HERE = Path(__file__).parent
conn = init_db(":memory:")
seed_db(conn)
agent = AgentLoop(conn, PolicyKB(HERE.parent / "app" / "policy" / "docs"), anthropic.Anthropic())
api = FastAPI()


class TicketIn(BaseModel):
    customer_id: str
    order_id: str | None = None
    message: str = Field(min_length=1, max_length=5000)


@api.get("/")
def page():
    return FileResponse(HERE / "index.html")


@api.get("/customers")
def customers():
    return [{"id": cid, "name": name,
             "orders": [{"id": o.id, "items": o.items, "total": o.total, "status": o.status,
                         "refunded": refunded_total(conn, o.id)} for o in get_customer_orders(conn, cid)]}
            for cid, name in conn.execute("SELECT id, name FROM customers ORDER BY rowid")]


@api.post("/tickets")
def create_ticket(body: TicketIn):
    ticket = Ticket(uuid.uuid4().hex[:8], body.customer_id, body.order_id or None,
                    redact_payment_details(body.message), "open")
    save_ticket(conn, ticket)
    return {**dataclasses.asdict(agent.resolve_ticket(ticket)), "stored_message": ticket.message}


@api.post("/reset")
def reset():
    with conn:
        conn.executescript("DELETE FROM refunds; DELETE FROM tickets; DELETE FROM traces;")
    return {"ok": True}
