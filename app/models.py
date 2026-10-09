from dataclasses import dataclass


@dataclass
class Order:
    id: str
    customer_id: str
    items: list[str]
    total: float
    status: str
    created_at: str


@dataclass
class Customer:
    id: str
    name: str
    email: str


@dataclass
class Ticket:
    id: str
    customer_id: str
    order_id: str | None
    message: str
    status: str


@dataclass
class Trace:
    ticket_id: str
    category: str
    steps: list[dict]
    resolution: str
    response: str
    cost_usd: float
    latency_s: float
