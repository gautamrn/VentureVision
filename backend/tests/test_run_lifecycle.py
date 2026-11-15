import json
import threading
import time
from contextlib import contextmanager

import pytest

from app.graph.workflow import resumableGraph
from app.nodes import critic
from app.runs import registry as registryModule
from app.runs.executor import registry
from app.runs.registry import RunBusyError, RunRegistry
from app.schemas.models import MemoOutput
from tests.fakes import SAMPLE_PITCH, critique, memoSynthesis, researchPlan

ADMIN = {"X-Admin-Key": "test-admin-key"}
THREE_QUERIES = ["dog walking app competitors", "pet care market size", "rover pricing"]


@pytest.fixture
def client(liveServer):
    return liveServer


def sseEvents(response):
    name = None
    for line in response.iter_lines():
        if line.startswith("event: "):
            name = line[7:].strip()
        elif line.startswith("data: ") and name:
            yield name, json.loads(line[6:])
            name = None


@contextmanager
def openStream(client, path: str = "/analyze/stream", body: dict | None = None):
    with client.stream("POST", path, json=body if body is not None else {"pitch": SAMPLE_PITCH}) as response:
        yield response, sseEvents(response)


def collect(client, path: str = "/analyze/stream", body: dict | None = None) -> list[tuple[str, dict]]:
    with openStream(client, path, body) as (_, events):
        return list(events)


