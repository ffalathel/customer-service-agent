import dataclasses
import os
import uuid
from pathlib import Path

import anthropic
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import verify
from app.agent.loop import AgentLoop
from app.data.seed import seed_db
from app.data.store import get_trace, init_db, save_ticket
from app.models import Ticket
from app.policy.kb import PolicyKB

SECRET = os.environ["RESOLVE_SECRET"]  # fail closed: no default
conn = init_db(os.environ.get("RESOLVE_DB", "resolve.db"))
if conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0:
    seed_db(conn)
kb = PolicyKB(Path(__file__).parent / "policy" / "docs")
agent = AgentLoop(conn, kb, anthropic.Anthropic())

app = FastAPI()


_ID = r"^[A-Za-z0-9_-]{1,64}$"


class TicketIn(BaseModel):
    customer_id: str = Field(pattern=_ID)
    order_id: str | None = Field(default=None, pattern=_ID)
    message: str = Field(min_length=1, max_length=5000)


@app.post("/tickets")
def create_ticket(body: TicketIn, x_customer_token: str | None = Header(default=None)):
    if not x_customer_token or not verify(body.customer_id, x_customer_token, SECRET):
        raise HTTPException(status_code=401, detail="Invalid customer token")
    ticket = Ticket(uuid.uuid4().hex, body.customer_id, body.order_id, body.message, "open")
    save_ticket(conn, ticket)
    trace = agent.resolve_ticket(ticket)
    return {"ticket_id": ticket.id, "resolution": trace.resolution, "response": trace.response}


@app.get("/tickets/{ticket_id}")
def read_ticket(ticket_id: str, customer_id: str = Query(pattern=_ID),
                x_customer_token: str | None = Header(default=None)):
    if not x_customer_token or not verify(customer_id, x_customer_token, SECRET):
        raise HTTPException(status_code=401, detail="Invalid customer token")
    owner = conn.execute("SELECT customer_id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    trace = get_trace(conn, ticket_id)
    if trace is None or owner is None or owner[0] != customer_id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return dataclasses.asdict(trace)
