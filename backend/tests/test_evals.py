import json
import runpy
import shutil
import sys
from collections import Counter
from pathlib import Path

import pytest

from app.evals.dataset import REPO_DIR, loadCases, loadDataset, loadManifest
from app.evals.harness import heuristicPredictor, regressionMessage, runEvals
from app.evals.results import buildSummary
from app.schemas.evals import EvalBaseline, EvidenceSnippet, GoldenCase, LabelScore
from app.verification.claimVerifier import verifyClaim
from app.verification.heuristic import classifyClaim, numericAgreement, quantities

RUN_EVALS = REPO_DIR / "evals" / "run_evals.py"
DEVOPS = EvidenceSnippet(
    source_url="https://example.com/devops",
    title="DevOps market report",
    text="DevOps Market Size Worth $12.85 Billion by 2025 | CAGR: 18.60%.",
)


def case(claim: str, label: str = "supported", evidence: list[EvidenceSnippet] | None = None) -> GoldenCase:
    return GoldenCase(
        id="t-1", pitch_excerpt="", claim=claim, evidence=[DEVOPS] if evidence is None else evidence,
        label=label, origin="seed-constructed", notes="",
    )


@pytest.fixture
def evalsDir(tmp_path, monkeypatch):
    for name in ("golden_dataset.jsonl", "dataset.json"):
        shutil.copy(REPO_DIR / "evals" / name, tmp_path / name)
    monkeypatch.setenv("EVALS_DIR", str(tmp_path))
    return tmp_path


def runCli(*args: str) -> int:
    argv = sys.argv
    sys.argv = [str(RUN_EVALS), *args]
    try:
        runpy.run_path(str(RUN_EVALS), run_name="__main__")
    except SystemExit as exc:
        return int(exc.code or 0)
    finally:
        sys.argv = argv
    return 0


# Dataset


def testGoldenDatasetIsValidBalancedAndVersioned():
    cases = loadDataset()

    assert len(cases) == 36
    assert Counter(c.label for c in cases) == {"supported": 12, "unsupported": 12, "contradicted": 12}
    assert loadManifest().version == 1


def testEveryVerdictThatAssertsSomethingHasEvidenceWithASource():
    for golden in loadDataset():
        if golden.label != "unsupported":
            assert golden.evidence, golden.id
        assert all(e.source_url and e.source_url.startswith("https://") and e.text for e in golden.evidence), golden.id


def testDatasetRejectsUnknownFieldsAndDuplicateIds(tmp_path):
    line = case("x").model_dump()
    (tmp_path / "extra.jsonl").write_text(json.dumps({**line, "confidence": 0.9}) + "\n")
    (tmp_path / "dupes.jsonl").write_text((json.dumps(line) + "\n") * 2)

    with pytest.raises(ValueError, match="Extra inputs"):
        loadCases(tmp_path / "extra.jsonl")
    with pytest.raises(ValueError, match="duplicate case ids: t-1"):
        loadCases(tmp_path / "dupes.jsonl")


# Heuristic baseline


def testQuantitiesParseMoneyPercentScaleAndSkipYears():
    found = quantities("USD 1.47 Billion in 2025, a CAGR of 10.18%, over $10B")

    assert [(q.kind, q.value, q.comparator) for q in found] == [
        ("money", 1.47e9, "approx"),
        ("percent", 10.18, "approx"),
        ("money", 10e9, "atLeast"),
    ]


@pytest.mark.parametrize(
    "claim, expected",
    [
        ("worth over $10B", "consistent"),
        ("worth about $13 billion", "consistent"),
        ("stays under $5 billion", "conflict"),
        ("growing 30% a year", "conflict"),
        ("a big market", "none"),
    ],
)
def testNumericAgreementRespectsComparators(claim, expected):
    assert numericAgreement(claim, DEVOPS.text) == expected


def testHeuristicNeverCallsMissingEvidenceAContradiction():
    assert classifyClaim("The DevOps market will never exceed $1B.", []).label == "unsupported"