def waitUntilIdle(timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while registry.activeCount and time.monotonic() < deadline:
        time.sleep(0.02)
    assert registry.activeCount == 0, "run worker thread did not finish"


def recentRun(client) -> dict:
    return client.get("/admin/metrics", headers=ADMIN).json()["recentRuns"][0]


def checkpointExists(runId: str) -> bool:
    return runId in resumableGraph.checkpointer.storage


def scriptHappyPath(fakeOpenAI, queries: list[str] | None = None) -> None:
    fakeOpenAI.script("ResearchPlan", researchPlan(queries or ["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())


def testStreamOpensWithRunIdAndStreamsEachSearchAsItCompletes(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI, THREE_QUERIES[:2])

    events = collect(client)

    names = [name for name, _ in events]
    assert names == ["run", "planner", "evidence", "evidence", "scout", "critic", "writer", "citation_audit"]
    run = events[0][1]
    assert run["attempt"] == 1 and run["retriesLeft"] == 2 and len(run["runId"]) >= 20
    first = events[2][1]
    assert first == {
        "round": 1,
        "query": "dog walking app competitors",
        "status": "ok",
        "error": None,
        "items": [{"title": "Result for dog walking app competitors", "url": "https://example.com/dog-walking-app-competitors"}],
    }
    waitUntilIdle()
    assert not checkpointExists(run["runId"])


def testSearchesWithNoResultsAreAnEmptyResultNotAnError(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI)
    fakeTavily.emptyQueries.add("dog walking app competitors")

    events = dict(collect(client))

    assert events["evidence"]["status"] == "ok" and events["evidence"]["items"] == []
    assert events["scout"] == {"evidenceCount": 0, "searches": 1, "failedSearches": 0}
    assert "error" not in events and "citation_audit" in events


def testSearchOutageIsARetryableScoutFailureNotAnEmptyResult(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI)
    fakeTavily.failAll = True

    events = collect(client)

    assert [name for name, _ in events] == ["run", "planner", "evidence", "error"]
    assert events[2][1]["status"] == "error" and events[2][1]["error"] == "ConnectionError"
    error = events[-1][1]
    assert error["node"] == "scout" and error["kind"] == "upstream_api" and error["retryable"] is True
    assert error["message"] == "Web search failed: all 1 Tavily searches failed (ConnectionError)."
    waitUntilIdle()
    assert recentRun(client)["status"] == "error"


def testRetryResumesAtTheFailedNodeWithoutRerunningEarlierAgents(client, fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", "not json at all", memoSynthesis(pitchScore=73))

    first = collect(client)
    error = first[-1][1]
    assert (first[-1][0], error["node"], error["kind"]) == ("error", "writer", "bad_model_output")
    waitUntilIdle()
    assert checkpointExists(error["runId"])

    retry = collect(client, f"/runs/{error['runId']}/retry", body={})

    assert [name for name, _ in retry] == ["run", "writer", "citation_audit"]
    assert retry[0][1]["attempt"] == 2 and retry[0][1]["retriesLeft"] == 1
    assert fakeTavily.queries == ["dog walking app competitors"]
    assert len(fakeOpenAI.callsFor("ResearchPlan")) == 1
    assert len(fakeOpenAI.callsFor("CritiqueResult")) == 1

    memo = MemoOutput.model_validate(retry[-1][1]["memo"])
    assert memo.pitch_score == 73
    writerTiming = next(n for n in memo.telemetry.nodes if n.node == "writer")
    assert writerTiming.runs == 2, "the failed writer attempt's time and tokens stay in the run total"
    assert memo.telemetry.llm_calls == 3, "the unparseable reply raised inside the SDK, so its usage is unknown"

    waitUntilIdle()
    metrics = client.get("/admin/metrics", headers=ADMIN).json()
    assert (metrics["totalRuns"], metrics["totalErrors"]) == (1, 0)
    assert metrics["recentRuns"][0]["status"] == "success"
    assert not checkpointExists(error["runId"])


def testRetryIsRefusedAfterTheLastAllowedAttempt(client, fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", "not json at all")

    runId = collect(client)[-1][1]["runId"]
    retryable = []
    for _ in range(registryModule.MAX_RETRIES):
        waitUntilIdle()
        retryable.append(collect(client, f"/runs/{runId}/retry", body={})[-1][1]["retryable"])

    assert retryable == [True, False]
    waitUntilIdle()
    assert client.post(f"/runs/{runId}/retry").status_code == 404


def testRetryOfUnknownOrSucceededRunIs404(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI)
    runId = collect(client)[0][1]["runId"]
    waitUntilIdle()

    assert client.post(f"/runs/{runId}/retry").status_code == 404
    assert client.post("/runs/not-a-run/retry").status_code == 404
    assert client.post("/runs/not-a-run/cancel").status_code == 404


def testCancelEndpointStopsTheRunBetweenSearches(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI, THREE_QUERIES)
    firstSearchMayFinish = threading.Event()
    fakeTavily.beforeSearch = lambda query: firstSearchMayFinish.wait(5)

    with openStream(client) as (_, events):
        name, run = next(events)
        assert name == "run"
        assert next(events)[0] == "planner"

        response = client.post(f"/runs/{run['runId']}/cancel")
        assert response.json() == {"runId": run["runId"], "status": "cancelling"}
        firstSearchMayFinish.set()
        rest = list(events)

    assert [name for name, _ in rest] == ["evidence", "cancelled"]
    assert rest[-1][1] == {"runId": run["runId"], "node": "scout"}
    assert fakeTavily.queries == THREE_QUERIES[:1], "remaining searches were skipped"
    assert fakeOpenAI.callsFor("CritiqueResult") == []

    waitUntilIdle()
    record = recentRun(client)
    assert record["status"] == "cancelled"
    assert record["searchCalls"] == 1 and record["costUsd"] > 0
    assert not checkpointExists(run["runId"])
    assert client.post(f"/runs/{run['runId']}/cancel").status_code == 404


def testCancelBetweenNodesRecordsNoTimingForTheNodeThatNeverStarted(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI)
    searchMayFinish = threading.Event()
    fakeTavily.beforeSearch = lambda query: searchMayFinish.wait(5)

    with openStream(client) as (_, events):
        _, run = next(events)
        assert next(events)[0] == "planner"
        client.post(f"/runs/{run['runId']}/cancel")
        searchMayFinish.set()
        rest = list(events)

    assert [name for name, _ in rest] == ["evidence", "scout", "cancelled"]
    assert rest[-1][1]["node"] == "critic"
    waitUntilIdle()
    assert set(recentRun(client)["nodeMs"]) == {"planner", "scout"}


def testClientDisconnectCancelsTheOrphanedRun(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI, THREE_QUERIES)
    firstSearchMayFinish = threading.Event()
    fakeTavily.beforeSearch = lambda query: firstSearchMayFinish.wait(5)

    with openStream(client) as (_, events):
        name, run = next(events)
        assert name == "run"
        assert next(events)[0] == "planner"

    handle = registry.get(run["runId"])
    deadline = time.monotonic() + 5
    while not handle.control.cancelled and time.monotonic() < deadline:
        time.sleep(0.01)
    assert handle.control.cancelled, "server did not notice the client disconnect"
    firstSearchMayFinish.set()

    waitUntilIdle()
    assert recentRun(client)["status"] == "cancelled"
    assert fakeTavily.queries == THREE_QUERIES[:1]
    assert fakeOpenAI.callsFor("CritiqueResult") == []


def testCriticAtIterationCapReportsCapInsteadOfZeroCoverage(client, fakeOpenAI, fakeTavily, monkeypatch):
    monkeypatch.setattr(critic, "QUICK_MAX_ITERATIONS", 1)
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.4, False, "rover pricing"))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    critics = [data for name, data in collect(client) if name == "critic"]

    assert [(c["coverageScore"], c["iterationCapReached"]) for c in critics] == [(0.4, False), (None, True)]


def testRegistryRefusesRunsBeyondTheConcurrencyCap():
    forgotten: list[str] = []
    runs = RunRegistry(onForget=forgotten.append)
    handles = [runs.start("market_scan", 0.25) for _ in range(registryModule.MAX_ACTIVE_RUNS)]

    with pytest.raises(RunBusyError):
        runs.start("market_scan", 0.25)

    runs.finish(handles[0], "cancelled")
    assert runs.start("market_scan", 0.25)
    assert forgotten == [handles[0].runId]
