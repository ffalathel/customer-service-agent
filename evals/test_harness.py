import json
from pathlib import Path

from app.models import Trace
import pytest

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


def test_scores_fake_run(monkeypatch, tmp_path):
    monkeypatch.setattr(run_evals.AgentLoop, "resolve_ticket", fake_resolve)
    report = tmp_path / "report.json"
    m = run_evals.run(client=None, report_path=report)
    assert m["resolution_rate"] == 20 / 21
    assert m["block_rate"] == 13 / 14
    assert m["category_accuracy"] == 1.0
    assert m["avg_cost_usd"] == 0.01
    assert m["p50_latency_s"] == pytest.approx(18.0)
    assert m["p95_latency_s"] == pytest.approx(34.2)
    failed = {f["id"] for f in m["failures"]}
    assert failed == {WRONG_STANDARD, LEAKED_ADVERSARIAL}
    assert json.loads(report.read_text()) == m


def test_baseline_unset_fails():
    with pytest.raises(AssertionError) as exc:
        run_evals.check_baseline(0.9, 0.0)
    assert str(exc.value) == (
        "baseline not set — run `python -m evals.run_evals` with ANTHROPIC_API_KEY "
        "and record resolution_rate in evals/baseline.json"
    )


def test_baseline_regression_fails():
    with pytest.raises(AssertionError):
        run_evals.check_baseline(0.8, 0.85)


def test_baseline_met_passes():
    run_evals.check_baseline(0.9, 0.85)
