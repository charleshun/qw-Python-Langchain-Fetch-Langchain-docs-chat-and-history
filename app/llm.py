import json
import aiohttp
from config import Config


async def stream_chat(messages, base_url=None, model=None):
    """
    Stream chat completion from llama.cpp OpenAI-compatible API.
    Yields content chunks as they arrive via SSE.
    """
    base_url = base_url or Config.LLM_BASE_URL
    model = model or Config.LLM_MODEL

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue
