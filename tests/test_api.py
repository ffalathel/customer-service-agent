import importlib

import pytest
from fastapi.testclient import TestClient

from app.data.store import save_trace
from app.models import Trace


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("RESOLVE_DB", ":memory:")
    main = importlib.reload(importlib.import_module("app.main"))

    def fake_resolve(ticket):
        trace = Trace(ticket.id, "refund", [{"type": "classify"}], "refunded", "Refund issued.", 0.01, 0.1)
        save_trace(main.conn, trace)
        return trace

    monkeypatch.setattr(main.agent, "resolve_ticket", fake_resolve)
    return TestClient(main.app)


def test_post_ticket_returns_resolution(api):
    r = api.post("/tickets", json={"customer_id": "cust_1", "order_id": "order_1", "message": "refund please"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"ticket_id", "resolution", "response"}
    assert body["resolution"] == "refunded"
    assert body["response"] == "Refund issued."


def test_get_ticket_returns_stored_trace(api):
    ticket_id = api.post("/tickets", json={"customer_id": "cust_1", "message": "hi"}).json()["ticket_id"]
    r = api.get(f"/tickets/{ticket_id}")
    assert r.status_code == 200
    assert r.json()["ticket_id"] == ticket_id
    assert r.json()["resolution"] == "refunded"


def test_get_unknown_ticket_404(api):
    assert api.get("/tickets/unknown").status_code == 404


def test_empty_message_422(api):
    r = api.post("/tickets", json={"customer_id": "cust_1", "message": ""})
    assert r.status_code == 422


def test_card_number_in_order_id_422(api):
    r = api.post("/tickets", json={"customer_id": "cust_1", "order_id": "4111 1111 1111 1111", "message": "hi"})
    assert r.status_code == 422
