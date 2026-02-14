from __future__ import annotations

import pickle
import csv
from pathlib import Path
from typing import Any

import numpy as np

from ml.config import DATA_DIR, MODEL_FILE


class CFRecommender:
    def __init__(self, model: dict[str, Any]) -> None:
        self.user_index: dict[str, int] = model["user_index"]
        self.item_index: dict[str, int] = model["item_index"]
        self.index_user: dict[int, str] = model["index_user"]
        self.index_item: dict[int, str] = model["index_item"]
        if "user_factors" in model and "item_factors" in model:
            self.user_factors: np.ndarray = model["user_factors"]
            self.item_factors: np.ndarray = model["item_factors"]
        else:
            u_mat: np.ndarray = model["U"]
            s_vals: np.ndarray = model["S"]
            v_mat: np.ndarray = model["Vt"]
            self.user_factors = u_mat * s_vals
            self.item_factors = v_mat
        self.user_means: np.ndarray = model["user_means"]
        self.item_means: np.ndarray = model["item_means"]
        self.global_mean: float = model["global_mean"]
        self.rated_items: dict[int, list[int]] = model.get("rated_items", {})
        self._movie_titles: dict[str, str] | None = None

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
        include_titles: bool = False,
    ) -> list[dict[str, float]]:
        if n <= 0:
            return []

        if user_id not in self.user_index:
            return self._cold_start(n)

        user_idx = self.user_index[user_id]
        scores = self.user_factors[user_idx] @ self.item_factors + self.user_means[user_idx]

        if exclude_rated:
            for item_idx in self.rated_items.get(user_idx, []):
                scores[item_idx] = -np.inf

        top_idx = self._top_indices(scores, n)
        titles = self._movie_titles if include_titles else None
        return [
            {
                "movie_id": self.index_item[item_idx],
                "score": float(scores[item_idx]),
                **(
                    {"title": titles.get(self.index_item[item_idx], "")}
                    if titles is not None
                    else {}
                ),
            }
            for item_idx in top_idx
        ]

    def _cold_start(self, n: int) -> list[dict[str, float]]:
        scores = np.array(self.item_means, dtype=np.float32)
        top_idx = self._top_indices(scores, n)
        return [
            {"movie_id": self.index_item[item_idx], "score": float(scores[item_idx])}
            for item_idx in top_idx
        ]

    def load_titles(self, movie_file: Path | None = None) -> None:
        path = movie_file or (DATA_DIR / "movie.csv")
        titles: dict[str, str] = {}
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                movie_id = (row.get("movieId") or "").strip()
                title = (row.get("title") or "").strip()
                if movie_id:
                    titles[movie_id] = title
        self._movie_titles = titles

    @staticmethod
    def _top_indices(scores: np.ndarray, n: int) -> list[int]:
        if scores.size == 0:
            return []
        n = min(n, scores.size)
        candidate_idx = np.argpartition(-scores, n - 1)[:n]
        return sorted(candidate_idx, key=lambda idx: scores[idx], reverse=True)
