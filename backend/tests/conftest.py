import os
from pathlib import Path

from dotenv import dotenv_values

_backendDir = Path(__file__).resolve().parents[1]
_dotenvKeys = {**dotenv_values(_backendDir.parent / ".env"), **dotenv_values(_backendDir / ".env")}
LIVE_KEYS = {
    name: os.environ.get(name) or _dotenvKeys.get(name)
    for name in ("OPENAI_API_KEY", "TAVILY_API_KEY")
}

# Must run before any `app` import: the nodes build their OpenAI/Tavily clients at
# import time, and app.main calls load_dotenv(), which never overrides variables
# that are already set. This keeps real keys from a local .env out of the tests;
# only tests marked `live` receive LIVE_KEYS, via the liveClients fixture.
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["TAVILY_API_KEY"] = "test-tavily-key"
os.environ["ADMIN_KEY"] = "test-admin-key"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

import socket

import pytest
from fastapi.testclient import TestClient
from langchain_openai import ChatOpenAI
from tavily import TavilyClient

from app.main import app
from app.middleware import rateLimiter
from app.nodes import critic, planner, scout, writer
from tests.fakes import FakeOpenAI, FakeTavily

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
_realConnect = socket.socket.connect


def _loopbackOnlyConnect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if host not in _LOOPBACK_HOSTS:
        raise RuntimeError(f"Test attempted a real network connection to {address!r}")
    return _realConnect(self, address)


@pytest.fixture(autouse=True)
def blockExternalNetwork(request, monkeypatch):
    if request.node.get_closest_marker("live"):
        return
    monkeypatch.setattr(socket.socket, "connect", _loopbackOnlyConnect)


@pytest.fixture(autouse=True)
def resetRateLimiter():
    rateLimiter._requests.clear()
    yield
    rateLimiter._requests.clear()


@pytest.fixture
def fakeOpenAI(monkeypatch):
    fake = FakeOpenAI()
    chat = fake.chatModel()
    monkeypatch.setattr(planner, "planner_llm", chat.with_structured_output(planner.ResearchPlan))
    monkeypatch.setattr(critic, "critic_llm", chat.with_structured_output(critic.CritiqueResult))
    monkeypatch.setattr(writer, "writer_llm", chat.with_structured_output(writer.MemoSynthesis))
    yield fake
    assert not fake.unscripted, f"OpenAI called without a scripted reply for: {fake.unscripted}"


@pytest.fixture
def fakeTavily(monkeypatch):
    fake = FakeTavily()
    monkeypatch.setattr(scout, "tavily", fake)
    return fake


@pytest.fixture
def liveClients(monkeypatch):
    missing = [name for name, value in LIVE_KEYS.items() if not value]
    if missing:
        pytest.skip(f"live test needs {', '.join(missing)} in the environment or .env")

    for module, attr, schema in (
        (planner, "planner_llm", planner.ResearchPlan),
        (critic, "critic_llm", critic.CritiqueResult),
        (writer, "writer_llm", writer.MemoSynthesis),
    ):
        realChat = ChatOpenAI(
            model=module.llm.model_name,
            temperature=0,
            max_tokens=module.llm.max_tokens,
            api_key=LIVE_KEYS["OPENAI_API_KEY"],
        )
        monkeypatch.setattr(module, attr, realChat.with_structured_output(schema))

    monkeypatch.setattr(scout, "tavily", TavilyClient(api_key=LIVE_KEYS["TAVILY_API_KEY"]))


@pytest.fixture
def client():
    return TestClient(app)
