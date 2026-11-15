import secrets
import time
from collections.abc import Callable
from datetime import datetime, timezone

from app.schemas.evals import (
    EVAL_LABELS,
    CaseOutcome,
    EvalBaseline,
    EvalMode,
    EvalRun,
    GoldenCase,
    LabelScore,
    Prediction,
)

Predictor = Callable[[GoldenCase], tuple[Prediction, float]]

MAX_ACCURACY_DROP_POINTS = 3.0


def heuristicPredictor() -> Predictor:
    from app.verification.heuristic import classifyClaim

    return lambda case: (classifyClaim(case.claim, case.evidence), 0.0)


def llmPredictor() -> Predictor:
    # Imported lazily: building the OpenAI client needs OPENAI_API_KEY, which heuristic runs don't.
    from app.verification.claimVerifier import verifyClaim

    def predict(case: GoldenCase) -> tuple[Prediction, float]:
        result = verifyClaim(case.claim, case.evidence)
        return Prediction(label=result.verdict, detail=result.reasoning, downgraded_from=result.downgraded_from), result.cost_usd

    return predict


def percent(correct: int, total: int) -> float:
    return round(100 * correct / total, 1) if total else 0.0


def scoreLabels(outcomes: list[CaseOutcome]) -> list[LabelScore]:
    scores = []
    for label in EVAL_LABELS:
        ofLabel = [o for o in outcomes if o.expected == label]
        correct = sum(o.correct for o in ofLabel)
        scores.append(LabelScore(label=label, total=len(ofLabel), correct=correct, accuracy=percent(correct, len(ofLabel))))
    return scores


def runEvals(
    cases: list[GoldenCase],
    mode: EvalMode,
    predictor: Predictor,
    *,
    model: str | None,
    datasetVersion: int,
    datasetSha: str,
    onCase: Callable[[CaseOutcome], None] = lambda _: None,
) -> EvalRun:
    startedAt = datetime.now(timezone.utc)
    start = time.perf_counter()
    outcomes: list[CaseOutcome] = []
    costUsd = 0.0
    for case in cases:
        prediction, cost = predictor(case)
        costUsd += cost
        outcome = CaseOutcome(
            id=case.id,
            expected=case.label,
            predicted=prediction.label,
            correct=prediction.label == case.label,
            detail=prediction.detail,
            downgraded_from=prediction.downgraded_from,
        )
        outcomes.append(outcome)
        onCase(outcome)

    correct = sum(o.correct for o in outcomes)
    return EvalRun(
        run_id=f"{startedAt:%Y-%m-%dT%H-%M-%SZ}_{mode}_{secrets.token_hex(3)}",
        mode=mode,
        model=model,
        dataset_version=datasetVersion,
        dataset_sha256=datasetSha,
        case_count=len(outcomes),
        started_at=startedAt,
        duration_ms=round((time.perf_counter() - start) * 1000),
        cost_usd=round(costUsd, 6),
        overall_accuracy=percent(correct, len(outcomes)),
        labels=scoreLabels(outcomes),
        cases=outcomes,
    )


def baselineOf(run: EvalRun) -> EvalBaseline:
    return EvalBaseline(
        run_id=run.run_id,
        mode=run.mode,
        dataset_version=run.dataset_version,
        case_count=run.case_count,
        overall_accuracy=run.overall_accuracy,
        labels=run.labels,
    )


def regressionMessage(run: EvalRun, baseline: EvalBaseline) -> str | None:
    """A failure message if overall accuracy fell more than MAX_ACCURACY_DROP_POINTS below the baseline."""
    drop = round(baseline.overall_accuracy - run.overall_accuracy, 1)
    if drop <= MAX_ACCURACY_DROP_POINTS:
        return None
    return (
        f"{run.mode} accuracy {run.overall_accuracy}% is {drop} points below the stored baseline "
        f"{baseline.overall_accuracy}% (run {baseline.run_id}); the allowed drop is {MAX_ACCURACY_DROP_POINTS} points."
    )
