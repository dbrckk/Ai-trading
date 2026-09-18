# Repo Brain

- Index mode: incremental
- Files indexed: 322
- Files reparsed this run: 0
- Symbols: 1289
- Internal import edges: 625
- Impacted files: 0
- Selected tests: 0

## Languages
- python: 320 files
- javascript: 2 files

## Highest-density symbol files
- src/ai_trading/cli.py: 42 symbols
- tests/test_hosted_persistence.py: 22 symbols
- tests/test_scheduler_endpoint.py: 22 symbols
- src/ai_trading/persistence.py: 21 symbols
- tests/test_paper_cycle_service.py: 20 symbols
- tests/test_dashboard_overview.py: 19 symbols
- tests/test_deployment_readiness.py: 17 symbols
- tests/test_dashboard_persistence.py: 16 symbols
- tests/test_paper_cycle.py: 15 symbols
- src/ai_trading/readiness_score.py: 14 symbols
- src/ai_trading/dashboard.py: 13 symbols
- tests/test_postgres_persistence.py: 13 symbols
- tests/test_runtime_persistence.py: 13 symbols
- src/ai_trading/champion_probation.py: 12 symbols
- tests/test_hosted_runtime.py: 12 symbols
- src/ai_trading/multiasset_runtime.py: 11 symbols
- src/ai_trading/multiasset_scheduler.py: 11 symbols
- src/ai_trading/resilience.py: 11 symbols
- tests/test_risk_governor.py: 11 symbols
- src/ai_trading/champions.py: 10 symbols

## Agent routing
- Read impact.json first after project/change context.
- Use selected-tests.json before broad validation.
- Search lookup.json for symbol routing; ast-grep enrichment may provide exact ranges.
- Verify source before editing.

## ast-grep enrichment
- ast-grep outline: available
- AST index mode: incremental
- AST files reparsed this run: 0
- outline files retained: 322
- top-level items retained: 2463
- direct members retained: 1288
- symbol shards: 25
- route named symbols via ast-routing.json, then fetch one ast-symbols/<initial>.json shard

