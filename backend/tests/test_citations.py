from datetime import datetime, timezone

import pytest

from app.graph.errors import describeFailure
from app.nodes.critic import citation_audit_node
from app.nodes.writer import writer_node
from app.runs.events import serializeNodeOutput
from app.schemas.models import Citation, EvidenceItem, MarketCompetitor, MemoOutput, PitchAnnotation
from tests.fakes import (
    SAMPLE_PITCH,
    annotationDraft,
    competitorDraft,
    critique,
    memoSynthesis,
    researchPlan,
    runGraph,
)

RETRIEVED_AT = datetime(2026, 11, 14, 9, 30, tzinfo=timezone.utc)
ROVER_URL = "https://example.com/rover"
ROVER_QUOTE = "Rover has raised $310M across six rounds."


def evidenceItem(url: str = ROVER_URL, snippet: str = f"Funding history. {ROVER_QUOTE} It operates in 14 countries.") -> EvidenceItem:
    return EvidenceItem(query="rover funding", title="Rover funding", snippet=snippet, source_url=url, retrieved_at=RETRIEVED_AT)


def citation(quote: str = ROVER_QUOTE, url: str = ROVER_URL) -> Citation:
    return Citation(quote=quote, source_url=url, retrieved_at=RETRIEVED_AT)


def annotation(annotationType: str, cite: Citation | None = None) -> PitchAnnotation:
    return PitchAnnotation(excerpt="vetted local walkers", annotation_type=annotationType, note="n", citation=cite)


def memoWith(annotations: list[PitchAnnotation], competitors: list[MarketCompetitor] | None = None) -> MemoOutput:
    base = memoSynthesis()
    base["pitch_annotations"] = [a.model_dump() for a in annotations]
    base["market_matrix"] = [c.model_dump() for c in (competitors or [])]
    return MemoOutput.model_validate({**base, "citation_links": []})


def audit(memo: MemoOutput, mode: str = "market_scan", evidence: list[EvidenceItem] | None = None) -> MemoOutput:
    state = {"final_memo": memo, "mode": mode, "raw_evidence": evidence if evidence is not None else [evidenceItem()]}
    return citation_audit_node(state)["final_memo"]


# Critic citation audit


def testUncitedStrongClaimIsDowngradedAndCounted():
    audited = audit(memoWith([annotation("strong")]))

    claim = audited.pitch_annotations[0]
    assert claim.annotation_type == "needs_research"
    assert claim.downgraded_from == "strong"
    assert claim.citation is None
    assert audited.groundedness.downgraded_claims == 1


def testUncitedStrongClaimInPitchLabFallsBackToUnsubstantiated():
    audited = audit(memoWith([annotation("strong")]), mode="pitch_lab")

    assert audited.pitch_annotations[0].annotation_type == "unsubstantiated"
    assert audited.pitch_annotations[0].downgraded_from == "strong"


def testCitedStrongClaimIsUntouched():
    original = annotation("strong", citation())

    audited = audit(memoWith([original]))

    assert audited.pitch_annotations[0] == original
    assert audited.groundedness.downgraded_claims == 0
    assert audited.groundedness.cited_claims == 1


def testCitedContradictedClaimIsUntouched():
    original = annotation("contradicted", citation())

    audited = audit(memoWith([original]))

    assert audited.pitch_annotations[0] == original


def testUncitedContradictedClaimIsDowngraded():
    audited = audit(memoWith([annotation("contradicted")]))

    assert audited.pitch_annotations[0].annotation_type == "needs_research"
    assert audited.pitch_annotations[0].downgraded_from == "contradicted"
    assert audited.groundedness.downgraded_claims == 1


def testStrongClaimWithQuoteNotInEvidenceIsDowngraded():
    fabricated = citation(quote="Rover has raised $2B and is profitable.")

    audited = audit(memoWith([annotation("strong", fabricated)]))

    assert audited.pitch_annotations[0].annotation_type == "needs_research"
    assert audited.pitch_annotations[0].citation is None


def testStrongClaimCitingUnretrievedUrlIsDowngraded():
    wrongSource = citation(url="https://example.com/not-retrieved")

    audited = audit(memoWith([annotation("strong", wrongSource)]))

    assert audited.pitch_annotations[0].annotation_type == "needs_research"


