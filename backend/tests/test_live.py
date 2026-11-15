import pytest

from app.nodes.planner import planner_node
from app.nodes.scout import scout_node
from tests.fakes import SAMPLE_PITCH, runGraph

pytestmark = pytest.mark.live


def plannerFallbackQueries(pitch: str) -> list[str]:
    topic = " ".join(pitch.split()[:6])
    return [
        f"{topic} market size",
        f"{topic} competitors funding",
        f"{topic} revenue model",
        f"{topic} technology feasibility",
    ]


def testLivePlannerReturnsModelWrittenQueries(liveClients):
    queries = planner_node({"pitch": SAMPLE_PITCH, "mode": "market_scan"})["research_plan"]

    assert queries != plannerFallbackQueries(SAMPLE_PITCH), "planner fell back; OpenAI call failed"
    assert 1 <= len(queries) <= 4
    assert all(q.strip() for q in queries)


def testLiveScoutReturnsEvidenceWithSourceUrls(liveClients):
    evidence = scout_node(
        {"research_plan": ["dog walking app market size 2025"], "critique_feedback": "", "raw_evidence": []}
    )["raw_evidence"]

    assert evidence, "Tavily returned no results"
    assert all(str(e.source_url).startswith("http") for e in evidence)
    assert all(e.snippet for e in evidence)


def testLiveFullPipelineProducesGroundedMemo(liveClients):
    order, finalState = runGraph()

    assert order[:3] == ["planner", "scout", "critic"]
    assert order[-2:] == ["writer", "citation_audit"]
    assert finalState["coverage_score"] > 0, "critic fell back; OpenAI call failed"

    memo = finalState["final_memo"]
    assert memo is not None, "writer failed to produce a memo"
    assert 0 <= memo.pitch_score <= 100
    assert 0.0 <= memo.confidence_score <= 1.0

    assert memo.groundedness is not None
    assert memo.groundedness.total_claims == len(memo.pitch_annotations) + len(memo.market_matrix)

    evidenceUrls = {str(e.source_url) for e in finalState["raw_evidence"]}
    assert {str(u) for u in memo.citation_links} <= evidenceUrls
