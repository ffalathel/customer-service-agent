import json
import sqlite3

from app.models import Customer, Order, Ticket, Trace

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (id TEXT PRIMARY KEY, name TEXT, email TEXT);
CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, customer_id TEXT, items TEXT,
    total REAL, status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, customer_id TEXT, order_id TEXT,
    message TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS traces (ticket_id TEXT PRIMARY KEY, category TEXT, steps TEXT,
    resolution TEXT, response TEXT, cost_usd REAL, latency_s REAL);
CREATE TABLE IF NOT EXISTS refunds (order_id TEXT, ticket_id TEXT, amount REAL);
"""


def init_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.executescript(SCHEMA)
    return conn


def _order(row) -> Order:
    return Order(row[0], row[1], json.loads(row[2]), row[3], row[4], row[5])


def get_order(conn, order_id: str) -> Order | None:
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return _order(row) if row else None


def get_customer(conn, customer_id: str) -> Customer | None:
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    return Customer(*row) if row else None


def get_customer_orders(conn, customer_id: str) -> list[Order]:
    rows = conn.execute("SELECT * FROM orders WHERE customer_id = ?", (customer_id,))
    return [_order(r) for r in rows]


def save_ticket(conn, ticket: Ticket) -> None:
    conn.execute("INSERT OR REPLACE INTO tickets VALUES (?, ?, ?, ?, ?)",
                 (ticket.id, ticket.customer_id, ticket.order_id, ticket.message, ticket.status))
    conn.commit()


def save_trace(conn, trace: Trace) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO traces VALUES (?, ?, ?, ?, ?, ?, ?)",
        (trace.ticket_id, trace.category, json.dumps(trace.steps), trace.resolution,
         trace.response, trace.cost_usd, trace.latency_s),
    )
    conn.commit()


def get_trace(conn, ticket_id: str) -> Trace | None:
    row = conn.execute("SELECT * FROM traces WHERE ticket_id = ?", (ticket_id,)).fetchone()
    if not row:
        return None
    return Trace(row[0], row[1], json.loads(row[2]), row[3], row[4], row[5], row[6])


def record_refund(conn, order_id: str, ticket_id: str, amount: float) -> None:
    conn.execute("INSERT INTO refunds VALUES (?, ?, ?)", (order_id, ticket_id, amount))
    conn.commit()


def refunded_total(conn, order_id: str) -> float:
    return conn.execute("SELECT COALESCE(SUM(amount), 0) FROM refunds WHERE order_id = ?", (order_id,)).fetchone()[0]
