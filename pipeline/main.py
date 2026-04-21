"""
COCO COLORS — Concurrent Multi-Agent Candidate Scoring Pipeline
RRA APEX Platform · Mayuk.ai

Architecture:
  Step 0: requirement-extractor-agent (sequential)
  Step 1: bio + resume + reference agents (concurrent)
  Step 2: match-scoring-agent (sequential)
  Step 3: output-formatting-agent (sequential)
"""

import asyncio
import json
import logging
import sys
import argparse
from datetime import datetime
from pathlib import Path

from foundry_client import call_foundry_agent
from concurrent_builder import ConcurrentBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


# ── STAGE FUNCTIONS ───────────────────────────────────────────────────────────

async def run_requirement_extraction(candidate_id: str, role: str) -> dict:
    """Step 0 — Extract requirements from position spec (sequential)."""
    log.info("🔍 Extracting requirements for role: %s", role)
    return await call_foundry_agent(
        "requirement-extractor-agent",
        {
            "candidate_id": candidate_id,
            "role": role,
            "position_spec": role,
        }
    )


async def run_bio(candidate_id: str, role: str) -> dict:
    """Bio document scoring agent."""
    return await call_foundry_agent(
        "doc-bio-matching-agent",
        {
            "candidate_id": candidate_id,
            "role": role,
        }
    )


async def run_resume(candidate_id: str, role: str) -> dict:
    """Resume document scoring agent."""
    return await call_foundry_agent(
        "doc-resume-matching-agent",
        {
            "candidate_id": candidate_id,
            "role": role,
        }
    )


async def run_reference(candidate_id: str, role: str) -> dict:
    """Reference document scoring agent."""
    return await call_foundry_agent(
        "doc-reference-matching-agent",
        {
            "candidate_id": candidate_id,
            "role": role,
        }
    )


async def run_synth(results: dict, requirements: dict) -> dict:
    """Step 2 — Score synthesis (sequential)."""
    log.info("⚖️  Synthesizing scores...")
    return await call_foundry_agent(
        "match-scoring-agent",
        {
            "bio":          results["bio"],
            "resume":       results["resume"],
            "reference":    results["reference"],
            "requirements": requirements,
        }
    )


async def run_output_formatting(score: dict, candidate_id: str) -> dict:
    """Step 3 — Format final output (sequential)."""
    log.info("📄 Formatting output...")
    return await call_foundry_agent(
        "output-formatting-agent",
        {
            "candidate_id": candidate_id,
            "score":        score,
        }
    )


# ── MAIN WORKFLOW ─────────────────────────────────────────────────────────────

async def run_workflow(candidate_id: str, role: str) -> dict:
    """
    Full COCO COLORS pipeline:
    Extract → [Bio || Resume || Reference] → Score → Format
    """
    start = datetime.utcnow()
    log.info("🚀 Starting COCO COLORS pipeline | candidate=%s role=%s",
             candidate_id, role)

    # ── Step 0: Requirement extraction (sequential) ───────────────────────────
    requirements = await run_requirement_extraction(candidate_id, role)

    # ── Step 1: Concurrent document scoring ──────────────────────────────────
    log.info("⚡ Launching concurrent document agents...")
    concurrent = (
        ConcurrentBuilder()
        .add_task("bio",       lambda: run_bio(candidate_id, role))
        .add_task("resume",    lambda: run_resume(candidate_id, role))
        .add_task("reference", lambda: run_reference(candidate_id, role))
    )
    results = await concurrent.run()

    # ── Step 2: Score synthesis (sequential) ─────────────────────────────────
    score = await run_synth(results, requirements)

    # ── Step 3: Output formatting (sequential) ────────────────────────────────
    final = await run_output_formatting(score, candidate_id)

    elapsed = (datetime.utcnow() - start).total_seconds()
    log.info("✅ Pipeline complete in %.2fs", elapsed)

    return {
        "candidate_id":  candidate_id,
        "role":          role,
        "result":        final,
        "pipeline_ms":   int(elapsed * 1000),
        "timestamp":     start.isoformat(),
    }


# ── ENTRYPOINT ────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="COCO COLORS Pipeline")
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
