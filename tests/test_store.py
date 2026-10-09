from app.data.seed import seed_db
from app.data.store import get_customer, get_customer_orders, get_order, get_trace, init_db, save_trace
from app.models import Order, Trace


def test_init_db_creates_empty_tables():
    conn = init_db(":memory:")
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"customers", "orders", "tickets", "traces"} <= names
    assert get_order(conn, "order_1") is None


def test_seed_then_get_order():
    conn = init_db(":memory:")
    seed_db(conn)
    assert get_order(conn, "order_1") == Order(
        id="order_1", customer_id="cust_1", items=["Phone case"], total=12.0,
        status="delivered", created_at="2026-09-01",
    )
    assert get_order(conn, "missing") is None
    assert get_customer(conn, "cust_1").id == "cust_1"


def test_get_customer_orders_returns_all_for_customer():
    conn = init_db(":memory:")
    seed_db(conn)
    orders = get_customer_orders(conn, "cust_1")
    assert [o.id for o in orders] == ["order_1", "order_11"]
    assert all(o.customer_id == "cust_1" for o in orders)


def test_save_and_get_trace_round_trip():
    conn = init_db(":memory:")
    trace = Trace(
        ticket_id="t_1", category="refund",
        steps=[{"tool": "get_order", "input": {"order_id": "order_1"}}],
        resolution="refunded", response="Refund issued.", cost_usd=0.0123, latency_s=1.5,
    )
    save_trace(conn, trace)
    assert get_trace(conn, "t_1") == trace
    assert get_trace(conn, "missing") is None
