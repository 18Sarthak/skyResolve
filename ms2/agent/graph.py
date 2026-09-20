"""
LangGraph state machine for the SkyResolve agent.

Graph structure:
  lookup_booking
       ↓
  extract_intent
       ↓
  apply_policy ──[escalation_required=True]──→ human_handoff ──→ log_turn
       ↓                                                              ↑
  draft_response ──────────────────────────────────────────────→ log_turn
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from openai import OpenAI
from typing_extensions import TypedDict

from agent.nodes import (
    apply_policy_node,
    draft_response_node,
    extract_intent_node,
    human_handoff_node,
    log_turn_node,
    lookup_booking_node,
)
from data.bookings import Booking
from data.customers import Customer


class AgentState(TypedDict, total=False):
    # Inputs
    pnr: str
    customer_message: str
    openai_client: Any  # OpenAI client instance

    # Populated by lookup_booking_node
    customer: Customer | None
    affected_booking: Booking | None
    all_bookings: list[Booking]
    error: str | None

    # Populated by extract_intent_node
    parsed_intent: dict | None

    # Populated by apply_policy_node
    policy_decision: dict | None
    escalation_required: bool

    # Populated by draft_response_node or human_handoff_node
    agent_response: str | None

    # Token accounting (accumulated across LLM calls)
    total_prompt_tokens: int
    total_completion_tokens: int


def _should_escalate(state: AgentState) -> str:
    """Conditional edge: route to human_handoff if escalation is required."""
    if state.get("escalation_required", False):
        return "human_handoff"
    return "draft_response"


def build_graph() -> Any:
    """Build and compile the LangGraph state machine."""
    builder = StateGraph(AgentState)

    builder.add_node("lookup_booking", lookup_booking_node)
    builder.add_node("extract_intent", extract_intent_node)
    builder.add_node("apply_policy", apply_policy_node)
    builder.add_node("draft_response", draft_response_node)
    builder.add_node("human_handoff", human_handoff_node)
    builder.add_node("log_turn", log_turn_node)

    builder.set_entry_point("lookup_booking")
    builder.add_edge("lookup_booking", "extract_intent")
    builder.add_edge("extract_intent", "apply_policy")

    builder.add_conditional_edges(
        "apply_policy",
        _should_escalate,
        {
            "draft_response": "draft_response",
            "human_handoff": "human_handoff",
        },
    )

    builder.add_edge("draft_response", "log_turn")
    builder.add_edge("human_handoff", "log_turn")
    builder.add_edge("log_turn", END)

    return builder.compile()


def run_conversation_turn(
    pnr: str,
    customer_message: str,
    openai_client: OpenAI,
) -> AgentState:
    """
    Execute one full conversation turn through the graph.

    Returns the final agent state.
    """
    graph = build_graph()
    initial_state: AgentState = {
        "pnr": pnr.upper(),
        "customer_message": customer_message,
        "openai_client": openai_client,
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
    }
    final_state = graph.invoke(initial_state)
    return final_state
