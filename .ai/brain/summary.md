# Repo Brain

- Index mode: incremental
- Files indexed: 341
- Files reparsed this run: 6
- Symbols: 1473
- Internal import edges: 1124
- Impacted files: 15
- Selected tests: 9

## Languages
- python: 339 files
- javascript: 2 files

## Highest-density symbol files
- src/ai_trading/cli.py: 42 symbols
- tests/test_dashboard_overview.py: 29 symbols
- tests/test_paper_cycle.py: 27 symbols
- tests/test_paper_cycle_service.py: 27 symbols
- tests/test_dashboard_persistence.py: 25 symbols
- src/ai_trading/persistence.py: 24 symbols
- tests/test_hosted_persistence.py: 22 symbols
- tests/test_scheduler_endpoint.py: 22 symbols
- tests/test_deployment_readiness.py: 17 symbols
- src/ai_trading/dashboard.py: 16 symbols
- tests/test_runtime_persistence.py: 16 symbols
- src/ai_trading/postgres_persistence.py: 15 symbols
- tests/test_multi_market.py: 15 symbols
- tests/test_postgres_persistence.py: 15 symbols
- src/ai_trading/readiness_score.py: 14 symbols
- tests/test_hosted_runtime.py: 14 symbols
- src/ai_trading/file_persistence.py: 13 symbols
- src/ai_trading/runtime.py: 13 symbols
- src/ai_trading/champion_probation.py: 12 symbols
- src/ai_trading/operational_overview.py: 12 symbols

## Agent routing
- Read impact.json first after project/change context.
- Use selected-tests.json before broad validation.
- Search lookup.json for symbol routing; ast-grep enrichment may provide exact ranges.
- Verify source before editing.

## ast-grep enrichment
- ast-grep outline: available
- AST index mode: incremental
- AST files reparsed this run: 6
- outline files retained: 341
- top-level items retained: 2718
- direct members retained: 1392
- symbol shards: 25
- route named symbols via ast-routing.json, then fetch one ast-symbols/<initial>.json shard

