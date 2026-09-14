from ai_trading.expert_diversity import DiversityReport
from ai_trading.global_selection import evaluate_global_generation


def test_global_generation_requires_score_and_diversity() -> None:
    good = evaluate_global_generation(
        previous_score=0.8,
        current_score=0.9,
        diversity=DiversityReport(0.4, 0.2, True),
    )
    assert good.accept

    bad_diversity = evaluate_global_generation(
        previous_score=0.8,
        current_score=1.0,
        diversity=DiversityReport(0.95, 0.8, False),
    )
    assert not bad_diversity.accept

    bad_score = evaluate_global_generation(
        previous_score=0.8,
        current_score=0.7,
        diversity=DiversityReport(0.4, 0.2, True),
    )
    assert not bad_score.accept
