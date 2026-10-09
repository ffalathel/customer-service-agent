import importlib

import pytest
from fastapi.testclient import TestClient

from app.auth import customer_token, verify
from app.data.store import save_trace
from app.models import Trace


SECRET = "test-secret"


def auth(customer_id):
    return {"X-Customer-Token": customer_token(customer_id, SECRET)}


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("RESOLVE_DB", ":memory:")
    monkeypatch.setenv("RESOLVE_SECRET", SECRET)
    main = importlib.reload(importlib.import_module("app.main"))

    def fake_resolve(ticket):
        trace = Trace(ticket.id, "refund", [{"type": "classify"}], "refunded", "Refund issued.", 0.01, 0.1)
        save_trace(main.conn, trace)
        return trace

    monkeypatch.setattr(main.agent, "resolve_ticket", fake_resolve)
    return TestClient(main.app)


def test_post_ticket_returns_resolution(api):
    r = api.post("/tickets", json={"customer_id": "cust_1", "order_id": "order_1", "message": "refund please"},
                 headers=auth("cust_1"))
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"ticket_id", "resolution", "response"}
    assert body["resolution"] == "refunded"
    assert body["response"] == "Refund issued."


def test_get_ticket_returns_stored_trace(api):
    ticket_id = api.post("/tickets", json={"customer_id": "cust_1", "message": "hi"},
                         headers=auth("cust_1")).json()["ticket_id"]
    r = api.get(f"/tickets/{ticket_id}", params={"customer_id": "cust_1"}, headers=auth("cust_1"))
    assert r.status_code == 200
    assert r.json()["ticket_id"] == ticket_id
    assert r.json()["resolution"] == "refunded"


def test_get_unknown_ticket_404(api):
    assert api.get("/tickets/unknown", params={"customer_id": "cust_1"}, headers=auth("cust_1")).status_code == 404


def test_empty_message_422(api):
    r = api.post("/tickets", json={"customer_id": "cust_1", "message": ""}, headers=auth("cust_1"))
    assert r.status_code == 422


def test_card_number_in_order_id_422(api):
    r = api.post("/tickets", json={"customer_id": "cust_1", "order_id": "4111 1111 1111 1111", "message": "hi"},
                 headers=auth("cust_1"))
    assert r.status_code == 422


def test_auth_verify():
    t = customer_token("cust_1", "s")
    assert verify("cust_1", t, "s") and not verify("cust_2", t, "s") and not verify("cust_1", t, "other")


def test_post_without_token_401(api):
    assert api.post("/tickets", json={"customer_id": "cust_1", "message": "hi"}).status_code == 401


def test_post_with_other_customers_token_401(api):
    r = api.post("/tickets", json={"customer_id": "cust_1", "message": "hi"}, headers=auth("cust_2"))
    assert r.status_code == 401


def test_get_other_customers_ticket_404(api):
    tid = api.post("/tickets", json={"customer_id": "cust_1", "message": "hi"}, headers=auth("cust_1")).json()["ticket_id"]
    assert api.get(f"/tickets/{tid}", params={"customer_id": "cust_2"}, headers=auth("cust_2")).status_code == 404
    assert api.get(f"/tickets/{tid}", params={"customer_id": "cust_1"}, headers=auth("cust_2")).status_code == 401
    assert api.get(f"/tickets/{tid}", params={"customer_id": "cust_1"}).status_code == 401


def test_stored_ticket_message_has_no_card_number(api):
    import app.main as main
    r = api.post("/tickets", headers=auth("cust_1"),
                 json={"customer_id": "cust_1", "message": "card 4111 1111 1111 1111 cvv 123, refund"})
    row = main.conn.execute("SELECT message FROM tickets WHERE id = ?", (r.json()["ticket_id"],)).fetchone()
    assert "4111" not in row[0] and "123" not in row[0]
