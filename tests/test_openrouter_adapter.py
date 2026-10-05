import json
from types import SimpleNamespace

import pytest

from controlplane.openrouter_adapter import OpenRouterAdapter


def test_openrouter_adapter_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenRouterAdapter()


def test_openrouter_adapter_posts_model_and_tools_without_exposing_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-secret")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-oss-20b")
    captured = {}

    class FakeResponse:
        def read(self):
            return json.dumps(
                {
                    "id": "gen-test",
                    "model": "openai/gpt-oss-20b",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "I will use ForgeOS.",
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {
                                            "name": "create_test_file",
                                            "arguments": '{"name":"hello.txt","content":"hi"}',
                                        },
                                    }
                                ],
                            }
                        }
                    ],
                }
            ).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode())
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("controlplane.openrouter_adapter.urllib.request.urlopen", fake_urlopen)

    adapter = OpenRouterAdapter()
    result = adapter.complete(
        messages=[{"role": "user", "content": "Create hello.txt"}],
        tools=[{"type": "function", "name": "create_test_file"}],
    )

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert captured["body"]["model"] == "openai/gpt-oss-20b"
    assert captured["body"]["tools"] == [{"type": "function", "name": "create_test_file"}]
    assert captured["body"]["messages"] == [{"role": "user", "content": "Create hello.txt"}]
    assert result["provider"] == "openrouter"
    assert result["model"] == "openai/gpt-oss-20b"
    assert result["text"] == "I will use ForgeOS."
    assert result["tool_calls"][0]["name"] == "create_test_file"
    assert result["tool_calls"][0]["arguments"] == {"name": "hello.txt", "content": "hi"}


def test_openrouter_adapter_never_puts_api_key_in_payload(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "super-secret")
    captured = {}

    class FakeResponse:
        def read(self):
            return b'{"choices":[{"message":{"content":"ok"}}]}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        captured["body"] = request.data.decode()
        return FakeResponse()

    monkeypatch.setattr("controlplane.openrouter_adapter.urllib.request.urlopen", fake_urlopen)

    OpenRouterAdapter().complete(messages=[{"role": "user", "content": "hello"}])

    assert "super-secret" not in captured["body"]
