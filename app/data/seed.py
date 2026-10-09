import json

CUSTOMERS = [(f"cust_{i}", f"Customer {i}", f"customer{i}@example.com") for i in range(1, 11)]

TOTALS = [12.0, 19.99, 25.0, 33.4, 40.0, 45.5, 49.99, 55.0, 60.25, 75.0,
          89.9, 99.0, 110.0, 125.5, 140.0, 160.0, 175.25, 190.0, 205.0, 220.0]
ITEMS = ["Phone case", "Wireless earbuds", "USB-C cable", "Desk lamp", "Notebook"]
STATUSES = ["delivered", "shipped", "processing"]


def seed_db(conn) -> None:
    conn.executemany("INSERT INTO customers VALUES (?, ?, ?)", CUSTOMERS)
    orders = [
        (f"order_{i}", f"cust_{(i - 1) % 10 + 1}", json.dumps([ITEMS[(i - 1) % len(ITEMS)]]),
         total, STATUSES[(i - 1) % len(STATUSES)], f"2026-09-{i:02d}")
        for i, total in enumerate(TOTALS, start=1)
    ]
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", orders)
    conn.commit()
