import importlib

import pytest
from fastapi.testclient import TestClient

from app.data.store import record_refunds
from app.models import Trace


@pytest.fixture
def demo(monkeypatch):
    server = importlib.reload(importlib.import_module("demo.server"))

    def fake_resolve(ticket):
        record_refunds(server.conn, ticket.id, [(ticket.order_id, 10.0, "test")])
        return Trace(ticket.id, "refund_request", [], "refunded", "Refund issued.", 0.01, 0.1)

    monkeypatch.setattr(server.agent, "resolve_ticket", fake_resolve)
    return server, TestClient(server.api)


def test_serves_page(demo):
    assert "text/html" in demo[1].get("/").headers["content-type"]


def test_customers_show_orders_and_refunds(demo):
    _, client = demo
    client.post("/tickets", json={"customer_id": "cust_1", "order_id": "order_1", "message": "refund"})
    customers = client.get("/customers").json()
    assert [c["id"] for c in customers] == [f"cust_{i}" for i in range(1, 11)]
    assert customers[0]["orders"][0] == {"id": "order_1", "items": ["Phone case"], "total": 12.0,
                                         "status": "delivered", "refunded": 10.0}


def test_ticket_is_redacted_before_storage(demo):
    server, client = demo
    r = client.post("/tickets", json={"customer_id": "cust_3", "order_id": "order_3",
                                      "message": "card 4111 1111 1111 1111 charged"}).json()
    assert r["resolution"] == "refunded"
    assert r["stored_message"] == "card [REDACTED] charged"
    assert server.conn.execute("SELECT message FROM tickets").fetchone()[0] == "card [REDACTED] charged"


def test_reset_clears_refunds(demo):
    _, client = demo
    client.post("/tickets", json={"customer_id": "cust_1", "order_id": "order_1", "message": "refund"})
    client.post("/reset")
    assert client.get("/customers").json()[0]["orders"][0]["refunded"] == 0
