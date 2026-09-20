"""
End-to-end scenario tests for the SkyResolve backend.

Requires:
  1. A running SkyResolve server (python main.py)
  2. A valid OPENAI_API_KEY in .env

Run with:
  python tests/test_scenarios.py

Each scenario prints the full API response and asserts on key expected outcomes.
"""
from __future__ import annotations

import json
import sys
import time
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"
SEPARATOR = "─" * 72


def call_message(pnr: str, message: str) -> dict[str, Any]:
    """POST a single message and return the parsed response JSON."""
    resp = httpx.post(
        f"{BASE_URL}/conversation/{pnr}/message",
        json={"message": message},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()


def print_result(scenario: str, pnr: str, message: str, result: dict) -> None:
    print(f"\n{SEPARATOR}")
    print(f"SCENARIO: {scenario}")
    print(f"PNR: {pnr}")
    print(f"CUSTOMER MESSAGE: {message}")
    print(SEPARATOR)
    print(f"AGENT RESPONSE:\n{result['response']}")
    print(f"\nACTIONS TAKEN: {result['actions_taken']}")
    print(f"ESCALATED:     {result['escalated']}")
    print(f"ESCALATION REASON: {result.get('escalation_reason')}")
    print(SEPARATOR)


def assert_or_fail(condition: bool, message: str) -> None:
    if not condition:
        print(f"\n❌  ASSERTION FAILED: {message}")
        sys.exit(1)
    print(f"✅  {message}")


def wait_for_server(max_wait: int = 30) -> None:
    print("Waiting for server to be ready...")
    for _ in range(max_wait):
        try:
            resp = httpx.get(f"{BASE_URL}/health", timeout=2.0)
            if resp.status_code == 200:
                print("Server is up.\n")
                return
        except httpx.ConnectError:
            time.sleep(1)
    print("ERROR: Server did not start within expected time.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Scenario 1 — Priya Nair (Gold, SK4821X)
# Cancelled flight, demands full refund + free business-class upgrade, angry
# Expected: offer rebook/refund correctly, ESCALATE the upgrade demand
# ---------------------------------------------------------------------------

def run_scenario_1() -> None:
    pnr = "SK4821X"
    message = (
        "My flight SK-204 to Goa was cancelled and this is completely unacceptable! "
        "I want a FULL CASH REFUND immediately AND a FREE business-class upgrade on "
        "my next flight for all this trouble. I'm absolutely furious!"
    )
    result = call_message(pnr, message)
    print_result("1 — Priya (Gold, cancelled flight + upgrade demand)", pnr, message, result)

    assert_or_fail(result["escalated"], "Scenario 1: Should be escalated due to upgrade demand")
    assert_or_fail(
        result["escalation_reason"] is not None,
        "Scenario 1: Must provide escalation reason",
    )


# ---------------------------------------------------------------------------
# Scenario 2 — Arvind Kulkarni (Silver, TR1190B)
# 4h delay, asks for hotel
# Expected: DENY hotel (delay not >5h), grant meal voucher + lounge only
# ---------------------------------------------------------------------------

def run_scenario_2() -> None:
    pnr = "TR1190B"
    message = (
        "My flight SK-118 from Mumbai is delayed by 4 hours. "
        "I need hotel accommodation arranged for while I wait — this is too long."
    )
    result = call_message(pnr, message)
    print_result("2 — Arvind (Silver, 4h delay + hotel request)", pnr, message, result)

    assert_or_fail(not result["escalated"], "Scenario 2: Should NOT be escalated")
    assert_or_fail(
        "meal_voucher" in result["actions_taken"],
        "Scenario 2: meal_voucher must be in actions_taken",
    )
    assert_or_fail(
        "lounge_access" in result["actions_taken"],
        "Scenario 2: lounge_access must be in actions_taken",
    )
    assert_or_fail(
        "hotel_for_delayed_hours_only" not in result["actions_taken"],
        "Scenario 2: hotel must NOT be granted for a 4h delay",
    )
    assert_or_fail(
        "hotel" not in result["actions_taken"],
        "Scenario 2: hotel must NOT appear in actions_taken",
    )


# ---------------------------------------------------------------------------
# Scenario 3 — Meher Kaur (Platinum, WL7742)
# 6h delay, asks for full night hotel + fare diff >₹1,500
# Expected: hotel granted for delayed hours only (not full night), escalate fare diff
# ---------------------------------------------------------------------------

def run_scenario_3() -> None:
    pnr = "WL7742"
    message = (
        "My flight SK-305 to Hyderabad is delayed by 6 hours. I want a full overnight "
        "hotel stay arranged, and I'd also like to switch to the earlier SK-302 flight "
        "which has a fare difference of ₹2,000. Please waive it given the delay."
    )
    result = call_message(pnr, message)
    print_result(
        "3 — Meher (Platinum, 6h delay + full-night hotel + ₹2,000 fare diff)",
        pnr,
        message,
        result,
    )

    assert_or_fail(result["escalated"], "Scenario 3: Should be escalated due to ₹2,000 fare diff")
    assert_or_fail(
        "hotel_for_delayed_hours_only" in result["actions_taken"],
        "Scenario 3: hotel_for_delayed_hours_only must be granted",
    )
    assert_or_fail(
        result["escalation_reason"] is not None
        and ("fare" in result["escalation_reason"].lower() or "1,500" in result["escalation_reason"]),
        "Scenario 3: escalation reason must mention fare difference",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    wait_for_server()
    print("\n" + "=" * 72)
    print("  SKYRESOLVE — END-TO-END SCENARIO TESTS")
    print("=" * 72)

    run_scenario_1()
    run_scenario_2()
    run_scenario_3()

    print(f"\n{'=' * 72}")
    print("  ALL SCENARIOS PASSED")
    print("=" * 72 + "\n")
