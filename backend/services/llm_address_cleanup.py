import json

from config import settings
from schemas.llm_outputs import CleanedAddress

SYSTEM_PROMPT = (
    "You clean up messy OCR text into a structured mailing address. "
    "If the text is too garbled to confidently produce an address, set "
    "confidence to 'low' and leave the address fields null - never invent "
    "details that aren't supported by the text. Return ONLY JSON, no other "
    "text, matching this shape: "
    '{"street": string|null, "city": string|null, "state": string|null, '
    '"zip": string|null, "confidence": "high"|"low", "notes": string|null}'
)


def clean_address(raw_text: str) -> CleanedAddress:
    """Calls the LLM and validates its output against CleanedAddress.
    Raises (ValueError/ValidationError) on malformed output - the caller
    treats that as a distinct failure mode from a plain low-confidence
    result."""
    content = _call_llm(SYSTEM_PROMPT, raw_text)
    data = json.loads(_strip_code_fence(content))
    return CleanedAddress(**data)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return text.strip()


def _call_llm(system_prompt: str, user_content: str) -> str:
    if settings.LLM_PROVIDER == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=settings.LLM_API_KEY)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return resp.content[0].text
    else:
        import openai

        client = openai.OpenAI(api_key=settings.LLM_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return resp.choices[0].message.content
