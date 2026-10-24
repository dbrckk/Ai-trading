This file is a merged representation of a subset of the codebase, containing specifically included files and files not matching ignore patterns, combined into a single document by Repomix.
The content has been processed where content has been compressed (code blocks are separated by ⋮---- delimiter).

# File Summary

## Purpose
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Only files matching these patterns are included: **/*.{py,js,mjs,cjs,ts,tsx,jsx,java,kt,kts,gd,groovy,gradle,toml,json,yaml,yml,sql,sh}
- Files matching these patterns are excluded: .ai/**, **/node_modules/**, **/.gradle/**, **/build/**, **/dist/**, **/.venv/**, **/__pycache__/**, **/.pytest_cache/**, **/.git/**, **/coverage/**, **/*.lock, **/*.min.js, **/*.map, assets/**, art/**, art_sources/**, marketing/**, colab/**, kaggle/**, discovery-cache.json, health-snapshot.json, history.json
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Content has been compressed - code blocks are separated by ⋮---- delimiter
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
mtf-prospective-2026-10-26-v1.json
```

# Files

## File: mtf-prospective-2026-10-26-v1.json
```json
{
  "schema_version": 1,
  "study_id": "mtf-prospective-2026-10-26-v1",
  "registered_on_utc_date": "2026-10-23",
  "observation_start_utc": "2026-10-26T00:00:00+00:00",
  "data_provider": "yahoo_yfinance_auto_adjusted",
  "bar_interval": "5m",
  "bar_timestamp_semantics": "opening_timestamp_utc",
  "minimum_completion_lag_minutes": 15,
  "acquisition_window": "5d",
  "symbols": [
    "GC=F",
    "^GDAXI",
    "BTC-USD"
  ],
  "frozen_research_comparators": [
    {
      "horizon_bars": 9,
      "minimum_threshold": 0.0005,
      "atr_multiplier": 0.25,
      "max_train_rows": 1000,
      "min_confidence": 0.56
    },
    {
      "horizon_bars": 9,
      "minimum_threshold": 0.0005,
      "atr_multiplier": 0.25,
      "max_train_rows": 1000,
      "min_confidence": 0.6
    },
    {
      "horizon_bars": 18,
      "minimum_threshold": 0.0003,
      "atr_multiplier": 0.15,
      "max_train_rows": 1000,
      "min_confidence": 0.6
    }
  ],
  "hypothetical_costs_bps_per_side": {
    "transaction": 2,
    "slippage": 1
  },
  "permitted_actions": [
    "archive_provider_ohlcv",
    "fingerprint_completed_bars",
    "report_missing_data"
  ],
  "prohibited_actions": [
    "fit_or_tune_on_prospective_bars",
    "promote_model",
    "place_trade",
    "write_production_persistence"
  ],
  "decisions": "no_historical_candidate_qualified; prospective capture is observation-only",
  "prior_research_overlap": "none_of_the_new_bars_exist_before_cutoff_if_recorded_honestly",
  "risks": [
    "provider_may_revise_historical_bars",
    "artifact_retention_not_permanent",
    "asset_currency_and_contract_multipliers_not_modeled"
  ],
  "live_broker_enabled": false
}
```
