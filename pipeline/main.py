"""
COCO COLORS — Single-workflow invoker
Mayuksacred Foundry · document-workflow-v2

The workflow chains requirement-parser-v2 → resume-analyst-v2 →
score-synthesizer-v2 → output-agent internally via Local.* variables.
We invoke the workflow as one unit; Foundry handles the chain.
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from foundry_client import call_foundry_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# The published workflow name — overridable for staging/prod variants
WORKFLOW_NAME = os.getenv("FOUNDRY_WORKFLOW", "document-workflow-v2")


async def run_workflow(candidate_id: str, role: str) -> dict:
    """Invoke the published workflow end-to-end. One HTTP call."""
    start = datetime.utcnow()
    log.info("🚀 Invoking workflow=%s | candidate=%s role=%s",
             WORKFLOW_NAME, candidate_id, role)

    # The Start node of the workflow accepts a single input message.
    # Adjust these field names to match what requirement-parser-v2 expects
    # at the workflow entry point (check the Start node's output bindings
    # in the Foundry UI).
    result = await call_foundry_agent(
        WORKFLOW_NAME,
        {
            "candidate_id": candidate_id,
            "role": role,
            "position_spec": role,
        },
    )

    elapsed = (datetime.utcnow() - start).total_seconds()

    if result.get("error"):
        log.error("❌ Workflow failed after %.2fs: %s",
                  elapsed, result.get("output"))
    else:
        log.info("✅ Workflow complete in %.2fs", elapsed)

    return {
        "candidate_id": candidate_id,
        "role":         role,
        "workflow":     WORKFLOW_NAME,
        "result":       result,
        "pipeline_ms":  int(elapsed * 1000),
        "timestamp":    start.isoformat(),
    }


# ── ENTRYPOINT ────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="COCO COLORS Workflow Invoker")
    parser.add_argument("--candidate-id", default="4744211")
    parser.add_argument("--position-spec", default="Spec-2602-214NA")
    parser.add_argument("--output", default=None,
                        help="Path to write JSON output")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    output = asyncio.run(
        run_workflow(args.candidate_id, args.position_spec)
    )

    print(json.dumps(output, indent=2))

    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2))
        log.info("Output written to %s", args.output)

    # Exit non-zero on workflow error so CI fails properly
    if output["result"].get("error"):
        exit(1)
