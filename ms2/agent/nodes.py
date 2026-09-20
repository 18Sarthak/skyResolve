"""
LangGraph node functions for the SkyResolve agent pipeline.

Each node takes the current AgentState and returns a dict of state updates.
Deterministic nodes have zero LLM calls and are independently testable.
LLM nodes delegate to agent.intent and agent.response.
"""
from __future__ import annotations

import logging

from data.bookings import get_affected_booking, get_bookings_by_pnr
from data.customers import get_customer_by_pnr
from data.policy_rules import (
    check_cancellation_entitlements,
    check_delay_entitlements,
    check_fare_difference_rule,
    check_loyalty_tier_extras,
    check_refund_rules,
    evaluate_escalation_triggers,
)

logger = logging.getLogger(__name__)

_ESCALATION_MESSAGE = (
    "I sincerely apologise for the difficulty you are experiencing. "
    "Your case has been flagged for immediate attention by one of our senior specialists, "
    "who will reach out to you directly within the next 2 hours. "
    "We take every concern seriously and are committed to resolving this for you."
)


# ---------------------------------------------------------------------------
# Node 1 — extract_intent (LLM)
# ---------------------------------------------------------------------------

def extract_intent_node(state: dict) -> dict:
    """
    Call the LLM to parse the customer's free-text message into structured JSON.
    Populates state with parsed_intent and accumulates token usage.
    """
    from agent.intent import extract_intent_llm

    customer = state["customer"]
    affected_booking = state.get("affected_booking")

    flight_context = "No disrupted flight found for this PNR."
    if affected_booking:
        flight_context = (
            f"Flight {affected_booking.flight_number} "
            f"{affected_booking.origin}→{affected_booking.destination} "
            f"scheduled {affected_booking.scheduled_dt.strftime('%d %b %Y %H:%M')} | "
            f"Status: {affected_booking.status}"
        )
        if affected_booking.delay_hours:
            flight_context += f" | Delay: {affected_booking.delay_hours}h"

    intent, prompt_tok, comp_tok = extract_intent_llm(
        customer_message=state["customer_message"],
        customer_name=customer.name,
        flight_context=flight_context,
        client=state["openai_client"],
    )

    return {
        "parsed_intent": intent,
        "total_prompt_tokens": state.get("total_prompt_tokens", 0) + prompt_tok,
        "total_completion_tokens": state.get("total_completion_tokens", 0) + comp_tok,
    }


# ---------------------------------------------------------------------------
# Node 2 — lookup_booking (deterministic)
# ---------------------------------------------------------------------------

