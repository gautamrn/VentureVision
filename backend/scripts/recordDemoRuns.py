"""Runs the real pipeline once per demo pitch and stores every streamed event as a frontend fixture.

Uses OPENAI_API_KEY and TAVILY_API_KEY from the repo-root .env (costs API credits).
Usage, from backend/:  .venv\\Scripts\\python.exe -m scripts.recordDemoRuns [sampleId ...]
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
FIXTURE_DIR = REPO_DIR / "frontend" / "src" / "data" / "demo"

load_dotenv(REPO_DIR / ".env")

from app.graph.workflow import ventureGraph  # noqa: E402
from app.routers.analyze import buildInitialState, serializeNodeOutput  # noqa: E402
from scripts.demoPitches import DEMO_PITCHES  # noqa: E402

DEMO_MODE = "pitch_lab"


def recordRun(sample: dict) -> dict:
    events = []
    startedAt = time.monotonic()
    for chunk in ventureGraph.stream(buildInitialState(sample["pitch"], DEMO_MODE)):
        nodeName, nodeState = next(iter(chunk.items()))
        events.append(
            {
                "event": nodeName,
                "atMs": int((time.monotonic() - startedAt) * 1000),
                "data": serializeNodeOutput(nodeName, nodeState),
            }
        )
        print(f"  {events[-1]['atMs']:>6} ms  {nodeName}")

    memo = events[-1]["data"].get("memo") if events and events[-1]["event"] == "citation_audit" else None
    if memo is None:
        raise RuntimeError(f"{sample['id']}: pipeline produced no memo; fixture not written")

    return {
        "id": sample["id"],
        "category": sample["category"],
        "title": sample["title"],
        "tagline": sample["tagline"],
        "pitch": sample["pitch"],
        "mode": DEMO_MODE,
        "recordedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "durationMs": events[-1]["atMs"],
        "events": events,
    }


def main(sampleIds: list[str]) -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    samples = [s for s in DEMO_PITCHES if not sampleIds or s["id"] in sampleIds]
    for sample in samples:
        print(f"Recording {sample['id']} ({DEMO_MODE})")
        fixture = recordRun(sample)
        groundedness = fixture["events"][-1]["data"]["memo"]["groundedness"]
        (FIXTURE_DIR / f"{sample['id']}.json").write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
        print(f"  wrote {sample['id']}.json in {fixture['durationMs'] / 1000:.1f}s, groundedness {groundedness}")


if __name__ == "__main__":
    main(sys.argv[1:])
