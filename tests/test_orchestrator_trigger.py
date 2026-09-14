from pathlib import Path

from ai_trading.audit import AuditLog
from ai_trading.config import RiskConfig
from ai_trading.orchestrator import AutonomousPaperOrchestrator
from ai_trading.runtime import PaperAutonomousRuntime
from ai_trading.runtime_state import RuntimeStateStore


def test_orchestrator_configuration_accepts_injected_runtime(tmp_path: Path) -> None:
    runtime = PaperAutonomousRuntime(
        risk_config=RiskConfig(),
        state_store=RuntimeStateStore(tmp_path / "state.json"),
        audit_log=AuditLog(tmp_path / "audit.jsonl"),
        online_model_path=tmp_path / "online.joblib",
        lock_path=tmp_path / "runtime.lock",
        learning_cycle_every_bars=1,
    )
    orchestrator = AutonomousPaperOrchestrator(
        runtime=runtime,
        learning_trials=1,
    )
    assert orchestrator.runtime is runtime
    assert orchestrator.learning_trials == 1
