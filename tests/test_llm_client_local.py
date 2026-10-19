"""The ``local:`` provider: a self-hosted OpenAI-compatible server named by LOCAL_BASE_URL, reached through the SDK."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from rtlscout.llm_client import DeepInfraClient, OpenAICompatibleClient
from rtlscout.runner import build_client, parse_model_spec


def test_model_spec_accepts_the_local_provider():
    assert parse_model_spec("local:Qwen/Qwen3-32B") == ("local", "Qwen/Qwen3-32B")
    with pytest.raises(ValueError):
        parse_model_spec("ollama:qwen3")


def test_build_client_needs_the_base_url(monkeypatch):
    monkeypatch.delenv("LOCAL_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="LOCAL_BASE_URL"):
        build_client("local", "qwen3")


def test_build_client_points_the_sdk_at_the_server(monkeypatch):
    monkeypatch.setenv("LOCAL_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.delenv("LOCAL_API_KEY", raising=False)
    client = build_client("local", "qwen3")
    assert isinstance(client, OpenAICompatibleClient) and not isinstance(client, DeepInfraClient)
    assert str(client._client.base_url).rstrip("/") == "http://127.0.0.1:8000/v1"
    assert client._client.api_key == "not-needed"            # the SDK insists on a key; local servers ignore it
    monkeypatch.setenv("LOCAL_API_KEY", "secret")
    assert build_client("local", "qwen3")._client.api_key == "secret"


def test_deepinfra_keeps_its_hosted_url():
    client = DeepInfraClient(model="m", api_key="k")
    assert str(client._client.base_url).rstrip("/") == DeepInfraClient.DEEPINFRA_BASE_URL


class _Server(BaseHTTPRequestHandler):
    """Answers one chat completion the way vLLM or Ollama would: a tool call, usage, no provider field."""
    requests: list = []

    def do_POST(self):                                     # noqa: N802 (http.server's naming)
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Server.requests.append((self.path, body))
        reply = {"id": "cmpl-1", "object": "chat.completion", "model": body["model"],
                 "choices": [{"index": 0, "finish_reason": "tool_calls",
                              "message": {"role": "assistant", "content": None,
                                          "tool_calls": [{"id": "call_1", "type": "function",
                                                          "function": {"name": "ls", "arguments": "{}"}}]}}],
                 "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15}}
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):                          # keep pytest output clean
        pass


def test_round_trip_through_a_local_server(monkeypatch):
    httpd = HTTPServer(("127.0.0.1", 0), _Server)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("LOCAL_BASE_URL", f"http://127.0.0.1:{httpd.server_address[1]}/v1")
        client = build_client("local", "qwen3")
        tools = [{"type": "function", "function": {"name": "ls", "description": "list", "parameters": {"type": "object"}}}]
        out = client.chat_completion([{"role": "user", "content": "go"}], tools=tools)
    finally:
        httpd.shutdown()
    path, body = _Server.requests[-1]
    assert path == "/v1/chat/completions" and body["model"] == "qwen3" and body["tools"] == tools
    assert out.content is None and out.finish_reason == "tool_calls" and out.provider is None
    assert [(c.id, c.name, c.arguments) for c in out.tool_calls] == [("call_1", "ls", "{}")]
    assert out.usage.input_tokens == 12 and out.usage.output_tokens == 3
