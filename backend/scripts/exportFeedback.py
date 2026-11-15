"""Appends reviewed (accepted) reader feedback to evals/candidates.jsonl as golden-format candidate cases.

Never touches evals/golden_dataset.jsonl: promote a candidate by moving its line there yourself.
Usage, from backend/:  .venv\\Scripts\\python.exe -m scripts.exportFeedback
Reads FEEDBACK_DB_PATH (default backend/data/feedback.sqlite3) and EVALS_DIR (default <repo>/evals).
"""

import sys

from app.evals.dataset import candidatesPath, datasetPath
from app.feedback.export import exportAccepted
from app.feedback.store import getFeedbackStore


def main() -> int:
    report = exportAccepted(getFeedbackStore(), candidatesPath(), datasetPath())
    for caseId in report.appended:
        print(f"appended {caseId}")
    for feedbackId, reason in report.skipped:
        print(f"skipped feedback #{feedbackId}: {reason}")
    print(f"{len(report.appended)} candidate(s) appended to {candidatesPath()}; golden dataset unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
