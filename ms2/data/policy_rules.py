"""
Deterministic airline policy rules.

Every function in this module is a pure Python function:
- No LLM calls, no I/O, no side effects.
- Each can be unit-tested in total isolation.
- All monetary amounts and thresholds are defined here as module-level
  constants so they are a single source of truth.
"""
from __future__ import annotations
from typing import Literal

# ---------------------------------------------------------------------------
# Policy constants — single source of truth for all thresholds/amounts
# ---------------------------------------------------------------------------
MEAL_VOUCHER_AMOUNT_INR = 500
LOUNGE_ACCESS_THRESHOLD_HOURS = 3.0
HOTEL_THRESHOLD_HOURS = 5.0
FARE_DIFF_WAIVER_MAX_INR = 1500


# ---------------------------------------------------------------------------
# Return-type aliases (plain dicts for simplicity; no extra deps)
# ---------------------------------------------------------------------------

# Each function returns a dict with at minimum:
#   allowed_actions: list[str]
#   denied_actions:  list[str]
#   details:         dict  (additional structured data the response drafter needs)


def check_cancellation_entitlements(
    disruption_cause: Literal["airline", "passenger", "none"],
) -> dict:
    """
    Rule 1 — Cancellation Rebooking Rule.

    Airline-caused cancellation → free rebooking within 24h OR full refund,
    customer's choice. Non-airline-caused cancellation is not covered.
    """
    if disruption_cause == "airline":
        return {
            "allowed_actions": ["free_rebooking_within_24h", "full_refund"],
            "denied_actions": [],
            "details": {
                "rebooking_window_hours": 24,
                "refund_method": "original_payment_method",
                "refund_processing_days": 7,
            },
        }
    return {
        "allowed_actions": [],
        "denied_actions": ["free_rebooking", "refund"],
        "details": {"reason": "Disruption was not caused by the airline."},
    }


def check_delay_entitlements(delay_hours: float) -> dict:
    """
    Rule 2 — Delay Compensation Rule.

    <3h  → meal voucher only
    ≥3h  → meal voucher + lounge access
    >5h  → meal voucher + lounge access + hotel for delayed hours only
    """
    allowed: list[str] = []
    details: dict = {"meal_voucher_amount_inr": MEAL_VOUCHER_AMOUNT_INR}

    if delay_hours > 0:
        allowed.append("meal_voucher")

    if delay_hours >= LOUNGE_ACCESS_THRESHOLD_HOURS:
        allowed.append("lounge_access")

    hotel_granted = delay_hours > HOTEL_THRESHOLD_HOURS
    if hotel_granted:
        allowed.append("hotel_for_delayed_hours_only")
        details["hotel_note"] = (
            "Hotel covers only the delayed hours, not a full overnight stay."
        )

    denied: list[str] = []
    if not hotel_granted and delay_hours > 0:
        denied.append("hotel")
        if delay_hours <= HOTEL_THRESHOLD_HOURS:
            details["hotel_denial_reason"] = (
                f"Hotel is only provided for delays exceeding "
                f"{HOTEL_THRESHOLD_HOURS}h. Current delay is {delay_hours}h."
            )

    return {
        "allowed_actions": allowed,
        "denied_actions": denied,
        "details": details,
    }


def check_refund_rules(payment_method_matches_original: bool) -> dict:
    """
    Rule 3 — Refund Processing Rule.

    Full refund within 7 business days to original payment method only.
    Refund to a different payment method requires human approval.
    """
    if payment_method_matches_original:
        return {
            "allowed_actions": ["process_refund"],
            "denied_actions": [],
            "details": {
                "processing_days": 7,
                "method": "original_payment_method",
            },
        }
    return {
        "allowed_actions": [],
        "denied_actions": ["process_refund_to_alternate_method"],
        "details": {
            "reason": (
                "Refunds can only be processed to the original payment method. "
                "A request for a different method requires supervisor approval."
            )
        },
    }


def check_fare_difference_rule(fare_diff_amount_inr: float) -> dict:
    """
    Rule 4 — Fare Difference Rule.

    Voluntary rebooking to a higher fare → customer pays difference.
    Agent may NOT waive fare differences above ₹1,500 without supervisor approval.
    """
    if fare_diff_amount_inr <= FARE_DIFF_WAIVER_MAX_INR:
        return {
            "allowed_actions": ["collect_fare_difference"],
            "denied_actions": [],
            "details": {
                "fare_diff_inr": fare_diff_amount_inr,
                "waiver_possible": fare_diff_amount_inr == 0,
            },
        }
    return {
        "allowed_actions": [],
        "denied_actions": ["waive_fare_difference"],
        "details": {
            "fare_diff_inr": fare_diff_amount_inr,
            "waiver_limit_inr": FARE_DIFF_WAIVER_MAX_INR,
            "reason": (
                f"Fare difference of ₹{fare_diff_amount_inr:.0f} exceeds the "
                f"₹{FARE_DIFF_WAIVER_MAX_INR} waiver authority. "
                "Supervisor approval required."
            ),
        },
    }


def check_loyalty_tier_extras(
    tier: Literal["Silver", "Gold", "Platinum"],
) -> dict:
    """
    Rule 5 — Loyalty Tier Rule.

    Gold/Platinum get priority rebooking queue only.
    No additional monetary compensation beyond standard policy.
    """
    priority_rebooking = tier in ("Gold", "Platinum")
    return {
        "allowed_actions": ["priority_rebooking"] if priority_rebooking else [],
        "denied_actions": [],
        "details": {
            "tier": tier,
            "priority_rebooking": priority_rebooking,
            "extra_compensation": False,
            "note": (
                "Loyalty tier provides priority rebooking access only. "
                "No extra monetary compensation is applicable beyond standard policy."
            ),
        },
    }


def evaluate_escalation_triggers(
    mentions_legal_threat: bool,
    compensation_beyond_policy: bool,
    fare_diff_waiver_exceeds_limit: bool,
    non_airline_exception_requested: bool,
    alternate_refund_method_requested: bool,
) -> dict:
    """
    Evaluate all escalation triggers.

    Returns escalation_required (bool) and the first matching reason.
    Legal threats always escalate immediately, before any other check.
    """
    if mentions_legal_threat:
        return {
            "escalation_required": True,
            "escalation_reason": (
                "Customer has mentioned legal action or a formal complaint. "
                "Escalating immediately to a human agent — no further automated resolution."
            ),
            "immediate": True,
        }

    reasons: list[str] = []

    if compensation_beyond_policy:
        reasons.append(
            "Customer requested compensation beyond stated policy amounts "
            "(e.g., free upgrade, extra monetary compensation)."
        )
    if fare_diff_waiver_exceeds_limit:
        reasons.append(
            f"Fare difference waiver requested exceeds the ₹{FARE_DIFF_WAIVER_MAX_INR} "
            "agent authority limit."
        )
    if non_airline_exception_requested:
        reasons.append(
            "Customer requested an exception for a disruption not caused by the airline."
        )
    if alternate_refund_method_requested:
        reasons.append(
            "Customer requested refund to a payment method different from the original."
        )

    if reasons:
        return {
            "escalation_required": True,
            "escalation_reason": " | ".join(reasons),
            "immediate": False,
        }

    return {
        "escalation_required": False,
        "escalation_reason": None,
        "immediate": False,
    }
