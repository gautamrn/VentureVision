import json

import pytest

from app.nodes import critic, planner, writer
from app.nodes.scout import scout_node
from app.schemas.models import MemoOutput, RunResponse
from app.telemetry.collector import NodeCollector, collecting
from app.telemetry.pricing import PRICING, UnpricedModelError, llmCostUsd, modelPrice, searchCostUsd
from tests.fakes import SAMPLE_PITCH, critique, memoSynthesis, researchPlan, runGraph

ADMIN = {"X-Admin-Key": "test-admin-key"}
FOLLOW_UPS = "Rover funding 2025, Wag pricing per walk, pet care market size 2025, dog walker supply"


def scriptHappyPath(fakeOpenAI) -> None:
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis(pitchScore=71))


def streamEvents(client, pitch: str = SAMPLE_PITCH) -> list[tuple[str, dict]]:
    events, name = [], None
    with client.stream("POST", "/analyze/stream", json={"pitch": pitch}) as response:
        for line in response.iter_lines():
            if line.startswith("event: "):
                name = line[7:].strip()
            elif line.startswith("data: ") and name:
                events.append((name, json.loads(line[6:])))
                name = None
    return events


@pytest.mark.parametrize("module", [planner, critic, writer], ids=lambda m: m.__name__)
def testEveryNodeModelHasAPrice(module):
    assert modelPrice(module.llm.model_name)


def testDatedModelSnapshotsUseTheirFamilyPrice():
    assert modelPrice("gpt-4o-mini-2024-07-18") == PRICING.models["gpt-4o-mini"]
    with pytest.raises(UnpricedModelError):
        modelPrice("gpt-4o-mini-but-not-really")


def testAnalyzeMemoCarriesMeasuredTokensCostAndLatency(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI)
    fakeOpenAI.usage = {"prompt_tokens": 1000, "completion_tokens": 500}

    memo = RunResponse.model_validate(client.post("/analyze", json={"pitch": SAMPLE_PITCH}).json()).memo

    telemetry = memo.telemetry
    assert telemetry.agent_count == 4
    assert telemetry.llm_calls == 3
    assert (telemetry.prompt_tokens, telemetry.completion_tokens) == (3000, 1500)
    assert telemetry.llm_cost_usd == pytest.approx(3 * llmCostUsd("gpt-4o-mini", 1000, 500))
    assert telemetry.search_calls == 1
    assert telemetry.search_cost_usd == pytest.approx(searchCostUsd(1))
    assert telemetry.total_cost_usd == pytest.approx(telemetry.llm_cost_usd + telemetry.search_cost_usd)
    assert [n.node for n in telemetry.nodes] == ["planner", "scout", "critic", "writer", "citation_audit"]
    assert all(n.runs == 1 and n.total_ms >= 0 for n in telemetry.nodes)
    assert telemetry.duration_ms >= sum(n.total_ms for n in telemetry.nodes)
    assert telemetry.budget_exit_reason is None
    assert telemetry.pricing_as_of == PRICING.as_of


def testStreamedMemoAndAdminMetricsReportTheSameRunCost(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI)

    events = dict(streamEvents(client))

    telemetry = MemoOutput.model_validate(events["citation_audit"]["memo"]).telemetry
    assert telemetry is not None and telemetry.total_cost_usd > 0
    assert events["scout"] == {"evidenceCount": 1, "searches": 1, "failedSearches": 0}

    metrics = client.get("/admin/metrics", headers=ADMIN).json()
    run = metrics["recentRuns"][0]
    assert metrics["totalCostUsd"] == pytest.approx(telemetry.total_cost_usd)
    assert run["costUsd"] == pytest.approx(telemetry.total_cost_usd)
    assert run["promptTokens"] == telemetry.prompt_tokens
    assert set(run["nodeMs"]) == {"planner", "scout", "critic", "writer", "citation_audit"}


def testFailedSearchIsRecordedButNotBilled(fakeTavily):
    fakeTavily.failingQueries.add("broken query")

    with collecting(NodeCollector(node="scout")) as collector:
        scout_node({"research_plan": ["broken query", "ok query"], "critique_feedback": "", "raw_evidence": []})

    failed, succeeded = collector.searchCalls
    assert (failed.error, failed.credits, failed.cost_usd) == ("ConnectionError", 0, 0.0)
    assert succeeded.error is None and succeeded.cost_usd == searchCostUsd(1)


def testRunawayCriticLoopIsStoppedByTheBudgetCap(client, fakeOpenAI, fakeTavily, monkeypatch):
    monkeypatch.setattr(critic, "QUICK_MAX_ITERATIONS", 1000)
    monkeypatch.setenv("RUN_BUDGET_USD", "0.10")
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.2, False, FOLLOW_UPS))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    memo = RunResponse.model_validate(client.post("/analyze", json={"pitch": SAMPLE_PITCH}).json()).memo

    telemetry = memo.telemetry
    criticRounds = len(fakeOpenAI.callsFor("CritiqueResult"))
    assert 1 <= criticRounds < 1000
    assert telemetry.budget_usd == 0.10
    assert telemetry.budget_exit_reason.startswith(f"Research stopped after {criticRounds} rounds")
    assert telemetry.total_cost_usd <= 0.10
    assert telemetry.search_calls == 1 + 4 * (criticRounds - 1)


def testBudgetExitStillRunsWriterAndAudit(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.2, False, FOLLOW_UPS))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    order, finalState = runGraph(budgetUsd=0.01)

    assert order == ["planner", "scout", "critic", "writer", "citation_audit"]
    assert finalState["budget_exit_reason"].startswith("Research stopped after 1 round ")
    assert finalState["final_memo"] is not None


def testGenerousBudgetLeavesTheIterationCapInCharge(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.2, False, FOLLOW_UPS))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    order, finalState = runGraph(budgetUsd=100.0)

    assert order.count("scout") == critic.QUICK_MAX_ITERATIONS + 1
    assert finalState["budget_exit_reason"] is None
