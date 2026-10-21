# Change impact

Base: 3c2bf9c1f06665e950c452e1a893d187bf9087dd
Head: 6f3fe1df3e49137e900d5a67a9a57d42f37d286c

## Changed files
- M docs/kronos-research.md
- M src/ai_trading/file_persistence.py
- M src/ai_trading/operational_overview.py
- M src/ai_trading/paper_cycle.py
- M src/ai_trading/postgres_persistence.py
- A src/ai_trading/river_v2_shadow.py
- M src/ai_trading/runtime.py
- M tests/test_dashboard_overview.py
- M tests/test_paper_cycle.py
- M tests/test_shadow_challenger.py
- M tests/test_shadow_quality.py

## Affected areas
- docs
- src
- tests

## Related test candidates
- tests/test_file_persistence.py
- tests/test_paper_cycle.py
- tests/test_postgres_persistence.py
- tests/test_runtime.py

## Agent guidance
- Read this file before broad repository exploration.
- Inspect only the affected areas first.
- Use .ai/commands.json to choose validation commands.
- Expand scope only if the change crosses module boundaries or tests fail.
