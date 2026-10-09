from types import SimpleNamespace

import anthropic
import httpx

from app.agent.classify import classify_intent


def _client(create):
    return SimpleNamespace(messages=SimpleNamespace(create=create))


def _tool_response(category):
    block = SimpleNamespace(type="tool_use", name="classify", input={"category": category})
    return SimpleNamespace(content=[block])


def test_classify_intent_parses_tool_response():
    calls = []

    def fake(**kwargs):
        calls.append(kwargs)
        return _tool_response("refund_request")

    result = classify_intent(_client(fake), "I want a refund for order_1")

    assert result == "refund_request"
    assert calls[0]["tool_choice"] == {"type": "tool", "name": "classify"}


def test_classify_intent_falls_back_to_other_on_api_error():
    def fake(**kwargs):
        raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://x"))

    assert classify_intent(_client(fake), "hi") == "other"


def test_classify_intent_falls_back_to_other_on_unknown_category():
    def fake(**kwargs):
        return _tool_response("sales_pitch")

    assert classify_intent(_client(fake), "hi") == "other"
