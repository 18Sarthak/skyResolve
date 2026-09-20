"""
FastAPI routes for the SkyResolve backend.

Endpoints:
  POST /conversation/{customer_pnr}/message  — run one agent turn
  GET  /conversation/{customer_pnr}/history  — full audit trail for a PNR
  GET  /health                               — liveness + API key check
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

from agent.graph import run_conversation_turn
from db.audit import get_history, init_db

load_dotenv()

_DEFAULT_ORIGINS = "http://localhost:3000,http://localhost:5173,http://localhost:8080,http://127.0.0.1:8080"

def _get_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS)
    return [o.strip() for o in raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SkyResolve — Airline Disruption Resolution Agent",
    description="Backend API for the SkyResolve agentic customer support system.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


def _get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set. Configure it in your .env file.",
        )
    return OpenAI(api_key=api_key)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class MessageRequest(BaseModel):
    message: str


class MessageResponse(BaseModel):
    response: str
    actions_taken: list[str]
    escalated: bool
    escalation_reason: str | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    """Liveness check. Verifies OPENAI_API_KEY is configured."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "OPENAI_API_KEY is not set. Add it to your .env file.",
            },
        )
    return {"status": "ok", "openai_key_configured": True}


@app.post("/conversation/{customer_pnr}/message", response_model=MessageResponse)
async def post_message(customer_pnr: str, body: MessageRequest) -> MessageResponse:
    """
    Process one customer message through the full agent pipeline.

    Runs: lookup_booking → extract_intent → apply_policy →
          draft_response (or human_handoff) → log_turn
    """
    client = _get_openai_client()

    try:
        final_state = run_conversation_turn(
            pnr=customer_pnr,
            customer_message=body.message,
            openai_client=client,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    policy_decision = final_state.get("policy_decision") or {}

    return MessageResponse(
        response=final_state.get("agent_response") or "",
        actions_taken=policy_decision.get("allowed_actions", []),
        escalated=final_state.get("escalation_required", False),
        escalation_reason=policy_decision.get("escalation_reason"),
    )


@app.get("/conversation/{customer_pnr}/history")
async def get_conversation_history(customer_pnr: str) -> list[dict]:
    """Return the full audit trail for the given PNR, oldest turn first."""
    history = get_history(customer_pnr.upper())
    return history
