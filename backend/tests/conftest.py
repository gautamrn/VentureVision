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
import threading
import time

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from langchain_openai import ChatOpenAI
from sse_starlette.sse import AppStatus
from tavily import TavilyClient

from app.main import app
from app.middleware import metrics, rateLimiter
from app.nodes import critic, planner, scout, writer
from app.telemetry.usage import structuredOutput
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


@pytest.fixture(autouse=True)
def resetSseExitEvent():
    # sse-starlette binds this module-level event to the first event loop; each TestClient has its own.
    AppStatus.should_exit_event = None


@pytest.fixture(autouse=True)
def resetMetrics(monkeypatch):
    metrics._records.clear()
    monkeypatch.setattr(metrics, "_totalRuns", 0)
    monkeypatch.setattr(metrics, "_totalErrors", 0)


@pytest.fixture
def fakeOpenAI(monkeypatch):
    fake = FakeOpenAI()
    chat = fake.chatModel()
    monkeypatch.setattr(planner, "planner_llm", structuredOutput(chat, planner.ResearchPlan))
    monkeypatch.setattr(critic, "critic_llm", structuredOutput(chat, critic.CritiqueResult))
    monkeypatch.setattr(writer, "writer_llm", structuredOutput(chat, writer.MemoSynthesis))
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
        monkeypatch.setattr(module, attr, structuredOutput(realChat, schema))

    monkeypatch.setattr(scout, "tavily", TavilyClient(api_key=LIVE_KEYS["TAVILY_API_KEY"]))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def liveServer():
    """The app on a real loopback uvicorn server. TestClient buffers a whole streamed response
    before returning it, so incremental SSE delivery, cancellation, and disconnects need this."""
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", lifespan="off"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as http:
        yield http
    server.should_exit = True
    thread.join(timeout=5)