def lookup_booking_node(state: dict) -> dict:
    """
    Fetch the customer record and their affected booking from the data layer.
    Sets error state if the PNR is not found.
    """
    pnr = state["pnr"]
    customer = get_customer_by_pnr(pnr)
    if not customer:
        return {
            "error": f"No customer found for PNR {pnr}.",
            "customer": None,
            "affected_booking": None,
            "all_bookings": [],
        }

    affected = get_affected_booking(pnr)
    all_bookings = get_bookings_by_pnr(pnr)

    return {
        "customer": customer,
        "affected_booking": affected,
        "all_bookings": all_bookings,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Node 3 — apply_policy (deterministic — NO LLM)
# ---------------------------------------------------------------------------

def apply_policy_node(state: dict) -> dict:
    """
    Apply all relevant policy rules deterministically.

    Reads the booking status, delay duration, and parsed intent.
    Returns a structured policy_decision dict with:
      - allowed_actions
      - denied_actions (each with reason)
      - escalation_required (bool)
      - escalation_reason (str | None)
    """
    booking = state.get("affected_booking")
    customer = state["customer"]
    intent = state.get("parsed_intent", {})

    allowed_actions: list[str] = []
    denied_actions: list[dict] = []
    decision_details: dict = {}

    # --- No affected booking ---
    if not booking:
        policy_decision = {
            "allowed_actions": [],
            "denied_actions": [],
            "details": {"note": "No disrupted flight found for this PNR."},
            "escalation_required": False,
            "escalation_reason": None,
        }
        return {"policy_decision": policy_decision, "escalation_required": False}

    # --- Cancellation entitlements ---
    if booking.status == "Cancelled":
        cancel_result = check_cancellation_entitlements(booking.disruption_cause)
        allowed_actions.extend(cancel_result["allowed_actions"])
        denied_actions.extend(
            {"action": a, "reason": cancel_result["details"].get("reason", "")}
            for a in cancel_result["denied_actions"]
        )
        decision_details.update(cancel_result["details"])

    # --- Delay entitlements ---
    if booking.status == "Delayed":
        delay_result = check_delay_entitlements(booking.delay_hours)
        allowed_actions.extend(delay_result["allowed_actions"])
        for denied_action in delay_result["denied_actions"]:
            reason = delay_result["details"].get(
                "hotel_denial_reason", "Not applicable under current delay duration."
            )
            denied_actions.append({"action": denied_action, "reason": reason})
        decision_details.update(delay_result["details"])

    # --- Loyalty tier extras ---
    tier_result = check_loyalty_tier_extras(customer.tier)
    allowed_actions.extend(tier_result["allowed_actions"])
    decision_details["loyalty"] = tier_result["details"]

    # --- Refund rules (if refund was mentioned) ---
    requested_action = intent.get("requested_action", "")
    alternate_refund = bool(intent.get("alternate_refund_method_requested", False))
    if requested_action == "refund" or "full_refund" in allowed_actions:
        refund_result = check_refund_rules(not alternate_refund)
        if refund_result["denied_actions"]:
            for da in refund_result["denied_actions"]:
                denied_actions.append({"action": da, "reason": refund_result["details"]["reason"]})
        decision_details["refund"] = refund_result["details"]

    # --- Fare difference rule (if voluntary upgrade requested) ---
    fare_diff_exceeds_limit = False
    fare_upgrade = bool(intent.get("fare_upgrade_requested", False))
    estimated_fare_diff = intent.get("estimated_fare_diff_inr") or 0
    if fare_upgrade and estimated_fare_diff:
        fare_result = check_fare_difference_rule(float(estimated_fare_diff))
        if fare_result["denied_actions"]:
            fare_diff_exceeds_limit = True
            for da in fare_result["denied_actions"]:
                denied_actions.append({"action": da, "reason": fare_result["details"]["reason"]})
        else:
            allowed_actions.extend(fare_result["allowed_actions"])
        decision_details["fare_difference"] = fare_result["details"]

    # --- Escalation evaluation ---
    compensation_beyond_policy = bool(intent.get("compensation_beyond_policy", False))
    escalation = evaluate_escalation_triggers(
        mentions_legal_threat=bool(intent.get("mentions_legal_threat", False)),
        compensation_beyond_policy=compensation_beyond_policy,
        fare_diff_waiver_exceeds_limit=fare_diff_exceeds_limit,
        non_airline_exception_requested=(
            booking.disruption_cause != "airline"
            and requested_action in ("refund", "rebooking", "compensation")
        ),
        alternate_refund_method_requested=alternate_refund,
    )

    policy_decision = {
        "allowed_actions": list(dict.fromkeys(allowed_actions)),  # deduplicate, preserve order
        "denied_actions": denied_actions,
        "details": decision_details,
        "escalation_required": escalation["escalation_required"],
        "escalation_reason": escalation["escalation_reason"],
        "immediate_escalation": escalation.get("immediate", False),
        "booking_status": booking.status,
        "delay_hours": booking.delay_hours,
        "flight_number": booking.flight_number,
        "route": f"{booking.origin}→{booking.destination}",
    }

    return {
        "policy_decision": policy_decision,
        "escalation_required": escalation["escalation_required"],
    }


# ---------------------------------------------------------------------------
# Node 4 — draft_response (LLM)
# ---------------------------------------------------------------------------

def draft_response_node(state: dict) -> dict:
    """
    Call the LLM to draft an empathetic customer-facing response.
    The LLM receives the policy decision as ground truth and may not alter it.
    """
    from agent.response import draft_response_llm

    response_text, prompt_tok, comp_tok = draft_response_llm(
        customer_name=state["customer"].name,
        customer_message=state["customer_message"],
        policy_decision=state["policy_decision"],
        client=state["openai_client"],
    )

    return {
        "agent_response": response_text,
        "total_prompt_tokens": state.get("total_prompt_tokens", 0) + prompt_tok,
        "total_completion_tokens": state.get("total_completion_tokens", 0) + comp_tok,
    }


# ---------------------------------------------------------------------------
# Node 5 — log_turn (deterministic)
# ---------------------------------------------------------------------------

def log_turn_node(state: dict) -> dict:
    """
    Persist the full conversation turn to the SQLite audit trail.
    Always the final node in every execution path.
    """
    from db.audit import log_turn

    policy_decision = state.get("policy_decision", {})
    allowed = policy_decision.get("allowed_actions", [])

    log_turn(
        pnr=state["pnr"],
        customer_message=state["customer_message"],
        parsed_intent=state.get("parsed_intent"),
        policy_decision=policy_decision,
        agent_response=state.get("agent_response"),
        actions_taken=allowed,
        escalated=state.get("escalation_required", False),
        escalation_reason=policy_decision.get("escalation_reason"),
        prompt_tokens=state.get("total_prompt_tokens", 0),
        completion_tokens=state.get("total_completion_tokens", 0),
    )

    logger.info(
        "Turn logged | PNR=%s escalated=%s actions=%s",
        state["pnr"],
        state.get("escalation_required"),
        allowed,
    )

    return {}


# ---------------------------------------------------------------------------
# human_handoff node
# ---------------------------------------------------------------------------

def human_handoff_node(state: dict) -> dict:
    """
    Produce a fixed escalation message without any LLM call.
    Always routes to log_turn_node afterward.
    """
    policy_decision = state.get("policy_decision", {})
    reason = policy_decision.get("escalation_reason", "Escalation triggered.")

    logger.info("Human handoff triggered | PNR=%s reason=%s", state["pnr"], reason)

    return {
        "agent_response": _ESCALATION_MESSAGE,
        "escalation_required": True,
    }
