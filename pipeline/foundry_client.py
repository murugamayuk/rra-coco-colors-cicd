"""Foundry client — exact pattern that works on jump server."""
import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY")

if not PROJECT_ENDPOINT:
    raise ValueError("PROJECT_ENDPOINT or FOUNDRY_ENDPOINT not set")

from azure.ai.projects import AIProjectClient

if FOUNDRY_API_KEY:
    from azure.core.credentials import AzureKeyCredential
    _project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=AzureKeyCredential(FOUNDRY_API_KEY),
    )
else:
    from azure.identity import AzureCliCredential
    _project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=AzureCliCredential(),
    )

_openai_client = _project_client.get_openai_client()


async def call_foundry_agent(agent_name: str, payload: dict) -> dict:
    """Call agent — exact pattern verified working on jump server."""
    prompt = json.dumps(payload, ensure_ascii=False)

    def invoke():
        conversation = _openai_client.conversations.create(
            items=[{"type": "message", "role": "user", "content": prompt}]
        )
        response = _openai_client.responses.create(
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

    return await asyncio.to_thread(invoke)
