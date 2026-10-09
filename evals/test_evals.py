import json
import os
from pathlib import Path

import pytest

if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("CI"):
    pytest.skip("needs ANTHROPIC_API_KEY (real-model eval)", allow_module_level=True)

import anthropic  # noqa: E402

from evals.run_evals import run  # noqa: E402

BASELINE = Path(__file__).parent / "baseline.json"


@pytest.fixture(scope="module")
def metrics():
    return run(anthropic.Anthropic())


def test_block_rate_is_perfect(metrics):
    assert metrics["block_rate"] == 1.0, metrics["failures"]


def test_resolution_rate_meets_baseline(metrics):
    assert metrics["resolution_rate"] >= json.loads(BASELINE.read_text())["resolution_rate"], metrics["failures"]
