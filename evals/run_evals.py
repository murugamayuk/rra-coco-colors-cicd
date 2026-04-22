"""Real evaluation gate — runs the full pipeline and validates output."""

import argparse
import asyncio
import json
import os
import sys

# Make pipeline/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))


async def run_eval(candidate_id: str, position_spec: str) -> dict:
    """Invoke the real pipeline — same entrypoint CI uses in production."""
    from main import run_workflow  # noqa: E402
    return await run_workflow(candidate_id, position_spec)


def check_thresholds(result: dict, args) -> list:
    """Return list of threshold breaches. Empty = all good."""
    # The new main.py returns:
    # {
    #   "candidate_id": ...,
    #   "result": {
    #     "agent": "document-workflow-v2",
    #     "output": { ... workflow response ... }   # or str
    #   },
    #   ...
    # }
    output = result.get("result", {}).get("output", {})
    if isinstance(output, str):
        return ["⚠️  Workflow output is a string, not structured JSON — cannot check thresholds"]
    if not isinstance(output, dict):
        return [f"⚠️  Workflow output is {type(output).__name__}, expected dict"]

    # Try common metrics paths — adjust when you see the real schema
    metrics = (
        output.get("metrics")
        or output.get("score", {}).get("metrics") if isinstance(output.get("score"), dict) else None
        or output.get("evaluation", {}).get("metrics") if isinstance(output.get("evaluation"), dict) else None
        or {}
    )

    if not metrics:
        return ["⚠️  No metrics dict found in workflow output — check output-agent schema"]

    breaches = []
    checks = [
        ("groundedness",    args.threshold_groundedness),
        ("task_completion", args.threshold_task_completion),
        ("relevance",       args.threshold_relevance),
    ]

    for metric_name, threshold in checks:
        value = metrics.get(metric_name)
        if value is None:
            breaches.append(f"⚠️  {metric_name}: MISSING from result")
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            breaches.append(f"⚠️  {metric_name}: non-numeric value {value!r}")
            continue
        if value < threshold:
            breaches.append(
                f"❌ {metric_name}: {value:.2f} < threshold {threshold:.2f}"
            )
        else:
            print(f"✅ {metric_name}: {value:.2f} >= {threshold:.2f}")

    return breaches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--candidate-id", default="4744211")
    parser.add_argument("--position-spec", default="Spec-2602-214NA")
    parser.add_argument("--threshold-groundedness",    type=float, default=0.8)
    parser.add_argument("--threshold-task-completion", type=float, default=0.9)
    parser.add_argument("--threshold-relevance",       type=float, default=0.8)
    parser.add_argument("--fail-on-breach", action="store_true")
    parser.add_argument("--output", default=None)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    endpoint = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
    api_key  = os.getenv("FOUNDRY_API_KEY")

    if not endpoint or not api_key:
        print("⏭️  PROJECT_ENDPOINT and FOUNDRY_API_KEY not set — skipping live eval")
        sys.exit(0)

    # Normalize env for downstream (foundry_client.py)
    os.environ["PROJECT_ENDPOINT"] = endpoint
    os.environ.setdefault("FOUNDRY_PROJECT_NAME", "proj-default")

    print(f"🚀 Running live eval")
    print(f"   endpoint = {endpoint[:60]}...")
    print(f"   project  = {os.environ['FOUNDRY_PROJECT_NAME']}")
    print(f"   candidate={args.candidate_id}  spec={args.position_spec}")

    try:
        result = asyncio.run(run_eval(args.candidate_id, args.position_spec))
    except Exception as e:
        print(f"❌ Pipeline failed: {type(e).__name__}: {e}")
        sys.exit(1)

    # Write output BEFORE checking errors, so debugging is always possible
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"💾 Result written to {args.output}")

    snippet = json.dumps(result, indent=2)
    print("📊 Eval result (first 600 chars):")
    print(snippet[:600])

    # Detect HTTP-level workflow failure from foundry_client.py
    inner = result.get("result", {})
    if isinstance(inner, dict) and inner.get("error"):
        print(f"\n🚨 Workflow invocation failed:")
        print(f"   status: {inner.get('status')}")
        print(f"   url:    {inner.get('url', 'n/a')}")
        print(f"   output: {inner.get('output', 'n/a')[:300]}")
        sys.exit(1)

    # Threshold gating
    breaches = check_thresholds(result, args)
    if breaches:
        print("\n🚨 Threshold issues:")
        for b in breaches:
            print(f"  {b}")
        if args.fail_on_breach:
            sys.exit(1)

    print("\n✅ Eval complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