def testQuoteMatchIgnoresCaseAndWhitespace():
    loose = citation(quote="  rover HAS raised\n$310M across   six rounds. ")

    audited = audit(memoWith([annotation("strong", loose)]))

    assert audited.pitch_annotations[0].annotation_type == "strong"


def testQuoteOfTruncatedClauseWithAddedPeriodIsAccepted():
    item = evidenceItem(snippet="The global DevOps market was valued at USD 16.2 billion in 2025 and is projected to grow.")
    truncated = citation(quote="The global DevOps market was valued at USD 16.2 billion in 2025.")

    audited = audit(memoWith([annotation("strong", truncated)]), evidence=[item])

    assert audited.pitch_annotations[0].annotation_type == "strong"


def testQuoteWithTypographicPunctuationIsAccepted():
    item = evidenceItem(snippet="Rover's walkers aren't employees, they are contractors.")
    curly = citation(quote="Rover\u2019s walkers aren\u2019t employees")

    audited = audit(memoWith([annotation("strong", curly)]), evidence=[item])

    assert audited.pitch_annotations[0].annotation_type == "strong"


def testQuoteFromEvidenceTitleIsAccepted():
    titled = EvidenceItem(
        query="q", title="Buildkite vs GitHub Actions | CI platform comparison", snippet="Pricing table.",
        source_url=ROVER_URL, retrieved_at=RETRIEVED_AT,
    )

    audited = audit(memoWith([annotation("strong", citation(quote="Buildkite vs GitHub Actions"))]), evidence=[titled])

    assert audited.pitch_annotations[0].annotation_type == "strong"


def testQuoteShorterThanThreeWordsIsRejected():
    audited = audit(memoWith([annotation("strong", citation(quote="$310M."))]))

    assert audited.pitch_annotations[0].annotation_type == "needs_research"


def testQuoteWithChangedWordsIsStillRejected():
    reworded = citation(quote="Rover has raised $310M over six rounds.")

    audited = audit(memoWith([annotation("strong", reworded)]))

    assert audited.pitch_annotations[0].annotation_type == "needs_research"


def testUncitedNoEvidenceVerdictIsNotCountedAsDowngrade():
    audited = audit(memoWith([annotation("needs_research")]))

    assert audited.pitch_annotations[0].annotation_type == "needs_research"
    assert audited.pitch_annotations[0].downgraded_from is None
    assert audited.groundedness.downgraded_claims == 0


def testGroundednessCountsAnnotationsAndMarketRows():
    memo = memoWith(
        [annotation("strong", citation()), annotation("strong"), annotation("needs_research")],
        competitors=[
            MarketCompetitor(competitor="Rover", pricing="-", funding="$310M", citation=citation()),
            MarketCompetitor(competitor="Wag", pricing="-", funding="-", citation=citation(quote="Wag raised $1B.")),
        ],
    )

    audited = audit(memo)

    assert audited.groundedness.model_dump() == {"cited_claims": 2, "total_claims": 5, "downgraded_claims": 1}
    assert audited.market_matrix[1].citation is None


def testAuditPassesThroughMissingMemo():
    assert citation_audit_node({"final_memo": None, "raw_evidence": []}) == {"final_memo": None}


# Writer citation resolution and verdict prompt


def testWriterResolvesCitationUrlAndDateFromEvidenceItem(fakeOpenAI):
    fakeOpenAI.script(
        "MemoSynthesis",
        memoSynthesis(annotations=[annotationDraft("strong", evidenceRef=1, evidenceQuote=ROVER_QUOTE)]),
    )

    memo = writer_node({"pitch": SAMPLE_PITCH, "mode": "market_scan", "raw_evidence": [evidenceItem()]})["final_memo"]

    assert memo.pitch_annotations[0].citation == citation()


@pytest.mark.parametrize("badRef", [0, 2, None])
def testWriterDropsCitationWithInvalidEvidenceRef(fakeOpenAI, badRef):
    fakeOpenAI.script(
        "MemoSynthesis",
        memoSynthesis(annotations=[annotationDraft("strong", evidenceRef=badRef, evidenceQuote=ROVER_QUOTE)]),
    )

    memo = writer_node({"pitch": SAMPLE_PITCH, "mode": "market_scan", "raw_evidence": [evidenceItem()]})["final_memo"]

    assert memo.pitch_annotations[0].citation is None


