from pathlib import Path

from ai_trading.replay import compare_replays, load_audit_events


def test_replay_comparison_is_deterministic_for_same_audit(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    path.write_text(
        '{"event":"runtime_step","payload":{"side":1}}\n'
        '{"event":"runtime_step","payload":{"side":0}}\n',
        encoding="utf-8",
    )
    events = load_audit_events(path, event_filter={"runtime_step"})
    report = compare_replays(events, list(events))
    assert report.deterministic
    assert report.compared_events == 2
