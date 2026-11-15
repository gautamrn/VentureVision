from app.middleware.rateLimiter import MAX_REQUESTS
from app.schemas.models import RunResponse
from tests.fakes import SAMPLE_PITCH, critique, memoSynthesis, researchPlan


def scriptHappyPath(fakeOpenAI) -> None:
    fakeOpenAI.script("ResearchPlan", researchPlan(["dog walking app competitors"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis(pitchScore=71))


def testHealthReturnsOk(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def testResponsesCarrySecurityHeaders(client):
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def testAnalyzeReturnsCompletedMemo(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI)

    response = client.post("/analyze", json={"pitch": SAMPLE_PITCH})

    assert response.status_code == 200
    body = RunResponse.model_validate(response.json())
    assert body.status == "complete"
    assert body.iterations == 1
    assert body.memo.pitch_score == 71
    assert [str(u) for u in body.memo.citation_links] == ["https://example.com/dog-walking-app-competitors"]
    assert body.memo.groundedness is not None


def testAnalyzePassesModeThroughToAgents(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI)

    response = client.post("/analyze", json={"pitch": SAMPLE_PITCH, "mode": "pitch_lab"})

    assert response.status_code == 200
    writerSystemPrompt = fakeOpenAI.callsFor("MemoSynthesis")[0]["messages"][0]["content"]
    assert writerSystemPrompt.startswith("You are a pitch coach.")


def testAnalyzeRejectsPitchShorterThanFortyCharacters(client, fakeOpenAI):
    response = client.post("/analyze", json={"pitch": "Too short."})

    assert response.status_code == 422
    assert fakeOpenAI.calls == []


def testAnalyzeRejectsUnknownMode(client, fakeOpenAI):
    response = client.post("/analyze", json={"pitch": SAMPLE_PITCH, "mode": "creative"})

    assert response.status_code == 422
    assert fakeOpenAI.calls == []


def testAnalyzeReturns502WhenWriterCannotProduceMemo(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI)
    fakeOpenAI.script("MemoSynthesis", "not json at all")

    response = client.post("/analyze", json={"pitch": SAMPLE_PITCH})

    assert response.status_code == 502
    assert response.json() == {"detail": "Analysis failed. Please try again."}


def testAnalyzeRateLimitsPerClient(client, fakeOpenAI, fakeTavily):
    scriptHappyPath(fakeOpenAI)

    for _ in range(MAX_REQUESTS):
        assert client.post("/analyze", json={"pitch": SAMPLE_PITCH}).status_code == 200

    response = client.post("/analyze", json={"pitch": SAMPLE_PITCH})

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def testAdminMetricsRequiresAdminKey(client):
    assert client.get("/admin/metrics").status_code == 403
    assert client.get("/admin/metrics", headers={"X-Admin-Key": "wrong"}).status_code == 403
    assert client.get("/admin/metrics", headers={"X-Admin-Key": "test-admin-key"}).status_code == 200
