import pytest

from app.graph.errors import describeFailure
from app.nodes.writer import writer_node
from app.schemas.models import EvidenceItem, MemoOutput
from tests.fakes import SAMPLE_PITCH, memoSynthesis


def evidenceItem(url: str, title: str = "Rover raises $310M") -> EvidenceItem:
    return EvidenceItem(query="dog walking competitors", title=title, snippet="Rover raised $310M.", source_url=url)


def writerState(evidence: list[EvidenceItem], mode: str = "market_scan") -> dict:
    return {"pitch": SAMPLE_PITCH, "mode": mode, "raw_evidence": evidence}


def testWriterParsesStructuredOutputIntoMemo(fakeOpenAI):
    fakeOpenAI.script("MemoSynthesis", memoSynthesis(pitchScore=67))

    memo = writer_node(writerState([evidenceItem("https://example.com/rover")]))["final_memo"]

    assert isinstance(memo, MemoOutput)
    assert memo.pitch_score == 67
    assert memo.subscores.market_size == 70
    assert memo.market_matrix[0].competitor == "Rover"
    assert memo.market_matrix[0].funding == "$310M"
    assert memo.investor_questions[0].question == "How do you acquire walkers?"
    assert memo.deal_context.red_flags == ["Low switching costs for owners."]
    assert memo.confidence_score == 0.7


def testWriterBuildsDeduplicatedCitationsFromEvidence(fakeOpenAI):
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())
    evidence = [
        evidenceItem("https://example.com/rover"),
        evidenceItem("https://example.com/rover", title="Rover pricing"),
        evidenceItem("https://example.com/wag"),
    ]

    memo = writer_node(writerState(evidence))["final_memo"]

    assert sorted(str(u) for u in memo.citation_links) == [
        "https://example.com/rover",
        "https://example.com/wag",
    ]


def testWriterWithNoEvidenceProducesNoCitations(fakeOpenAI):
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    memo = writer_node(writerState([]))["final_memo"]

    assert memo.citation_links == []


def testWriterRequestsMemoSynthesisSchemaAndSendsEvidence(fakeOpenAI):
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    writer_node(writerState([evidenceItem("https://example.com/rover")]))

    call = fakeOpenAI.callsFor("MemoSynthesis")[0]
    assert call["body"]["response_format"]["type"] == "json_schema"
    humanMessage = call["messages"][-1]["content"]
    assert SAMPLE_PITCH in humanMessage
    assert "Source: https://example.com/rover" in humanMessage


def testWriterUsesPitchCoachPromptInPitchLabMode(fakeOpenAI):
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    writer_node(writerState([], mode="pitch_lab"))

    systemMessage = fakeOpenAI.callsFor("MemoSynthesis")[0]["messages"][0]["content"]
    assert systemMessage.startswith("You are a pitch coach.")


def assertBadModelOutput(fakeOpenAI) -> None:
    with pytest.raises(Exception) as raised:
        writer_node(writerState([]))
    assert describeFailure("writer", raised.value)[0] == "bad_model_output"


def testWriterOutputMissingRequiredFieldsIsABadModelOutputFailure(fakeOpenAI):
    incomplete = memoSynthesis()
    del incomplete["deal_context"]
    fakeOpenAI.script("MemoSynthesis", incomplete)

    assertBadModelOutput(fakeOpenAI)


def testWriterOutputWithWrongTypesIsABadModelOutputFailure(fakeOpenAI):
    wrongTypes = memoSynthesis()
    wrongTypes["subscores"]["market_size"] = "very large"
    fakeOpenAI.script("MemoSynthesis", wrongTypes)

    assertBadModelOutput(fakeOpenAI)


def testWriterOutputThatIsNotJsonIsABadModelOutputFailure(fakeOpenAI):
    fakeOpenAI.script("MemoSynthesis", "I'm sorry, I can't help with that.")

    assertBadModelOutput(fakeOpenAI)
