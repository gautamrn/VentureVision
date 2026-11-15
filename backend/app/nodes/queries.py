MAX_FOLLOW_UP_QUERIES = 4


def parseFeedbackQueries(feedback: str) -> list[str]:
    """The critic's feedback is a comma-separated list of follow-up searches for the scout."""
    queries = [q.strip() for q in feedback.split(",") if q.strip()]
    if not queries and feedback.strip():
        queries = [feedback.strip()]
    return queries[:MAX_FOLLOW_UP_QUERIES]
