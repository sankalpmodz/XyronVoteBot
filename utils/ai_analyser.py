import httpx
import json
import re
import asyncio
import unicodedata
from config import AI_API_KEYS, AI_API_URL, AI_MODEL

SYSTEM_PROMPT = """Content moderation AI for a Telegram giveaway bot. Analyze user's name and username for illegal/harmful content.

IMPORTANT: Users may have names in ANY language (Hindi, Arabic, Japanese, Chinese, Russian, etc.) or use special fonts/symbols/emojis. Focus ONLY on the actual meaning.

Flag UNSAFE ONLY for CLEAR, EXPLICIT references to:
- Child exploitation/CSAM/child abuse
- Illegal weapons trafficking/explosives manufacturing
- Illegal drug trafficking/sales
- Terrorism/violent extremist propaganda
- Extreme hate speech/racial slurs
- Pornographic/sexually explicit content
- Gore/extreme graphic violence

ALWAYS mark SAFE (ignore completely):
- Telegram platform labels: "scam", "fake", warning tags — added by Telegram, NOT by user
- Impersonation of celebrities/brands/organizations — NOT illegal
- Normal/innocent/gaming/edgy names and nicknames in ANY language
- Names with special fonts, symbols, emojis, decorations — SAFE
- Names you cannot read or understand — mark SAFE
- Empty or minimal profiles

Respond ONLY with JSON:
{"safe": true, "reason": ""}
or
{"safe": false, "reason": "Short reason"}"""


def _sanitize_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r'[\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff]', '', text)
    text = ''.join(c for c in text if unicodedata.category(c)[0] != 'C' or c in '\n\t ')
    text = re.sub(r' +', ' ', text).strip()
    return text


async def _call_ai_api(api_key: str, profile_text: str) -> dict | None:
    endpoint = AI_API_URL or "https://api.openai.com/v1/chat/completions"
    model = AI_MODEL or "gpt-4o-mini"
    try:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this Telegram user profile:\n\n{profile_text}"}
            ],
            "temperature": 0.1,
            "max_completion_tokens": 1024,
            "reasoning_effort": "low"
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )

            if response.status_code == 400 and "reasoning_effort" in response.text:
                payload.pop("reasoning_effort", None)
                payload.pop("max_completion_tokens", None)
                payload["max_tokens"] = 1024
                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

            if response.status_code == 429:
                print(f"[AI_ANALYSER] Rate limited on key ...{api_key[-6:]}")
                return None
            if response.status_code != 200:
                print(f"[AI_ANALYSER] Error {response.status_code} on key ...{api_key[-6:]}: {response.text[:150]}")
                return None

            data = response.json()
            choices = data.get("choices")
            if not choices or len(choices) == 0:
                print(f"[AI_ANALYSER] Empty choices from key ...{api_key[-6:]}")
                return None

            msg = choices[0].get("message", {})
            content = (msg.get("content") or "").strip()
            reasoning = (msg.get("reasoning") or msg.get("reasoning_content") or "").strip()

            raw_text = content if content else reasoning
            if not raw_text:
                print(f"[AI_ANALYSER] Empty content & reasoning from key ...{api_key[-6:]}")
                return None

            clean_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
            clean_text = re.sub(r'\s*```$', '', clean_text).strip()

            result = None
            try:
                result = json.loads(clean_text)
            except json.JSONDecodeError:
                pass

            if not result or not isinstance(result, dict):
                m = re.search(r'\{[^{}]*"safe"\s*:\s*(true|false)[^{}]*\}', clean_text, re.IGNORECASE)
                if m:
                    try:
                        result = json.loads(m.group())
                    except json.JSONDecodeError:
                        pass

            if not result or not isinstance(result, dict):
                m = re.search(r'["\']?safe["\']?\s*:\s*(true|false)', clean_text, re.IGNORECASE)
                if m:
                    is_safe = m.group(1).lower() == "true"
                    r = re.search(r'["\']?reason["\']?\s*:\s*["\']([^"\']*)', clean_text)
                    result = {"safe": is_safe, "reason": r.group(1) if r else ""}

            if not result or "safe" not in result:
                print(f"[AI_ANALYSER] Could not parse from key ...{api_key[-6:]}, raw: {repr(clean_text[:200])}")
                return None

            return {
                "safe": bool(result["safe"]),
                "reason": str(result.get("reason", "") or "")
            }

    except httpx.TimeoutException:
        print(f"[AI_ANALYSER] Timeout on key ...{api_key[-6:]}")
        return None
    except Exception as e:
        print(f"[AI_ANALYSER] Error on key ...{api_key[-6:]}: {e}")
        return None


async def analyse_user_profile(first_name: str = "", last_name: str = "",
                                username: str = "", bio: str = "",
                                user_id: int = 0) -> dict:
    if not AI_API_KEYS:
        return {
            "safe": False,
            "reason": "AI Analyser not configured — joining blocked until API keys are set up.",
            "analysed": False
        }

    profile_parts = []
    if first_name:
        profile_parts.append(f"First Name: {_sanitize_text(first_name)}")
    if last_name:
        profile_parts.append(f"Last Name: {_sanitize_text(last_name)}")
    if username:
        profile_parts.append(f"Username: @{_sanitize_text(username)}")

    if not profile_parts:
        return {"safe": True, "reason": "", "analysed": True}

    profile_text = "\n".join(profile_parts)

    for i, api_key in enumerate(AI_API_KEYS):
        for attempt in range(2):
            result = await _call_ai_api(api_key, profile_text)

            if result is not None:
                result["analysed"] = True
                print(f"[AI_ANALYSER] OK key {i+1} attempt {attempt+1}: safe={result['safe']}")
                return result

            await asyncio.sleep(0.3)

    print("[AI_ANALYSER] ALL keys exhausted — blocking join (fail-closed, no ban)")
    return {
        "safe": False,
        "reason": "AI analysis temporarily unavailable — please try again later.",
        "analysed": False
    }
