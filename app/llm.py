"""Optional LLM access. The pipeline works without any API key (rule-based fallback)."""
import json
import os


def llm_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def llm_json(system: str, user: str) -> dict:
    from openai import OpenAI  # imported lazily so the package is optional

    client = OpenAI()
    resp = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return json.loads(resp.choices[0].message.content)
