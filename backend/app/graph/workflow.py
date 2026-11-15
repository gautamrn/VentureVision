from langgraph.graph import StateGraph, START, END

from app.graph.instrumentation import instrumentNode
from app.graph.state import AgentState
from app.nodes.planner import planner_node
from app.nodes.scout import scout_node
from app.nodes.critic import citation_audit_node, critic_node
from app.nodes.writer import writer_node


def routeAfterCritic(state: AgentState) -> str:
    if state.get("is_validated", False):
        return "writer"
    return "scout"


def buildGraph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", instrumentNode("planner", planner_node))
    graph.add_node("scout", instrumentNode("scout", scout_node))
    graph.add_node("critic", instrumentNode("critic", critic_node))
    graph.add_node("writer", instrumentNode("writer", writer_node))
    graph.add_node("citation_audit", instrumentNode("citation_audit", citation_audit_node))

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "scout")
    graph.add_edge("scout", "critic")

    graph.add_conditional_edges(
        "critic",
        routeAfterCritic,
        {
            "scout": "scout",
            "writer": "writer",
        },
    )

    graph.add_edge("writer", "citation_audit")
    graph.add_edge("citation_audit", END)

    return graph.compile()


ventureGraph = buildGraph()
