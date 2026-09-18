# Change impact

Base: d1d4c4d5ae2b0ca11c66fabadd62828a5f8fc4da
Head: 9d450b886fb39efda0b341ede3fc8e444653954a

## Changed files
- M src/ai_trading/burnin.py
- M src/ai_trading/dashboard.py
- M src/ai_trading/file_persistence.py
- M src/ai_trading/operational_overview.py
- M src/ai_trading/persistence.py
- M src/ai_trading/postgres_persistence.py
- M tests/test_dashboard_overview.py
- M tests/test_dashboard_persistence.py
- A tests/test_durable_burnin_persistence.py

## Affected areas
- src
- tests

## Related test candidates
- tests/test_burnin.py
- tests/test_dashboard.py
- tests/test_file_persistence.py
- tests/test_persistence.py
- tests/test_postgres_persistence.py

## Agent guidance
- Read this file before broad repository exploration.
- Inspect only the affected areas first.
- Use .ai/commands.json to choose validation commands.
- Expand scope only if the change crosses module boundaries or tests fail.
