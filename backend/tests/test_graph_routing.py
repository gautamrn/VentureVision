from app.graph.workflow import routeAfterCritic
from tests.fakes import SAMPLE_PITCH, critique, memoSynthesis, researchPlan, runGraph


def testRouteAfterCriticSendsValidatedStateToWriter():
    assert routeAfterCritic({"is_validated": True}) == "writer"


def testRouteAfterCriticSendsUnvalidatedStateBackToScout():
    assert routeAfterCritic({"is_validated": False}) == "scout"
    assert routeAfterCritic({}) == "scout"


def testGraphRunsPlannerScoutCriticWriterAuditInOrder(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors", "pet care market size"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    order, finalState = runGraph()

    assert order == ["planner", "scout", "critic", "writer", "citation_audit"]
    assert finalState["analysis_iteration"] == 1
    assert finalState["final_memo"] is not None


def testPlannerQueriesDriveScoutAndEvidenceReachesCritic(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors", "pet care market size"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    _, finalState = runGraph()

    assert fakeTavily.queries == ["dog walking app competitors", "pet care market size"]
    assert len(finalState["raw_evidence"]) == 2

    criticPrompt = fakeOpenAI.callsFor("CritiqueResult")[0]["messages"][-1]["content"]
    assert "Result for dog walking app competitors" in criticPrompt
    assert "Result for pet care market size" in criticPrompt


def testMarketScanCapsPlanAtFourQueries(fakeOpenAI, fakeTavily):
    sixQueries = [f"query {i}" for i in range(6)]
    fakeOpenAI.script("ResearchPlan", researchPlan(sixQueries))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    runGraph(mode="market_scan")

    assert fakeTavily.queries == sixQueries[:4]


def testPitchLabKeepsFullPlan(fakeOpenAI, fakeTavily):
    sixQueries = [f"query {i}" for i in range(6)]
    fakeOpenAI.script("ResearchPlan", researchPlan(sixQueries))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    runGraph(mode="pitch_lab")

    assert fakeTavily.queries == sixQueries


def testPlannerFallsBackToPitchDerivedQueriesWhenOpenAIOutputIsUnusable(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", "not json at all")
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    order, _ = runGraph()

    topic = " ".join(SAMPLE_PITCH.split()[:6])
    assert order == ["planner", "scout", "critic", "writer", "citation_audit"]
    assert fakeTavily.queries == [
        f"{topic} market size",
        f"{topic} competitors funding",
        f"{topic} revenue model",
        f"{topic} technology feasibility",
    ]
