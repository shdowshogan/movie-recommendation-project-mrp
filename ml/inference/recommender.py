from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np

from ml.config import MODEL_FILE


class CFRecommender:
    def __init__(self, model: dict[str, Any]) -> None:
        self.user_index: dict[str, int] = model["user_index"]
        self.item_index: dict[str, int] = model["item_index"]
        self.index_user: dict[int, str] = model["index_user"]
        self.index_item: dict[int, str] = model["index_item"]
        self.U: np.ndarray = model["U"]
        self.S: np.ndarray = model["S"]
        self.Vt: np.ndarray = model["Vt"]
        self.user_means: np.ndarray = model["user_means"]
        self.item_means: np.ndarray = model["item_means"]
        self.global_mean: float = model["global_mean"]
        self.rated_items: dict[int, list[int]] = model.get("rated_items", {})

    @classmethod
    def load(cls, model_path: Path = MODEL_FILE) -> "CFRecommender":
        with model_path.open("rb") as handle:
            model = pickle.load(handle)
        return cls(model)

    def recommend(
        self,
        user_id: str,
        n: int = 10,
        exclude_rated: bool = True,
    ) -> list[dict[str, float]]:
        if n <= 0:
            return []

        if user_id not in self.user_index:
            return self._cold_start(n)

        user_idx = self.user_index[user_id]
        user_vec = self.U[user_idx] * self.S
        scores = user_vec @ self.Vt + self.user_means[user_idx]

        if exclude_rated:
            for item_idx in self.rated_items.get(user_idx, []):
                scores[item_idx] = -np.inf

        top_idx = self._top_indices(scores, n)
        return [
            {"movie_id": self.index_item[item_idx], "score": float(scores[item_idx])}
            for item_idx in top_idx
        ]

    def _cold_start(self, n: int) -> list[dict[str, float]]:
        scores = np.array(self.item_means, dtype=np.float32)
        top_idx = self._top_indices(scores, n)
        return [
            {"movie_id": self.index_item[item_idx], "score": float(scores[item_idx])}
            for item_idx in top_idx
        ]

    @staticmethod
    def _top_indices(scores: np.ndarray, n: int) -> list[int]:
        if scores.size == 0:
            return []
        n = min(n, scores.size)
        candidate_idx = np.argpartition(-scores, n - 1)[:n]
        return sorted(candidate_idx, key=lambda idx: scores[idx], reverse=True)
