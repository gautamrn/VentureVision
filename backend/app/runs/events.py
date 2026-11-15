def serializeNodeOutput(nodeName: str, nodeState: dict) -> dict:
    if nodeName == "planner":
        queries = nodeState.get("research_plan", [])
        return {"queries": queries, "queryCount": len(queries)}

    if nodeName == "scout":
        evidence = nodeState.get("raw_evidence", [])
        searches = nodeState.get("search_calls", [])
        return {
            "evidenceCount": len(evidence),
            "searches": len(searches),
            "failedSearches": sum(1 for s in searches if s.error),
        }

    if nodeName == "critic":
        # At the iteration cap the critic skips its model call, so there is no new coverage score.
        capReached = bool(nodeState.get("is_validated")) and "coverage_score" not in nodeState
        return {
            "iteration": nodeState.get("analysis_iteration", 1),
            "isValidated": nodeState.get("is_validated", False),
            "coverageScore": nodeState.get("coverage_score"),
            "feedback": nodeState.get("critique_feedback", ""),
            "budgetExitReason": nodeState.get("budget_exit_reason"),
            "iterationCapReached": capReached,
        }

    if nodeName == "writer":
        return {"memoReady": nodeState.get("final_memo") is not None}

    if nodeName == "citation_audit":
        memo = nodeState.get("final_memo")
        if memo is not None and hasattr(memo, "model_dump"):
            return {"memo": memo.model_dump(mode="json")}
        return {"memo": None}

    return {}