def testHeuristicRunIsDeterministic():
    cases = loadDataset()
    first = runEvals(cases, "heuristic", heuristicPredictor(), model=None, datasetVersion=1, datasetSha="x")
    second = runEvals(cases, "heuristic", heuristicPredictor(), model=None, datasetVersion=1, datasetSha="x")

    assert [c.predicted for c in first.cases] == [c.predicted for c in second.cases]
    assert first.cost_usd == 0.0


# Baseline regression gate


def baseline(accuracy: float) -> EvalBaseline:
    return EvalBaseline(
        run_id="base", mode="heuristic", dataset_version=1, case_count=36, overall_accuracy=accuracy,
        labels=[LabelScore(label="supported", total=1, correct=1, accuracy=100.0)],
    )


def testRegressionGateAllowsThreePointsAndFailsBeyond():
    run = runEvals([case("worth over $10B")], "heuristic", heuristicPredictor(), model=None, datasetVersion=1, datasetSha="x")

    assert run.overall_accuracy == 100.0
    assert regressionMessage(run, baseline(103.0)) is None
    assert "3.1 points below" in regressionMessage(run, baseline(103.1))


def testCliRecordsRunAndPassesBaselineCheck(evalsDir):
    assert runCli("--mode", "heuristic", "--write-baseline") == 0
    assert runCli("--mode", "heuristic", "--check-baseline") == 0

    assert len(list((evalsDir / "results" / "history").glob("*_heuristic_*.json"))) == 2


def testCliFailsWhenAccuracyDropsBelowBaseline(evalsDir):
    (evalsDir / "results").mkdir()
    (evalsDir / "results" / "baseline_heuristic.json").write_text(baseline(99.0).model_dump_json())

    assert runCli("--mode", "heuristic", "--check-baseline", "--no-record") == 1
    assert not (evalsDir / "results" / "history").exists()


def testSummaryJoinsFailuresWithTheirCases(evalsDir):
    runCli("--mode", "heuristic")

    summary = buildSummary()

    assert summary.dataset.case_count == 36 and summary.dataset.candidate_count == 0
    assert summary.latest_llm is None
    latest = summary.latest_heuristic
    assert latest.failures and all(f.expected != f.predicted and f.claim and f.notes for f in latest.failures)
    assert len(latest.failures) == latest.case_count - sum(score.correct for score in latest.labels)


# LLM verifier: same quote rule as the pipeline's citation audit


def verdictDraft(verdict: str, ref: int | None = None, quote: str | None = None) -> dict:
    return {"verdict": verdict, "evidence_ref": ref, "evidence_quote": quote, "reasoning": "because"}


def testVerifierKeepsSupportedVerdictWithVerbatimQuote(fakeOpenAI):
    fakeOpenAI.script("ClaimVerdictDraft", verdictDraft("supported", 1, "DevOps Market Size Worth $12.85 Billion by 2025"))

    result = verifyClaim("The DevOps market is worth over $10B.", [DEVOPS])

    assert (result.verdict, result.downgraded_from) == ("supported", None)
    assert result.citation.source_url == DEVOPS.source_url
    assert result.model == "gpt-4o-mini"


@pytest.mark.parametrize(
    "draft",
    [
        verdictDraft("contradicted"),
        verdictDraft("contradicted", 1, "The DevOps market is shrinking fast"),
        verdictDraft("supported", 2, "DevOps Market Size Worth $12.85 Billion by 2025"),
    ],
    ids=["no-quote", "fabricated-quote", "bad-ref"],
)
def testVerifierDowngradesVerdictWithoutAGroundedQuote(fakeOpenAI, draft):
    fakeOpenAI.script("ClaimVerdictDraft", draft)

    result = verifyClaim("The DevOps market is worth under $1B.", [DEVOPS])

    assert (result.verdict, result.downgraded_from, result.citation) == ("unsupported", draft["verdict"], None)


def testVerifierPromptNumbersEvidenceAndStatesTheBoundary(fakeOpenAI):
    fakeOpenAI.script("ClaimVerdictDraft", verdictDraft("unsupported"))

    verifyClaim("Claim text.", [DEVOPS])

    system, human = (m["content"] for m in fakeOpenAI.callsFor("ClaimVerdictDraft")[0]["messages"])
    assert 'absence of evidence is never "contradicted"' in system
    assert f"[E1] Source: {DEVOPS.source_url}" in human
