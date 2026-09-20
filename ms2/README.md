# SkyResolve — Airline Disruption Customer Resolution Agent (Backend)

## Overview

SkyResolve is an AI-powered airline disruption support agent backend. It handles customer conversations about flight cancellations and delays, applies airline policy **deterministically** (no LLM in the policy layer), and escalates to a human agent when policy authority runs out.

**Tech stack:** Python 3.11 · LangGraph · OpenAI SDK · FastAPI · SQLite

---

## Quick Start

### 1. Clone and set up the environment

```bash
cd SkyResolve
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your OpenAI API key

```bash
cp .env.example .env
# Open .env and replace the placeholder with your real key:
#   OPENAI_API_KEY=sk-...your-key-here...
```

> ⚠️ Never commit `.env` to version control. It is in `.gitignore`.

### 3. Start the backend server

```bash
python main.py
```

The server starts at `http://localhost:8000`.
Swagger UI is available at `http://localhost:8000/docs`.

---

## API Reference

### `GET /health`
Liveness check. Returns `{"status": "ok"}` if the API key is configured, or an error if it's missing.

### `POST /conversation/{customer_pnr}/message`
Run one turn of the agent for the given PNR.

**Request body:**
```json
{ "message": "My flight was cancelled, I want a refund." }
```

**Response:**
```json
{
  "response": "Dear Priya, ...",
  "actions_taken": ["free_rebooking_within_24h", "full_refund", "priority_rebooking"],
  "escalated": false,
  "escalation_reason": null
}
```

### `GET /conversation/{customer_pnr}/history`
Returns the full audit trail for a PNR — all turns, parsed intents, policy decisions, and token usage.

---

## Running the Tests

### Policy unit tests (offline, no API key needed)

```bash
pytest tests/test_policy.py -v
```

These tests exercise all 5 policy functions against boundary conditions (3h/5h thresholds, ₹1,500 fare limit, etc.) with zero network calls.

### End-to-end scenario tests (requires running server + API key)

In one terminal, start the server:
```bash
python main.py
```

In another terminal:
```bash
python tests/test_scenarios.py
```

This runs all three required demo scenarios and prints full output.

---

## Test Scenarios

| # | Customer | PNR | Situation | Expected |
|---|----------|-----|-----------|----------|
| 1 | Priya Nair (Gold) | SK4821X | Cancelled flight, demands refund + free business-class upgrade | Rebook/refund offered ✅, upgrade demand escalated 🔺 |
| 2 | Arvind Kulkarni (Silver) | TR1190B | 4h delay, requests hotel | Meal + lounge granted ✅, hotel denied ❌ (not >5h) |
| 3 | Meher Kaur (Platinum) | WL7742 | 6h delay, wants full-night hotel + ₹2,000 fare waiver | Hotel for delayed hours only ✅, fare diff escalated 🔺 |

---

## Architecture

```
POST /message
     │
     └─► LangGraph Pipeline
              │
              ├─ lookup_booking      [deterministic] fetch customer + booking
              ├─ extract_intent      [LLM: gpt-4o-mini] parse free-text → JSON
              ├─ apply_policy        [deterministic] compute entitlements
              │       │
              │  escalation_required?
              │       ├─ YES → human_handoff  [fixed message, no LLM]
              │       └─ NO  → draft_response [LLM: gpt-4o] phrase decision
              │
              └─ log_turn            [deterministic] write to SQLite
```

### Policy Rules (enforced deterministically, single source of truth)

| Rule | Detail |
|------|--------|
| Cancellation | Airline-caused → free rebooking within 24h **or** full refund |
| Delay <3h | ₹500 meal voucher |
| Delay ≥3h | Meal voucher + lounge access |
| Delay >5h | Meal + lounge + hotel for **delayed hours only** |
| Refund | 7 business days, original payment method only |
| Fare difference | Agent waiver limit ₹1,500; above requires supervisor |
| Loyalty | Gold/Platinum → priority rebooking only (no extra comp) |

### Escalation Triggers (always routes to human)

- Any compensation beyond stated policy (free upgrades, extra cash, etc.)
- Fare difference waiver above ₹1,500
- Exception for non-airline-caused disruption
- Legal threat or formal complaint mention — **immediate**, no automated resolution
- Refund to a different payment method

---

## Project Structure

```
SkyResolve/
├── data/
│   ├── customers.py      — Customer records + PNR lookup
│   ├── bookings.py       — Booking records + disruption metadata
│   └── policy_rules.py   — Pure deterministic policy functions
├── agent/
│   ├── graph.py          — LangGraph StateGraph definition
│   ├── nodes.py          — 5 node functions + human_handoff
│   ├── intent.py         — OpenAI intent-extraction call
│   └── response.py       — OpenAI response-drafting call
├── db/
│   └── audit.py          — SQLite schema + log_turn + get_history
├── api/
│   └── routes.py         — FastAPI app + 3 endpoints
├── tests/
│   ├── test_policy.py    — Offline policy unit tests
│   └── test_scenarios.py — E2E scenario tests
├── main.py               — Uvicorn entrypoint
├── requirements.txt
├── .env.example
└── README.md
```

---

## LLM Cost Notes

- Intent extraction uses `gpt-4o-mini` (cheaper, structured JSON output).
- Response drafting uses `gpt-4o` (better empathy and natural language).
- Token usage per call is stored in the SQLite audit trail for cost visibility.
- Both calls are wrapped with tenacity retry (3 attempts, exponential backoff).
