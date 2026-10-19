# Change impact

Base: 4b54b4376c6a53a846fe6b27e39ccf143ad880ac
Head: fddfd942340c3d859390f2c391e64f2024f6c8c0

## Changed files
- M .github/workflows/paper-cycle.yml
- M README.md
- M infra/cloudflare-paper-scheduler/wrangler.toml
- M src/ai_trading/scheduler_endpoint.py
- A src/ai_trading/scheduler_fallback.py
- M tests/test_paper_cycle_workflow.py
- M tests/test_scheduler_endpoint.py

## Affected areas
- .github
- (root)
- infra
- src
- tests

## Related test candidates
- tests/test_scheduler_endpoint.py

## Agent guidance
- Read this file before broad repository exploration.
- Inspect only the affected areas first.
- Use .ai/commands.json to choose validation commands.
- Expand scope only if the change crosses module boundaries or tests fail.
