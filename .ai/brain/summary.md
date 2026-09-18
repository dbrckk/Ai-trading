# Repo Brain

- Index mode: incremental
- Files indexed: 324
- Files reparsed this run: 9
- Symbols: 1315
- Internal import edges: 635
- Impacted files: 18
- Selected tests: 15

## Languages
- python: 322 files
- javascript: 2 files

## Highest-density symbol files
- src/ai_trading/cli.py: 42 symbols
- src/ai_trading/persistence.py: 23 symbols
- tests/test_hosted_persistence.py: 22 symbols
- tests/test_scheduler_endpoint.py: 22 symbols
- tests/test_dashboard_overview.py: 20 symbols
- tests/test_paper_cycle_service.py: 20 symbols
- tests/test_dashboard_persistence.py: 18 symbols
- tests/test_deployment_readiness.py: 17 symbols
- tests/test_paper_cycle.py: 15 symbols
- src/ai_trading/readiness_score.py: 14 symbols
- src/ai_trading/dashboard.py: 13 symbols
- tests/test_postgres_persistence.py: 13 symbols
- tests/test_runtime_persistence.py: 13 symbols
- src/ai_trading/champion_probation.py: 12 symbols
- src/ai_trading/postgres_persistence.py: 12 symbols
- tests/test_hosted_runtime.py: 12 symbols
- src/ai_trading/multiasset_runtime.py: 11 symbols
- src/ai_trading/multiasset_scheduler.py: 11 symbols
- src/ai_trading/resilience.py: 11 symbols
- tests/test_risk_governor.py: 11 symbols

## Agent routing
- Read impact.json first after project/change context.
- Use selected-tests.json before broad validation.
- Search lookup.json for symbol routing; ast-grep enrichment may provide exact ranges.
- Verify source before editing.

## ast-grep enrichment
- ast-grep outline: available
- AST index mode: incremental
- AST files reparsed this run: 9
- outline files retained: 324
- top-level items retained: 2511
- direct members retained: 1299
- symbol shards: 25
- route named symbols via ast-routing.json, then fetch one ast-symbols/<initial>.json shard

