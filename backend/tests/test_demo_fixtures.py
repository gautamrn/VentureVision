import json
from pathlib import Path

import pytest

from app.schemas.models import MemoOutput
from scripts.demoPitches import DEMO_PITCHES

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "frontend" / "src" / "data" / "demo"


@pytest.mark.parametrize("sample", DEMO_PITCHES, ids=[s["id"] for s in DEMO_PITCHES])
def testDemoFixtureMatchesPitchAndCurrentMemoSchema(sample):
    fixture = json.loads((FIXTURE_DIR / f"{sample['id']}.json").read_text(encoding="utf-8"))

    assert fixture["pitch"] == sample["pitch"], "pitch text changed; re-run scripts.recordDemoRuns"
    assert [e["event"] for e in fixture["events"]][-2:] == ["writer", "citation_audit"]
    assert fixture["events"][0]["event"] == "planner"

    memo = MemoOutput.model_validate(fixture["events"][-1]["data"]["memo"])
    assert memo.groundedness is not None
    assert memo.telemetry is not None, "fixture predates run instrumentation; re-run scripts.recordDemoRuns"
    assert any(e["event"] == "evidence" for e in fixture["events"])
