import sqlite3
from pathlib import Path

from app.agent.tools import (
    TOOL_SCHEMAS,
    escalate,
    issue_refund,
    lookup_customer_history,
    lookup_order,
    search_policy,
)
from app.data.seed import seed_db
from app.data.store import init_db, record_refund
from app.policy.kb import PolicyKB

DOCS_DIR = Path(__file__).resolve().parent.parent / "app" / "policy" / "docs"


def make_conn() -> sqlite3.Connection:
    conn = init_db(":memory:")
    seed_db(conn)
    return conn


def test_lookup_order_found():
    result = lookup_order(make_conn(), "order_1")
    assert result["found"] is True
    assert result["order"]["id"] == "order_1"
    assert result["order"]["customer_id"] == "cust_1"


def test_lookup_order_missing():
    assert lookup_order(make_conn(), "order_999") == {"found": False, "order": None}


def test_lookup_customer_history_counts_seeded_orders():
    # cust_1 owns order_1, order_11 (i-1 % 10 == 0), so two orders
    result = lookup_customer_history(make_conn(), "cust_1")
    assert len(result["orders"]) == 2
    assert {o["id"] for o in result["orders"]} == {"order_1", "order_11"}


def test_search_policy_returns_top_refund_doc():
    result = search_policy(PolicyKB(DOCS_DIR), "can I get a refund after 30 days")
    assert result["results"][0]["title"] == "refund_policy"
    assert result["results"][0]["excerpt"]


def test_search_policy_drops_zero_score_docs():
    result = search_policy(PolicyKB(DOCS_DIR), "zzzzqqqq xxxxyyyy")
    assert result == {"results": []}


def test_issue_refund_shape():
    result = issue_refund(make_conn(), "order_1", 12.0, "damaged")
    assert result == {"status": "issued", "order_id": "order_1", "amount": 12.0}


def test_escalate_shape():
    result = escalate(make_conn(), "ticket_1", "customer angry")
    assert result == {"status": "escalated", "ticket_id": "ticket_1", "summary": "customer angry"}


def test_tool_schemas_match_function_names():
    names = [s["name"] for s in TOOL_SCHEMAS]
    assert names == ["lookup_order", "lookup_customer_history", "search_policy",
                     "issue_refund", "escalate"]
    for schema in TOOL_SCHEMAS:
        assert schema["input_schema"]["type"] == "object"
        assert "conn" not in schema["input_schema"]["properties"]
        assert "kb" not in schema["input_schema"]["properties"]
    assert TOOL_SCHEMAS[-1]["input_schema"]["properties"].keys() == {"summary"}


def test_lookup_order_shows_prior_refunds():
    conn = make_conn()
    assert lookup_order(conn, "order_1")["refunded"] == 0
    record_refund(conn, "order_1", "tkt_1", 5.0)
    assert lookup_order(conn, "order_1")["refunded"] == 5.0
