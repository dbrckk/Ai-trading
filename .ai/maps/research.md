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
mtf-prospective-evaluation-2026-10-26-v1.json
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

## File: mtf-prospective-evaluation-2026-10-26-v1.json
```json
{
  "schema_version": 1,
  "study_id": "mtf-prospective-evaluation-2026-10-26-v1",
  "registered_utc_date": "2026-10-25",
  "linked_capture_study_id": "mtf-prospective-2026-10-26-v1",
  "linked_capture_registration_sha256": "7b8870cce74d7941ed6e3f3c33e0829cd28b2d92f32d11ab5ca8309daf48b096",
  "observation_start_utc": "2026-10-26T00:00:00+00:00",
  "evaluation_end_exclusive_utc": "2027-01-24T00:00:00+00:00",
  "symbols": [
    "GC=F",
    "^GDAXI",
    "BTC-USD"
  ],
  "fixed_comparators": [
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
  "study_objectives": [
    "audit_capture_integrity_and_temporal_continuity",
    "assess_frozen_comparators_only_if_genuine_pre_outcome_predictions_exist",
    "avoid_retrospective_selection_or_promotion"
  ],
  "evaluation_data_requirements": {
    "archive_provenance": "registration_hash_and_independent_ohlcv_rehash_verified",
    "bars": "5m_adjusted_ohlcv_acquired_after_completion_lag",
    "minimum_completed_bars_per_symbol": 2000,
    "minimum_distinct_utc_capture_dates_per_symbol": 20,
    "predictions": "durably_timestamped_before_next_bar_entry_and_before_horizon_outcome",
    "minimum_matured_predictions_per_symbol": 500,
    "minimum_nonoverlapping_hypothetical_trades_per_symbol": 30,
    "complete_market_coverage_required": true,
    "missing_or_revised_bars": "report_explicitly_no_silent_backfill_or_unlabeled_revisions",
    "provider_session_gaps": "report_separately_from_bad_or_missing_market_data"
  },
  "primary_readouts": [
    "net_return_per_market_after_frozen_assumed_costs",
    "shared_capital_net_return_after_costs",
    "shared_capital_max_drawdown",
    "nonoverlapping_trade_count_and_market_coverage"
  ],
  "secondary_readouts": [
    "directional_accuracy",
    "active_signal_precision",
    "brier_score",
    "market_data_revision_and_gap_rate"
  ],
  "paper_execution_assumptions": {
    "transaction_cost_bps_per_side": 2,
    "slippage_bps_per_side": 1,
    "entry_price": "next_5m_bar_open_only_after_pre_outcome_signal",
    "exit_price": "horizon_bar_close",
    "no_overlapping_positions_within_market": true,
    "starting_paper_cash": 100000,
    "per_market_target_notional_fraction": 0.1,
    "shared_gross_exposure_limit_fraction": 0.3,
    "position_size_definition": "normalized_price_proxy_not_broker_contract_notional",
    "currency_conversion_funding_spread_market_impact_and_contract_multipliers": "not_modeled_not_live_eligible"
  },
  "review_gates": {
    "requires_all_three_market_data_quality": true,
    "requires_contemporaneous_prehorizon_prediction_evidence": true,
    "requires_positive_after_costs_result_in_each_market": true,
    "requires_positive_after_costs_shared_portfolio": true,
    "requires_complete_90_calendar_day_window": true,
    "allows_live_broker_activation": false,
    "allows_automatic_model_promotion": false,
    "consequence_if_gate_fails": "inconclusive_or_negative_no_promotion"
  },
  "invalid_evidence": [
    "predictions_reconstructed_after_target_maturity",
    "selection_on_prospective_observations",
    "model_fitted_or_tuned_using_archived_prospective_bars",
    "historical_walk_forward_replay_relabelled_as_forward_logged",
    "ohlcv_only_claimed_as_predictive_model_performance",
    "unverified_or_missing_archives",
    "provider_revisions_silently_overwritten"
  ],
  "operational_constraints": {
    "capture_registration_unchanged": true,
    "capture_is_data_only": true,
    "retention_days_for_github_actions_artifacts": 90,
    "long_term_artifact_persistence": "not_established_must_verify_before_final_review",
    "paper_only": true,
    "live_broker_enabled": false
  },
  "decision_status": "no_comparator_promoted; no_prior_historical_candidate_qualified",
  "protocol_changes": "versioned_new_study_only_never_rewrite_this_pre_observation_registration"
}
```
