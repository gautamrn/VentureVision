import pytest

from app.graph.errors import NodeFailure
from app.nodes import critic
from app.nodes.critic import critic_node
from tests.fakes import critique, memoSynthesis, researchPlan, runGraph


def testLowCoverageTriggersAnotherScoutRound(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script(
        "CritiqueResult",
        critique(0.5, False, "Rover funding 2025, Wag pricing per walk"),
        critique(0.85, True),
    )
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    order, finalState = runGraph()

    assert order == ["planner", "scout", "critic", "scout", "critic", "writer", "citation_audit"]
    assert fakeTavily.queries == [
        "dog walking app competitors",
        "Rover funding 2025",
        "Wag pricing per walk",
    ]
    assert finalState["analysis_iteration"] == 2
    assert finalState["coverage_score"] == 0.85


def testEvidenceAccumulatesAcrossScoutRounds(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script(
        "CritiqueResult",
        critique(0.4, False, "Rover funding 2025, Wag pricing per walk"),
        critique(0.9, True),
    )
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    _, finalState = runGraph()

    titles = [e.title for e in finalState["raw_evidence"]]
    assert titles == [
        "Result for dog walking app competitors",
        "Result for Rover funding 2025",
        "Result for Wag pricing per walk",
    ]


def testSufficientCoverageOnFirstPassSkipsExtraScoutRounds(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.8, True))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    order, _ = runGraph()

    assert order.count("scout") == 1
    assert len(fakeOpenAI.callsFor("CritiqueResult")) == 1


@pytest.mark.parametrize(
    "mode, maxIterations",
    [
        ("market_scan", critic.QUICK_MAX_ITERATIONS),
        ("pitch_lab", critic.DEEP_MAX_ITERATIONS),
    ],
)
def testIterationCapForcesExitToWriter(fakeOpenAI, fakeTavily, mode, maxIterations):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.3, False, "more competitor data"))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    order, finalState = runGraph(mode=mode)

    assert order == ["planner"] + ["scout", "critic"] * (maxIterations + 1) + ["writer", "citation_audit"]
    assert len(fakeOpenAI.callsFor("CritiqueResult")) == maxIterations
    assert finalState["analysis_iteration"] == maxIterations
    assert finalState["is_validated"] is True
    assert finalState["final_memo"] is not None


def testCriticAtCapValidatesWithoutCallingOpenAI(fakeOpenAI):
    result = critic_node(
        {
            "mode": "market_scan",
            "analysis_iteration": critic.QUICK_MAX_ITERATIONS,
            "research_plan": ["q"],
            "raw_evidence": [],
        }
    )

    assert result == {"is_validated": True, "analysis_iteration": critic.QUICK_MAX_ITERATIONS}
    assert fakeOpenAI.calls == []


def testCriticFailureStopsTheRunInsteadOfPassingUnjudgedEvidence(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", "not json at all")

    with pytest.raises(NodeFailure) as failure:
        runGraph()

    assert (failure.value.node, failure.value.kind) == ("critic", "bad_model_output")
    assert fakeOpenAI.callsFor("MemoSynthesis") == []
