"""Foundry client — supports both API key and AzureCliCredential."""
import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY")

if not PROJECT_ENDPOINT:
    raise ValueError("PROJECT_ENDPOINT or FOUNDRY_ENDPOINT is not set")

# Use API key if available (CI/CD), else AzureCliCredential (local)
if FOUNDRY_API_KEY:
    import openai
    _client = openai.AzureOpenAI(
        azure_endpoint=PROJECT_ENDPOINT,
        api_key=FOUNDRY_API_KEY,
        api_version="2025-01-01-preview"
    )
    _use_sdk = False
else:
    from azure.identity import AzureCliCredential
    from azure.ai.projects import AIProjectClient
    _credential = AzureCliCredential()
    _project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=_credential,
    )
    _openai_client = _project_client.get_openai_client()
    _use_sdk = True


async def call_foundry_agent(agent_name: str, payload: dict) -> dict:
    """Call a Foundry agent — works with API key or AzureCliCredential."""
    prompt = json.dumps(payload, ensure_ascii=False)

    def invoke():
        if _use_sdk:
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
        else:
            # API key path — direct responses API
            response = _client.responses.create(
                model="gpt-4o-mini",
                input=prompt,
            )
            return {"agent": agent_name, "output": response.output_text}

    return await asyncio.to_thread(invoke)
