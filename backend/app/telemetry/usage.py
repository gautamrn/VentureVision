from typing import Any

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.schemas.models import LlmCall, SearchCall
from app.telemetry.collector import currentCollector
from app.telemetry.pricing import llmCostUsd, searchCostUsd, searchCredits


class ModelOutputError(ValueError):
    """The model answered, but its output did not parse into the requested schema."""


def structuredOutput(chat: ChatOpenAI, schema: type[BaseModel]) -> Runnable:
    # include_raw keeps the AIMessage, which carries the token usage the parsed object drops.
    return chat.with_structured_output(schema, include_raw=True)


def invokeStructured(runnable: Runnable, messages: list) -> tuple[Any, LlmCall]:
    collector = currentCollector()
    output = runnable.invoke(messages)
    raw = output["raw"]
    usage = raw.usage_metadata or {}
    modelName = raw.response_metadata.get("model_name", "")
    promptTokens = usage.get("input_tokens", 0)
    completionTokens = usage.get("output_tokens", 0)
    call = LlmCall(
        node=collector.node,
        model=modelName,
        prompt_tokens=promptTokens,
        completion_tokens=completionTokens,
        cost_usd=llmCostUsd(modelName, promptTokens, completionTokens),
    )
    collector.llmCalls.append(call)

    if output.get("parsing_error") is not None or output.get("parsed") is None:
        raise ModelOutputError(f"{collector.node} output did not match its schema: {output.get('parsing_error')}")
    return output["parsed"], call


def recordSearch(query: str, resultCount: int, error: str | None = None) -> SearchCall:
    collector = currentCollector()
    billed = error is None
    call = SearchCall(
        node=collector.node,
        query=query,
        result_count=resultCount,
        credits=searchCredits() if billed else 0,
        cost_usd=searchCostUsd() if billed else 0.0,
        error=error,
    )
    collector.searchCalls.append(call)
    return call
