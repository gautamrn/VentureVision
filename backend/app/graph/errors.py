import json
from typing import Literal

import openai
from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError

from app.schemas.models import LlmCall, SearchCall
from app.telemetry.usage import ModelOutputError

FailureKind = Literal["upstream_api", "bad_model_output", "internal"]


class SearchUnavailable(RuntimeError):
    """Every web search in a scout round failed, so there is no evidence to judge — not an empty result."""


class RunCancelled(Exception):
    def __init__(self, node: str, started: bool = True) -> None:
        super().__init__(f"run cancelled before {node} {'finished' if started else 'started'}")
        self.node = node
        self.started = started
        self.llmCalls: list[LlmCall] = []
        self.searchCalls: list[SearchCall] = []
        self.durationMs = 0


class NodeFailure(Exception):
    """A node raised; carries what the attempt already spent so the run's cost stays complete."""

    def __init__(
        self,
        node: str,
        cause: BaseException,
        llmCalls: list[LlmCall],
        searchCalls: list[SearchCall],
        durationMs: int,
    ) -> None:
        self.node = node
        self.cause = cause
        self.kind, self.message = describeFailure(node, cause)
        self.llmCalls = llmCalls
        self.searchCalls = searchCalls
        self.durationMs = durationMs
        super().__init__(self.message)


def describeFailure(node: str, exc: BaseException) -> tuple[FailureKind, str]:
    if isinstance(exc, SearchUnavailable):
        return "upstream_api", f"Web search failed: {exc}"
    if isinstance(exc, openai.APIStatusError):
        return "upstream_api", f"OpenAI returned HTTP {exc.status_code} to the {node} agent."
    if isinstance(exc, openai.APIConnectionError):
        return "upstream_api", f"The {node} agent could not reach OpenAI ({type(exc).__name__})."
    if isinstance(
        exc,
        (ModelOutputError, ValidationError, json.JSONDecodeError, OutputParserException, openai.LengthFinishReasonError),
    ):
        return "bad_model_output", f"The {node} agent's model response did not match the expected schema."
    return "internal", f"The {node} agent failed with an internal error ({type(exc).__name__})."
