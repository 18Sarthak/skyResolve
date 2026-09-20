"""
Unit tests for all policy rule functions.

These tests run entirely offline — no LLM calls, no network, no database.
Each function in data/policy_rules.py is independently exercised.
"""
import pytest

from data.policy_rules import (
    FARE_DIFF_WAIVER_MAX_INR,
    HOTEL_THRESHOLD_HOURS,
    LOUNGE_ACCESS_THRESHOLD_HOURS,
    MEAL_VOUCHER_AMOUNT_INR,
    check_cancellation_entitlements,
    check_delay_entitlements,
    check_fare_difference_rule,
    check_loyalty_tier_extras,
    check_refund_rules,
    evaluate_escalation_triggers,
)


# ---------------------------------------------------------------------------
# check_cancellation_entitlements
# ---------------------------------------------------------------------------

class TestCancellationEntitlements:
    def test_airline_caused_allows_rebooking_and_refund(self):
        result = check_cancellation_entitlements("airline")
        assert "free_rebooking_within_24h" in result["allowed_actions"]
        assert "full_refund" in result["allowed_actions"]
        assert result["denied_actions"] == []

    def test_passenger_caused_denies_everything(self):
        result = check_cancellation_entitlements("passenger")
        assert result["allowed_actions"] == []
        assert len(result["denied_actions"]) > 0

    def test_no_cause_denies_everything(self):
        result = check_cancellation_entitlements("none")
        assert result["allowed_actions"] == []


# ---------------------------------------------------------------------------
# check_delay_entitlements
# ---------------------------------------------------------------------------

class TestDelayEntitlements:
    def test_zero_delay_no_entitlements(self):
        result = check_delay_entitlements(0)
        assert result["allowed_actions"] == []

    def test_short_delay_meal_voucher_only(self):
        result = check_delay_entitlements(2.0)
        assert "meal_voucher" in result["allowed_actions"]
        assert "lounge_access" not in result["allowed_actions"]
        assert "hotel_for_delayed_hours_only" not in result["allowed_actions"]
        assert "hotel" in result["denied_actions"]

    def test_at_lounge_threshold_grants_lounge(self):
        result = check_delay_entitlements(LOUNGE_ACCESS_THRESHOLD_HOURS)
        assert "meal_voucher" in result["allowed_actions"]
        assert "lounge_access" in result["allowed_actions"]
        assert "hotel_for_delayed_hours_only" not in result["allowed_actions"]

    def test_four_hour_delay_no_hotel(self):
        """Scenario 2: Arvind's 4h delay should NOT grant hotel."""
        result = check_delay_entitlements(4.0)
        assert "meal_voucher" in result["allowed_actions"]
        assert "lounge_access" in result["allowed_actions"]
        assert "hotel_for_delayed_hours_only" not in result["allowed_actions"]
        assert "hotel" in result["denied_actions"]
        assert "hotel_denial_reason" in result["details"]

    def test_just_above_hotel_threshold_grants_hotel(self):
        result = check_delay_entitlements(HOTEL_THRESHOLD_HOURS + 0.1)
        assert "hotel_for_delayed_hours_only" in result["allowed_actions"]

    def test_six_hour_delay_grants_hotel(self):
        """Scenario 3: Meher's 6h delay should grant hotel (for delayed hours only)."""
        result = check_delay_entitlements(6.0)
        assert "meal_voucher" in result["allowed_actions"]
        assert "lounge_access" in result["allowed_actions"]
        assert "hotel_for_delayed_hours_only" in result["allowed_actions"]
        # Hotel note must clarify it's delayed hours only
        assert "hotel_note" in result["details"]
        assert "delayed hours" in result["details"]["hotel_note"].lower()

    def test_exactly_at_hotel_threshold_no_hotel(self):
        """Boundary: exactly 5h is NOT above threshold."""
        result = check_delay_entitlements(HOTEL_THRESHOLD_HOURS)
        assert "hotel_for_delayed_hours_only" not in result["allowed_actions"]
        assert "hotel" in result["denied_actions"]

    def test_meal_voucher_amount_in_details(self):
        result = check_delay_entitlements(2.0)
        assert result["details"]["meal_voucher_amount_inr"] == MEAL_VOUCHER_AMOUNT_INR


# ---------------------------------------------------------------------------
# check_refund_rules
# ---------------------------------------------------------------------------

class TestRefundRules:
    def test_original_method_allowed(self):
        result = check_refund_rules(True)
        assert "process_refund" in result["allowed_actions"]
        assert result["denied_actions"] == []

    def test_alternate_method_denied(self):
        result = check_refund_rules(False)
        assert result["allowed_actions"] == []
        assert "process_refund_to_alternate_method" in result["denied_actions"]


