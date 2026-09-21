# Repo Brain

- Index mode: incremental
- Files indexed: 345
- Files reparsed this run: 3
- Symbols: 1541
- Internal import edges: 1136
- Impacted files: 10
- Selected tests: 7

## Languages
- python: 343 files
- javascript: 2 files

## Highest-density symbol files
- src/ai_trading/cli.py: 42 symbols
- tests/test_paper_cycle.py: 38 symbols
- tests/test_dashboard_overview.py: 37 symbols
- tests/test_paper_cycle_service.py: 33 symbols
- tests/test_dashboard_persistence.py: 25 symbols
- src/ai_trading/persistence.py: 24 symbols
- tests/test_hosted_persistence.py: 22 symbols
- tests/test_scheduler_endpoint.py: 22 symbols
- tests/test_deployment_readiness.py: 17 symbols
- tests/test_multi_market.py: 17 symbols
- src/ai_trading/dashboard.py: 16 symbols
- src/ai_trading/mtf_parameter_benchmark.py: 16 symbols
- tests/test_runtime_persistence.py: 16 symbols
- src/ai_trading/postgres_persistence.py: 15 symbols
- tests/test_mtf_shadow_challenger.py: 15 symbols
- tests/test_postgres_persistence.py: 15 symbols
- src/ai_trading/readiness_score.py: 14 symbols
- tests/test_hosted_runtime.py: 14 symbols
- src/ai_trading/file_persistence.py: 13 symbols
- src/ai_trading/runtime.py: 13 symbols

## Agent routing
- Read impact.json first after project/change context.
- Use selected-tests.json before broad validation.
- Search lookup.json for symbol routing; ast-grep enrichment may provide exact ranges.
- Verify source before editing.

## ast-grep enrichment
- ast-grep outline: available
- AST index mode: incremental
- AST files reparsed this run: 3
- outline files retained: 345
- top-level items retained: 2785
- direct members retained: 1445
- symbol shards: 25
- route named symbols via ast-routing.json, then fetch one ast-symbols/<initial>.json shard

