# Change impact

Base: 484dac0ae5efcfc25707122114b34f31038cd8ed
Head: d954a582630dd355c8ff744476a702ff62f825f1

## Changed files
- M src/ai_trading/dashboard.py
- M src/ai_trading/file_persistence.py
- A src/ai_trading/mtf_shadow_challenger.py
- A src/ai_trading/mtf_shadow_quality.py
- A src/ai_trading/multi_timeframe_features.py
- M src/ai_trading/operational_overview.py
- M src/ai_trading/paper_cycle.py
- M src/ai_trading/postgres_persistence.py
- M src/ai_trading/runtime.py
- M tests/test_dashboard_overview.py
- A tests/test_mtf_shadow_challenger.py
- A tests/test_mtf_shadow_quality.py
- M tests/test_multi_market.py
- A tests/test_multi_timeframe_features.py
- M tests/test_paper_cycle.py

## Affected areas
- src
- tests

## Related test candidates
- tests/test_dashboard.py
- tests/test_file_persistence.py
- tests/test_mtf_shadow_challenger.py
- tests/test_mtf_shadow_quality.py
- tests/test_multi_timeframe_features.py
- tests/test_paper_cycle.py
- tests/test_postgres_persistence.py
- tests/test_runtime.py

## Agent guidance
- Read this file before broad repository exploration.
- Inspect only the affected areas first.
- Use .ai/commands.json to choose validation commands.
- Expand scope only if the change crosses module boundaries or tests fail.
