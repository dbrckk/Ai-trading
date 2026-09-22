# Repo Brain

- Index mode: incremental
- Files indexed: 359
- Files reparsed this run: 2
- Symbols: 1730
- Internal import edges: 1195
- Impacted files: 7
- Selected tests: 3

## Languages
- python: 357 files
- javascript: 2 files

## Highest-density symbol files
- tests/test_paper_cycle.py: 43 symbols
- src/ai_trading/cli.py: 42 symbols
- tests/test_dashboard_overview.py: 41 symbols
- tests/test_paper_cycle_service.py: 36 symbols
- tests/test_dashboard_persistence.py: 31 symbols
- src/ai_trading/persistence.py: 28 symbols
- tests/test_scheduler_endpoint.py: 28 symbols
- tests/test_hosted_persistence.py: 22 symbols
- src/ai_trading/dashboard.py: 21 symbols
- tests/test_multi_market.py: 21 symbols
- tests/test_postgres_persistence.py: 21 symbols
- src/ai_trading/postgres_persistence.py: 18 symbols
- src/ai_trading/mtf_parameter_benchmark.py: 17 symbols
- tests/test_deployment_readiness.py: 17 symbols
- src/ai_trading/file_persistence.py: 16 symbols
- tests/test_runtime_persistence.py: 16 symbols
- tests/test_mtf_shadow_challenger.py: 15 symbols
- src/ai_trading/readiness_score.py: 14 symbols
- tests/test_hosted_runtime.py: 14 symbols
- src/ai_trading/runtime.py: 13 symbols

## Agent routing
- Read impact.json first after project/change context.
- Use selected-tests.json before broad validation.
- Search lookup.json for symbol routing; ast-grep enrichment may provide exact ranges.
- Verify source before editing.

## ast-grep enrichment
- ast-grep outline: available
- AST index mode: incremental
- AST files reparsed this run: 2
- outline files retained: 359
- top-level items retained: 3032
- direct members retained: 1513
- symbol shards: 25
- route named symbols via ast-routing.json, then fetch one ast-symbols/<initial>.json shard