def testWriterNumbersEvidenceWithRetrievalDate(fakeOpenAI):
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    writer_node({"pitch": SAMPLE_PITCH, "mode": "market_scan", "raw_evidence": [evidenceItem()]})

    humanMessage = fakeOpenAI.callsFor("MemoSynthesis")[0]["messages"][-1]["content"]
    assert f"[E1] Source: {ROVER_URL}\nRetrieved: 2026-11-14" in humanMessage


@pytest.mark.parametrize("mode, noEvidenceVerdict", [("market_scan", "needs_research"), ("pitch_lab", "unsubstantiated")])
def testWriterPromptStatesContradictedBoundary(fakeOpenAI, mode, noEvidenceVerdict):
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    writer_node({"pitch": SAMPLE_PITCH, "mode": mode, "raw_evidence": []})

    systemPrompt = fakeOpenAI.callsFor("MemoSynthesis")[0]["messages"][0]["content"]
    assert 'absence of evidence is never "contradicted"' in systemPrompt
    assert f'the verdict is "{noEvidenceVerdict}", not "contradicted"' in systemPrompt


def testWriterRejectsUnknownVerdict(fakeOpenAI):
    fakeOpenAI.script("MemoSynthesis", memoSynthesis(annotations=[annotationDraft("refuted")]))

    with pytest.raises(Exception) as raised:
        writer_node({"pitch": SAMPLE_PITCH, "mode": "market_scan", "raw_evidence": []})
    assert describeFailure("writer", raised.value)[0] == "bad_model_output"


# All three verdicts through the full graph


def testPipelineCarriesAllThreeVerdictsWithCitations(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["rover funding", "dog walking market size"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script(
        "MemoSynthesis",
        memoSynthesis(
            annotations=[
                annotationDraft("strong", "vetted local walkers", 1, "Evidence about rover funding."),
                annotationDraft("contradicted", "no direct competitors", 2, "Evidence about dog walking market size."),
                annotationDraft("needs_research", "20% commission per walk"),
            ],
            competitors=[competitorDraft("Rover", 1, "Evidence about rover funding.")],
        ),
    )

    _, finalState = runGraph()
    memo = finalState["final_memo"]

    verdicts = [(a.excerpt, a.annotation_type, a.downgraded_from) for a in memo.pitch_annotations]
    assert verdicts == [
        ("vetted local walkers", "strong", None),
        ("no direct competitors", "contradicted", None),
        ("20% commission per walk", "needs_research", None),
    ]
    assert str(memo.pitch_annotations[1].citation.source_url) == "https://example.com/dog-walking-market-size"
    assert memo.pitch_annotations[2].citation is None
    assert memo.groundedness.model_dump() == {"cited_claims": 3, "total_claims": 4, "downgraded_claims": 0}


def testPipelineDowngradesStrongClaimWhoseQuoteTavilyNeverReturned(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["rover funding"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script(
        "MemoSynthesis",
        memoSynthesis(annotations=[annotationDraft("strong", evidenceRef=1, evidenceQuote="Rover is profitable.")]),
    )

    _, finalState = runGraph()

    claim = finalState["final_memo"].pitch_annotations[0]
    assert (claim.annotation_type, claim.downgraded_from) == ("needs_research", "strong")


# Streaming contract


def testWriterEventSignalsReadinessWithoutLeakingUnauditedMemo():
    memo = memoWith([annotation("strong")])

    assert serializeNodeOutput("writer", {"final_memo": memo}) == {"memoReady": True}
    assert serializeNodeOutput("writer", {"final_memo": None}) == {"memoReady": False}


def testCitationAuditEventCarriesAuditedMemo():
    audited = audit(memoWith([annotation("strong", citation())]))

    payload = serializeNodeOutput("citation_audit", {"final_memo": audited})

    assert payload["memo"]["groundedness"] == {"cited_claims": 1, "total_claims": 1, "downgraded_claims": 0}
    assert payload["memo"]["pitch_annotations"][0]["citation"]["retrieved_at"] == "2026-11-14T09:30:00Z"
