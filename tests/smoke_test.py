"""
Smoke test — verifies all agents respond after deployment.
Used in CI/CD deploy pipeline.
"""

import asyncio
import argparse
import sys
import logging

from pipeline.foundry_client import call_foundry_agent

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

AGENTS = [
    "requirement-extractor-agent",
    "doc-bio-matching-agent",
    "doc-resume-matching-agent",
    "doc-reference-matching-agent",
    "match-scoring-agent",
    "output-formatting-agent",
]


async def smoke_test_agent(agent_name: str, candidate_id: str, role: str) -> bool:
    try:
        result = await call_foundry_agent(agent_name, {
            "candidate_id": candidate_id,
            "role": role,
        })
        if result:
            log.info("✅ %s — OK", agent_name)
            return True
        else:
            log.error("❌ %s — Empty response", agent_name)
            return False
    except Exception as e:
        log.error("❌ %s — Error: %s", agent_name, str(e))
        return False


async def main(candidate_id: str, position_spec: str):
    log.info("Running smoke tests against %d agents...", len(AGENTS))

    results = await asyncio.gather(
        *[smoke_test_agent(a, candidate_id, position_spec) for a in AGENTS]
    )

    passed = sum(results)
    total = len(results)

    log.info("Smoke test results: %d/%d passed", passed, total)

    if passed < total:
        log.error("Smoke test FAILED — %d agents did not respond", total - passed)
        sys.exit(1)

    log.info("All agents healthy ✅")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", default="4744211")
    parser.add_argument("--position-spec", default="Spec-2602-214NA")
    args = parser.parse_args()

    asyncio.run(main(args.candidate_id, args.position_spec))
