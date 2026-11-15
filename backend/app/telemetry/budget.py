import os

from app.schemas.models import LlmCall, SearchCall

DEFAULT_RUN_BUDGET_USD = 0.25


def configuredBudgetUsd() -> float:
    return float(os.getenv("RUN_BUDGET_USD", DEFAULT_RUN_BUDGET_USD))


def spentUsd(llmCalls: list[LlmCall], searchCalls: list[SearchCall]) -> float:
    return sum(c.cost_usd for c in llmCalls) + sum(c.cost_usd for c in searchCalls)


def budgetExitReason(
    *,
    spentSoFarUsd: float,
    nextRoundUsd: float,
    writerReserveUsd: float,
    budgetUsd: float,
    completedRounds: int,
) -> str | None:
    """Reason to stop the research loop, or None if another round still fits the budget.

    The projection is built from measured numbers only: what this run has spent, the next
    round's search count at the configured search price plus this round's measured critic
    call, and the writer's max_tokens at the configured output price.
    """
    projectedUsd = spentSoFarUsd + nextRoundUsd + writerReserveUsd
    if projectedUsd <= budgetUsd:
        return None
    rounds = "round" if completedRounds == 1 else "rounds"
    return (
        f"Research stopped after {completedRounds} {rounds} to stay within the ${budgetUsd:.2f} per-run budget: "
        f"${spentSoFarUsd:.4f} spent, and another round (${nextRoundUsd:.4f}) plus the memo "
        f"(up to ${writerReserveUsd:.4f}) was projected to reach ${projectedUsd:.4f}."
    )
