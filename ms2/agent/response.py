"""
OpenAI response-drafting call.

Takes a pre-computed policy decision (ground truth) and drafts an empathetic
customer-facing message. The LLM is explicitly prohibited from altering the
substance of the decision — it only phrases it.

Uses gpt-4o with temperature=0.4 for natural, empathetic language.
Wrapped in tenacity retry for live-demo resilience.
"""
from __future__ import annotations

import logging

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are SkyResolve, a customer support agent for SkyAirlines.
Your ONLY job is to phrase the following pre-computed policy decision into a warm, empathetic,
and clear message for the customer. You MUST NOT alter any of the following:
- The specific actions allowed or denied
- Any monetary amounts or thresholds
- Whether the case is escalated or not
- The escalation reason if provided

You are a voice, not a decision-maker. The policy decision is ground truth.

Guidelines:
- Address the customer by name.
- Acknowledge any inconvenience sincerely.
- Clearly explain what the customer is entitled to.
- If something is denied, explain why briefly and without being dismissive.
- If escalating, inform the customer warmly that a specialist will be in touch shortly.
- Keep the message concise (3-5 short paragraphs maximum).
- Do not use bullet points — write in flowing prose.
- Do not invent actions, amounts, or commitments not in the decision.
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def draft_response_llm(
    customer_name: str,
    customer_message: str,
    policy_decision: dict,
    client: OpenAI,
) -> tuple[str, int, int]:
    """
    Draft an empathetic customer-facing response based on a policy decision.

    Returns:
        (response_text, prompt_tokens, completion_tokens)

    Raises:
        openai.OpenAIError on persistent failure after retries.
    """
    import json

    decision_json = json.dumps(policy_decision, indent=2)

    user_content = (
        f"Customer name: {customer_name}\n"
        f"Customer's message: {customer_message}\n\n"
        f"Policy decision (ground truth — do not contradict):\n{decision_json}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.4,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    text = response.choices[0].message.content.strip()

    prompt_tokens = response.usage.prompt_tokens if response.usage else 0
    completion_tokens = response.usage.completion_tokens if response.usage else 0

    logger.info(
        "Response drafted | tokens: prompt=%d completion=%d",
        prompt_tokens,
        completion_tokens,
    )

    return text, prompt_tokens, completion_tokens
