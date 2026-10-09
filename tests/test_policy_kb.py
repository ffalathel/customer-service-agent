from pathlib import Path

from app.policy.kb import PolicyKB

DOCS_DIR = Path(__file__).resolve().parent.parent / "app" / "policy" / "docs"


def test_search_returns_refund_policy_for_refund_query():
    results = PolicyKB(DOCS_DIR).search("can I get a refund after 30 days")
    assert results
    assert results[0].title == "refund_policy"