# ---------------------------------------------------------------------------
# check_fare_difference_rule
# ---------------------------------------------------------------------------

class TestFareDifferenceRule:
    def test_below_limit_allowed(self):
        result = check_fare_difference_rule(1000)
        assert "collect_fare_difference" in result["allowed_actions"]
        assert result["denied_actions"] == []

    def test_at_exact_limit_allowed(self):
        result = check_fare_difference_rule(FARE_DIFF_WAIVER_MAX_INR)
        assert "collect_fare_difference" in result["allowed_actions"]

    def test_above_limit_denied_and_escalated(self):
        """Scenario 3: Meher's ₹2,000 fare diff should be denied."""
        result = check_fare_difference_rule(2000)
        assert result["allowed_actions"] == []
        assert "waive_fare_difference" in result["denied_actions"]
        assert "Supervisor approval required" in result["details"]["reason"]

    def test_just_above_limit(self):
        result = check_fare_difference_rule(FARE_DIFF_WAIVER_MAX_INR + 1)
        assert result["allowed_actions"] == []
        assert "waive_fare_difference" in result["denied_actions"]


# ---------------------------------------------------------------------------
# check_loyalty_tier_extras
# ---------------------------------------------------------------------------

class TestLoyaltyTierExtras:
    def test_silver_no_priority(self):
        result = check_loyalty_tier_extras("Silver")
        assert "priority_rebooking" not in result["allowed_actions"]

    def test_gold_gets_priority(self):
        result = check_loyalty_tier_extras("Gold")
        assert "priority_rebooking" in result["allowed_actions"]
        assert result["details"]["extra_compensation"] is False

    def test_platinum_gets_priority(self):
        result = check_loyalty_tier_extras("Platinum")
        assert "priority_rebooking" in result["allowed_actions"]
        assert result["details"]["extra_compensation"] is False

    def test_no_extra_monetary_compensation_for_any_tier(self):
        for tier in ("Silver", "Gold", "Platinum"):
            result = check_loyalty_tier_extras(tier)
            assert result["details"]["extra_compensation"] is False


# ---------------------------------------------------------------------------
# evaluate_escalation_triggers
# ---------------------------------------------------------------------------

class TestEscalationTriggers:
    def test_legal_threat_immediate_escalation(self):
        result = evaluate_escalation_triggers(
            mentions_legal_threat=True,
            compensation_beyond_policy=False,
            fare_diff_waiver_exceeds_limit=False,
            non_airline_exception_requested=False,
            alternate_refund_method_requested=False,
        )
        assert result["escalation_required"] is True
        assert result["immediate"] is True

    def test_compensation_beyond_policy_triggers_escalation(self):
        """Scenario 1: Priya demands free business-class upgrade."""
        result = evaluate_escalation_triggers(
            mentions_legal_threat=False,
            compensation_beyond_policy=True,
            fare_diff_waiver_exceeds_limit=False,
            non_airline_exception_requested=False,
            alternate_refund_method_requested=False,
        )
        assert result["escalation_required"] is True
        assert result["immediate"] is False

    def test_fare_diff_exceeds_limit_triggers_escalation(self):
        """Scenario 3: Meher's ₹2,000 fare diff."""
        result = evaluate_escalation_triggers(
            mentions_legal_threat=False,
            compensation_beyond_policy=False,
            fare_diff_waiver_exceeds_limit=True,
            non_airline_exception_requested=False,
            alternate_refund_method_requested=False,
        )
        assert result["escalation_required"] is True

    def test_no_triggers_no_escalation(self):
        result = evaluate_escalation_triggers(
            mentions_legal_threat=False,
            compensation_beyond_policy=False,
            fare_diff_waiver_exceeds_limit=False,
            non_airline_exception_requested=False,
            alternate_refund_method_requested=False,
        )
        assert result["escalation_required"] is False
        assert result["escalation_reason"] is None

    def test_alternate_refund_method_triggers_escalation(self):
        result = evaluate_escalation_triggers(
            mentions_legal_threat=False,
            compensation_beyond_policy=False,
            fare_diff_waiver_exceeds_limit=False,
            non_airline_exception_requested=False,
            alternate_refund_method_requested=True,
        )
        assert result["escalation_required"] is True

    def test_legal_threat_overrides_all_other_flags(self):
        """Legal threat must always produce immediate=True regardless of other flags."""
        result = evaluate_escalation_triggers(
            mentions_legal_threat=True,
            compensation_beyond_policy=True,
            fare_diff_waiver_exceeds_limit=True,
            non_airline_exception_requested=True,
            alternate_refund_method_requested=True,
        )
        assert result["immediate"] is True
