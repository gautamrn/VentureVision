import hashlib
import os
from collections import Counter
from pathlib import Path

from app.schemas.evals import DatasetManifest, GoldenCase

REPO_DIR = Path(__file__).resolve().parents[3]


def evalsDir() -> Path:
    return Path(os.getenv("EVALS_DIR") or REPO_DIR / "evals")


def datasetPath() -> Path:
    return evalsDir() / "golden_dataset.jsonl"


def candidatesPath() -> Path:
    return evalsDir() / "candidates.jsonl"


def loadCases(path: Path) -> list[GoldenCase]:
    if not path.exists():
        return []
    cases = [
        GoldenCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    duplicates = [caseId for caseId, count in Counter(c.id for c in cases).items() if count > 1]
    if duplicates:
        raise ValueError(f"{path.name} has duplicate case ids: {', '.join(sorted(duplicates))}")
    return cases


def loadDataset() -> list[GoldenCase]:
    return loadCases(datasetPath())


def loadManifest() -> DatasetManifest:
    return DatasetManifest.model_validate_json((evalsDir() / "dataset.json").read_text(encoding="utf-8"))


def datasetSha256() -> str:
    return hashlib.sha256(datasetPath().read_bytes()).hexdigest()[:16]
