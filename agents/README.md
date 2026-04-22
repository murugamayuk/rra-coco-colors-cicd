# Agents

Agents for this project are managed directly in **Azure AI Foundry**, 
not as code in this repository.

Workflow: `document-workflow-v2` in project `proj-default` 
(resource group `rg-mayuksacred-5599`).

To edit agents:
1. Go to https://ai.azure.com
2. Select project `proj-default`
3. Build → Workflows → document-workflow-v2

Future direction: if we move to agent-as-code, specs would go here 
(e.g. `requirement-parser-v2.yaml`) and `pipeline/deploy_agents.py` 
would apply them via the Foundry REST API.
