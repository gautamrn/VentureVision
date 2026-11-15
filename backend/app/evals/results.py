from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.evals.dataset import evalsDir, loadCases, candidatesPath, loadDataset, loadManifest
from app.schemas.evals import (
    EVAL_LABELS,
    DatasetSummary,
    EvalBaseline,
    EvalMode,
    EvalRun,
    EvalSummary,
    FailedCase,
    LatestRun,
    RunSummary,
)


def historyDir() -> Path:
    return evalsDir() / "results" / "history"


def baselinePath() -> Path:
    return evalsDir() / "results" / "baseline_heuristic.json"


def saveRun(run: EvalRun) -> Path:
    historyDir().mkdir(parents=True, exist_ok=True)
    path = historyDir() / f"{run.run_id}.json"
    path.write_text(run.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def loadRuns() -> list[EvalRun]:
    if not historyDir().exists():
        return []
    runs = [EvalRun.model_validate_json(p.read_text(encoding="utf-8")) for p in historyDir().glob("*.json")]
    return sorted(runs, key=lambda r: r.started_at)


def loadBaseline() -> EvalBaseline | None:
    if not baselinePath().exists():
        return None
    return EvalBaseline.model_validate_json(baselinePath().read_text(encoding="utf-8"))


def saveBaseline(baseline: EvalBaseline) -> Path:
    baselinePath().parent.mkdir(parents=True, exist_ok=True)
    baselinePath().write_text(baseline.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return baselinePath()


def summaryOf(run: EvalRun) -> RunSummary:
    return RunSummary.model_validate(run.model_dump(include=set(RunSummary.model_fields)))


def latestRunWithFailures(runs: list[EvalRun], mode: EvalMode) -> LatestRun | None:
    ofMode = [r for r in runs if r.mode == mode]
    if not ofMode:
        return None
    run = ofMode[-1]
    casesById = {c.id: c for c in loadDataset()}
    failures = [
        FailedCase(
            id=outcome.id,
            origin=case.origin,
            claim=case.claim,
            pitch_excerpt=case.pitch_excerpt,
            evidence=case.evidence,
            expected=outcome.expected,
            predicted=outcome.predicted,
            detail=outcome.detail,
            downgraded_from=outcome.downgraded_from,
            notes=case.notes,
        )
        for outcome in run.cases
        if not outcome.correct and (case := casesById.get(outcome.id)) is not None
    ]
    return LatestRun(**summaryOf(run).model_dump(), failures=failures)


def buildSummary() -> EvalSummary:
    manifest = loadManifest()
    cases = loadDataset()
    runs = loadRuns()
    labelCounts = Counter(c.label for c in cases)
    return EvalSummary(
        generated_at=datetime.now(timezone.utc),
        dataset=DatasetSummary(
            name=manifest.name,
            version=manifest.version,
            updated=manifest.updated,
            case_count=len(cases),
            label_counts={label: labelCounts.get(label, 0) for label in EVAL_LABELS},
            origin_counts=dict(Counter(c.origin for c in cases)),
            candidate_count=len(loadCases(candidatesPath())),
        ),
        baseline=loadBaseline(),
        latest_heuristic=latestRunWithFailures(runs, "heuristic"),
        latest_llm=latestRunWithFailures(runs, "llm"),
        history=[summaryOf(r) for r in runs],
    )
