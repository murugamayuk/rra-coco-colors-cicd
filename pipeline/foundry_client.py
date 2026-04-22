"""Foundry client — direct HTTP with API key for CI, SDK for local."""
import os
import json
import asyncio
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY")

if not PROJECT_ENDPOINT:
    raise ValueError("PROJECT_ENDPOINT or FOUNDRY_ENDPOINT not set")

# SDK client for local (AzureCliCredential)
_openai_client = None

def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from azure.identity import AzureCliCredential
        from azure.ai.projects import AIProjectClient
        client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=AzureCliCredential(),
        )
        _openai_client = client.get_openai_client()
    return _openai_client


async def call_foundry_agent(agent_name: str, payload: dict) -> dict:
    """Call agent — API key via HTTP for CI, SDK for local."""
    prompt = json.dumps(payload, ensure_ascii=False)

    if FOUNDRY_API_KEY:
        # CI/CD path — direct Activity Protocol with API key
        def invoke_http():
            url = f"{PROJECT_ENDPOINT}/applications/{agent_name}/protocols/activityprotocol?api-version=2025-11-15-preview"
            body = json.dumps({
                "type": "message",
                "text": prompt,
                "conversation": {"id": "ci-eval-001", "isGroup": False},
                "recipient": {"id": "agent", "role": "bot"},
                "from": {"id": "ci-runner", "role": "user"},
                "channelId": "directline",
            }).encode()
            headers = {
                "Content-Type": "application/json",
                "api-key": FOUNDRY_API_KEY,
            }
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req) as r:
                    raw = r.read().decode()
                    return {"agent": agent_name, "output": raw or "202 accepted"}
            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                return {"agent": agent_name, "output": f"HTTP {e.code}: {error_body[:200]}"}

        return await asyncio.to_thread(invoke_http)
    else:
        # Local path — SDK with AzureCliCredential
        def invoke_sdk():
            oc = _get_openai_client()
            conversation = oc.conversations.create(
                items=[{"type": "message", "role": "user", "content": prompt}]
            )
            response = oc.responses.create(
                conversation=conversation.id,
                input=prompt,
                extra_body={
                    "agent_reference": {
                        "name": agent_name,
                        "type": "agent_reference",
                    }
                },
            )
            return {"agent": agent_name, "output": response.output_text}

        return await asyncio.to_thread(invoke_sdk)
