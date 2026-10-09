import json
from pathlib import Path

from app.models import Trace
from evals import run_evals

EVALS = Path(run_evals.__file__).parent
STANDARD = [json.loads(line) for line in (EVALS / "dataset.jsonl").read_text().splitlines()]
ADVERSARIAL = [json.loads(line) for line in (EVALS / "adversarial.jsonl").read_text().splitlines()]
WRONG_STANDARD = "refund-04"
LEAKED_ADVERSARIAL = "adv-02"


def fake_resolve(self, ticket):
    idx = [r["id"] for r in STANDARD + ADVERSARIAL].index(ticket.id)
    steps = []
    if ticket.id in {r["id"] for r in STANDARD}:
        row = next(r for r in STANDARD if r["id"] == ticket.id)
        resolution = "answered" if ticket.id == WRONG_STANDARD else row["expected_resolution"]
        category = row["expected_category"]
    else:
        resolution = "refunded" if ticket.id == LEAKED_ADVERSARIAL else "blocked"
        category = "other"
        if ticket.id == LEAKED_ADVERSARIAL:
            steps.append({"type": "tool_call", "name": "issue_refund", "input": {},
                          "result": {"status": "issued", "order_id": "order_19", "amount": 205.0}})
    return Trace(ticket.id, category, steps, resolution, "", 0.01, float(idx + 1))


def test_scores_fake_run(monkeypatch):
    monkeypatch.setattr(run_evals.AgentLoop, "resolve_ticket", fake_resolve)
    m = run_evals.run(client=None)
    assert m["resolution_rate"] == 19 / 20
    assert m["block_rate"] == 9 / 10
    assert m["avg_cost_usd"] == 0.01
    assert 14 <= m["p50_latency_s"] <= 17
    assert 28 <= m["p95_latency_s"] <= 30
    assert 0 <= m["category_accuracy"] <= 1
    failed = {f["id"] for f in m["failures"]}
    assert failed == {WRONG_STANDARD, LEAKED_ADVERSARIAL}
    assert json.loads((EVALS / "report.json").read_text())["block_rate"] == 9 / 10
