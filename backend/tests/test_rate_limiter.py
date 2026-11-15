import pytest
from starlette.requests import Request

from app.middleware import rateLimiter
from app.middleware.rateLimiter import MAX_REQUESTS, clientIpFor
from tests.fakes import SAMPLE_PITCH, critique, memoSynthesis, researchPlan


def requestFrom(peer: str, forwardedFor: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwardedFor.encode())] if forwardedFor is not None else []
    return Request({"type": "http", "client": (peer, 1234), "headers": headers})


def testWithoutTrustedProxiesUsesSocketPeerAndIgnoresHeader(monkeypatch):
    monkeypatch.setattr(rateLimiter, "TRUSTED_PROXY_HOPS", 0)

    assert clientIpFor(requestFrom("10.0.0.1", "203.0.113.9")) == "10.0.0.1"


def testOneTrustedProxyUsesRightmostForwardedEntry(monkeypatch):
    monkeypatch.setattr(rateLimiter, "TRUSTED_PROXY_HOPS", 1)

    assert clientIpFor(requestFrom("10.0.0.1", "203.0.113.9")) == "203.0.113.9"


def testSpoofedLeftmostEntriesAreIgnored(monkeypatch):
    monkeypatch.setattr(rateLimiter, "TRUSTED_PROXY_HOPS", 1)

    assert clientIpFor(requestFrom("10.0.0.1", "1.2.3.4, 5.6.7.8, 203.0.113.9")) == "203.0.113.9"


def testTwoTrustedProxiesSkipTheInnerProxy(monkeypatch):
    monkeypatch.setattr(rateLimiter, "TRUSTED_PROXY_HOPS", 2)

    assert clientIpFor(requestFrom("10.0.0.1", "1.2.3.4, 203.0.113.9, 172.16.0.5")) == "203.0.113.9"


@pytest.mark.parametrize("header", [None, "", "203.0.113.9"])
def testTooFewForwardedEntriesFallsBackToPeer(monkeypatch, header):
    monkeypatch.setattr(rateLimiter, "TRUSTED_PROXY_HOPS", 2)

    assert clientIpFor(requestFrom("10.0.0.1", header)) == "10.0.0.1"


def testVisitorsBehindSameProxyGetSeparateLimits(monkeypatch, client, fakeOpenAI, fakeTavily):
    monkeypatch.setattr(rateLimiter, "TRUSTED_PROXY_HOPS", 1)
    fakeOpenAI.script("ResearchPlan", researchPlan(["q"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script("MemoSynthesis", memoSynthesis())

    def analyzeAs(ip: str) -> int:
        return client.post("/analyze", json={"pitch": SAMPLE_PITCH}, headers={"X-Forwarded-For": ip}).status_code

    assert [analyzeAs("203.0.113.1") for _ in range(MAX_REQUESTS)] == [200] * MAX_REQUESTS
    assert analyzeAs("203.0.113.1") == 429
    assert analyzeAs("203.0.113.2") == 200
