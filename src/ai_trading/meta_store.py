from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .meta_router import MetaContext, ModelContextStats, context_key


class MetaRouterStore:
    def __init__(self, path: str | Path = "artifacts/meta_router.json") -> None:
        self.path = Path(path)

    def load(self) -> dict[str, dict[str, ModelContextStats]]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            ctx: {
                model: ModelContextStats(**stats)
                for model, stats in models.items()
            }
            for ctx, models in payload.items()
        }

    def save(self, data: dict[str, dict[str, ModelContextStats]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                {
                    ctx: {model: asdict(stats) for model, stats in models.items()}
                    for ctx, models in data.items()
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temp.replace(self.path)

    def update(
        self,
        context: MetaContext,
        model_name: str,
        *,
        correct: bool,
        edge: float,
    ) -> ModelContextStats:
        data = self.load()
        key = context_key(context)
        models = data.setdefault(key, {})
        current = models.get(model_name, ModelContextStats())
        updated = ModelContextStats(
            wins=current.wins + int(correct),
            losses=current.losses + int(not correct),
            cumulative_edge=current.cumulative_edge + float(edge),
        )
        models[model_name] = updated
        self.save(data)
        return updated

    def scores(self, context: MetaContext) -> dict[str, float]:
        data = self.load()
        models = data.get(context_key(context), {})
        return {name: stats.score for name, stats in models.items()}
