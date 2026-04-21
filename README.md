# COCO COLORS — RRA Candidate Intelligence Pipeline

**Azure AI Foundry · Multi-Agent · Concurrent Execution · CI/CD**

Built by Murugesan Karmegam · RRA APEX Platform · April 2026

---

## Architecture

```
GitHub Push
    ↓
CI (lint → unit test → eval gate)
    ↓ passes
Deploy (terraform → agents → smoke test → integration test)
    ↓
Foundry Agents (mayuksacred Azure)
    ↓
requirement-extractor → [bio || resume || reference] → match-scoring → output-formatting
    ↓
Structured Scorecard (score, tier, decision, evidence)
```

## Pipeline Stages

| Stage | Agent | Mode | Latency |
|---|---|---|---|
| Requirement Extraction | requirement-extractor-agent | Sequential | ~3s |
| Bio Scoring | doc-bio-matching-agent | Concurrent | ~10s |
| Resume Scoring | doc-resume-matching-agent | Concurrent | ~10s |
| Reference Analysis | doc-reference-matching-agent | Concurrent | ~12s |
| Score Synthesis | match-scoring-agent | Sequential | ~5s |
| Output Formatting | output-formatting-agent | Sequential | ~3s |
| **Total** | | | **~18s** (vs ~46s sequential) |

## CI/CD Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | Every push/PR | Lint, unit tests, eval gate |
| `deploy.yml` | Merge to main | Terraform + agent deploy |
| `eval.yml` | Nightly 6am UTC | Full eval suite |

## Setup

### 1. GitHub Secrets Required

```
FOUNDRY_ENDPOINT       = https://rg-mayuk-agent-demo.services.ai.azure.com/api/projects/proj-default
FOUNDRY_API_KEY        = (from Azure AI Foundry)
AZURE_CLIENT_ID        = (app registration)
AZURE_TENANT_ID        = (Azure tenant)
AZURE_SUBSCRIPTION_ID  = (Azure subscription)
TF_STATE_RG            = rg-mayuksacred-5599
TF_STATE_SA            = (storage account for tf state)
SLACK_WEBHOOK_URL      = (optional — for notifications)
```

### 2. Run locally

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your values
python pipeline/main.py --candidate-id 4744211 --position-spec Spec-2602-214NA
```

### 3. Run evals

```bash
python evals/run_evals.py --dataset evals/datasets/simulated_v1.jsonl
```

## Simulated Data

One complete search lifecycle included:
- **Search:** PROJ-001 — CFO at Acme Capital Group
- **Candidate:** 4744211 — Susan Carter
- **Result:** Placed — Score 72/100 — Strong Yes

See `data/simulated/events/search-PROJ-001.json` for full lifecycle.

## Quality Gates

| Evaluator | CI Threshold | Nightly Threshold |
|---|---|---|
| Groundedness | ≥ 0.80 | ≥ 0.85 |
| TaskCompletion | ≥ 0.90 | ≥ 0.90 |
| Relevance | ≥ 0.80 | ≥ 0.85 |
| ScoringConsistency | ≥ 0.90 | ≥ 0.95 |
| HallucinationRate | ≤ 0.05 | ≤ 0.02 |
