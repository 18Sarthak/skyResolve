"""
OpenAI intent-extraction call.

Parses a customer's free-text message into a structured JSON intent object.
Uses gpt-4o-mini with response_format json_object and low temperature for
consistency. Wrapped in tenacity retry for resilience during live demos.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an airline customer support intent classifier. Given a customer message and context,
extract the intent into a JSON object with EXACTLY these fields:

{
  "requested_action": "<string: one of rebooking|refund|compensation|upgrade|information|other>",
  "secondary_actions": ["<list of any additional actions requested>"],
  "sentiment": "<string: positive|neutral|frustrated|angry>",
  "anger_flag": <boolean>,
  "mentions_legal_threat": <boolean: true if customer mentions lawsuit, legal action, consumer court, complaint authority, or regulatory body>,
  "compensation_beyond_policy": <boolean: true if customer requests something not in standard policy, e.g. upgrades, extra vouchers, cash beyond refund>,
  "alternate_refund_method_requested": <boolean: true if customer asks for refund to a different payment method>,
  "fare_upgrade_requested": <boolean: true if customer wants to switch to a higher-fare flight voluntarily>,
  "estimated_fare_diff_inr": <number or null: customer's stated or implied fare difference amount>,
  "hotel_requested": <boolean: true if customer explicitly asks for hotel accommodation>,
  "full_night_hotel_requested": <boolean: true if customer asks for a full overnight stay vs just delayed hours>,
  "target_flight_context": "<string: brief description of which flight the customer is asking about>"
}

Return ONLY the JSON object. No explanation, no markdown, no extra text.
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def extract_intent_llm(
    customer_message: str,
    customer_name: str,
    flight_context: str,
    client: OpenAI,
) -> tuple[dict[str, Any], int, int]:
    """
    Extract structured intent from a customer message.

    Returns:
        (intent_dict, prompt_tokens, completion_tokens)

    Raises:
        openai.OpenAIError on persistent failure after retries.
    """
    user_content = (
        f"Customer name: {customer_name}\n"
        f"Flight context: {flight_context}\n"
        f"Customer message: {customer_message}"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    raw = response.choices[0].message.content
    intent = json.loads(raw)

    prompt_tokens = response.usage.prompt_tokens if response.usage else 0
    completion_tokens = response.usage.completion_tokens if response.usage else 0

    logger.info(
        "Intent extracted | tokens: prompt=%d completion=%d",
        prompt_tokens,
        completion_tokens,
    )

    return intent, prompt_tokens, completion_tokens
