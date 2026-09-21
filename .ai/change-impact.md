# Change impact

Base: 50438766084503b1667896fce1337935cc6e1f69
Head: e3ec0bfb17445d07e0bad60ae56f36da333f131c

## Changed files
- M src/ai_trading/broker.py
- M src/ai_trading/paper_execution.py
- M src/ai_trading/performance_metrics.py
- M src/ai_trading/postgres_persistence.py
- M src/ai_trading/runtime.py
- M src/ai_trading/runtime_state.py
- M src/ai_trading/trade_journal.py
- M tests/test_performance_metrics.py
- M tests/test_postgres_persistence.py
- A tests/test_realized_pnl_accounting.py

## Affected areas
- src
- tests

## Related test candidates
- tests/test_broker.py
- tests/test_paper_execution.py
- tests/test_performance_metrics.py
- tests/test_postgres_persistence.py
- tests/test_runtime.py
- tests/test_runtime_state.py

## Agent guidance
- Read this file before broad repository exploration.
- Inspect only the affected areas first.
- Use .ai/commands.json to choose validation commands.
- Expand scope only if the change crosses module boundaries or tests fail.
