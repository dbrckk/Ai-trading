# Change impact

Base: a9187665403c5ca3f333c4bb6c75460208064305
Head: 53cf19eb161a2893475a793af4a5c339bf2b1370

## Changed files
- M .github/workflows/ci.yml
- M .github/workflows/cloudflare-paper-scheduler-deploy.yml
- M .github/workflows/mtf-parameter-benchmark.yml
- M .github/workflows/paper-cycle.yml
- M src/ai_trading/data.py
- M src/ai_trading/marginal_alpha.py
- M src/ai_trading/performance.py
- M tests/test_cloudflare_scheduler_deploy_workflow.py
- M tests/test_data.py
- M tests/test_performance.py

## Affected areas
- .github
- src
- tests

## Related test candidates
- tests/test_data.py
- tests/test_marginal_alpha.py
- tests/test_performance.py

## Agent guidance
- Read this file before broad repository exploration.
- Inspect only the affected areas first.
- Use .ai/commands.json to choose validation commands.
- Expand scope only if the change crosses module boundaries or tests fail.
