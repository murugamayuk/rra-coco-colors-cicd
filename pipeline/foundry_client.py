"""Foundry client — invokes published workflow/agent applications.

Canonical URL (from Foundry "Consume" panel):
  {resource_endpoint}/api/projects/{project}/applications/{app}/protocols/activityprotocol?api-version=2025-11-15-preview

Auth: api-key header (per Foundry Consume panel).
Note: if any internal agent uses OBO-auth tools (e.g. knowledge bases
with On-Behalf-Of auth), API key will fail and bearer token is required.
"""

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
PROJECT_NAME     = os.getenv("FOUNDRY_PROJECT_NAME", "proj-default")
FOUNDRY_API_KEY  = os.getenv("FOUNDRY_API_KEY")
API_VERSION      = os.getenv("FOUNDRY_API_VERSION", "2025-11-15-preview")

if not PROJECT_ENDPOINT:
    raise ValueError("PROJECT_ENDPOINT or FOUNDRY_ENDPOINT not set")

# Normalize: strip trailing slash, append /api/projects/{name} if not already present
PROJECT_ENDPOINT = PROJECT_ENDPOINT.rstrip("/")
if "/api/projects/" in PROJECT_ENDPOINT:
    _BASE = PROJECT_ENDPOINT
else:
    _BASE = f"{PROJECT_ENDPOINT}/api/projects/{PROJECT_NAME}"


# ── Bearer token (fallback for OBO-auth tools) ───────────────────────────────

_bearer_token = None
_bearer_expires_at = 0


def _get_bearer_token() -> str | None:
    global _bearer_token, _bearer_expires_at
    import time

    now = time.time()
    if _bearer_token and now < _bearer_expires_at - 300:
        return _bearer_token

    try:
        from azure.identity import DefaultAzureCredential
        cred = DefaultAzureCredential()
        token = cred.get_token("https://ai.azure.com/.default")
        _bearer_token = token.token
        _bearer_expires_at = token.expires_on
        return _bearer_token
    except Exception:
        return None


def _build_headers(prefer_bearer: bool = False) -> dict:
    """API key by default (matches Consume panel). Bearer if explicitly requested."""
    if prefer_bearer or not FOUNDRY_API_KEY:
        token = _get_bearer_token()
        if token:
            return {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }
    if FOUNDRY_API_KEY:
        return {
            "Content-Type": "application/json",
            "api-key": FOUNDRY_API_KEY,
        }
    raise RuntimeError(
        "No auth available. Set FOUNDRY_API_KEY or configure OIDC/az login."
    )


# ── Agent/Workflow invocation ────────────────────────────────────────────────

async def call_foundry_agent(app_name: str, payload: dict) -> dict:
    """Invoke a published workflow or agent via Activity Protocol.

    `app_name` is the published application name (e.g. 'document-workflow-v2').
    `payload` is serialized to JSON and sent as the `text` field of the activity.
    """
    prompt = json.dumps(payload, ensure_ascii=False)

    def invoke_http(use_bearer: bool = False):
        url = (
            f"{_BASE}/applications/{urllib.parse.quote(app_name)}"
            f"/protocols/activityprotocol"
            f"?api-version={API_VERSION}"
        )

        body = json.dumps({
            "type": "message",
            "text": prompt,
            "conversation": {"id": f"ci-{os.getpid()}", "isGroup": False},
            "recipient": {"id": "agent", "role": "bot"},
            "from": {"id": "ci-runner", "role": "user"},
            "channelId": "directline",
        }).encode()

        headers = _build_headers(prefer_bearer=use_bearer)
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read().decode()
                try:
                    parsed = json.loads(raw) if raw else {"status": "202 accepted"}
                except json.JSONDecodeError:
                    parsed = {"raw": raw}
                return {"agent": app_name, "output": parsed}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            # If OBO auth error with API key, retry with bearer token
            if (e.code in (401, 403) and not use_bearer
                    and "OBO" in error_body):
                print(f"⚠️  {e.code} with API key (OBO tool detected), retrying with bearer...")
                return invoke_http(use_bearer=True)
            return {
                "agent": app_name,
                "error": True,
                "status": e.code,
                "output": f"HTTP {e.code}: {error_body[:500]}",
                "url": url,
            }
        except urllib.error.URLError as e:
            return {
                "agent": app_name,
                "error": True,
                "output": f"URL error: {e.reason}",
                "url": url,
            }

    return await asyncio.to_thread(invoke_http)
