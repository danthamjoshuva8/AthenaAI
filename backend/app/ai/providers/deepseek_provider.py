import json

import httpx

from app.core.config import settings
from app.ai.providers.base_provider import BaseLLMProvider


class DeepSeekProvider(BaseLLMProvider):

    BASE_URL = "https://api.deepseek.com/chat/completions"

    async def analyze_trade(self, prompt: str):

        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are AthenaAI. "
                        "Always return ONLY valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.2,
            "max_tokens": 5000,
            "response_format": {
                "type": "json_object"
            }
        }

        async with httpx.AsyncClient(timeout=60) as client:

            response = await client.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                print(settings.DEEPSEEK_MODEL)
                print("Status Code:", response.status_code)
                print("Response Body:", response.text)
                print("Request Payload:", payload)
                raise Exception(f"DeepSeek Error: {response.text}")

            response.raise_for_status()

            data = response.json()

        content = response.json()["choices"][0]["message"]["content"]

        print("=" * 100)
        print(response.json())
        print("=" * 100)

        return json.loads(content)