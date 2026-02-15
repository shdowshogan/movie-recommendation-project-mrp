from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from ml.inference.content import ContentRecommender
from ml.inference.recommender import CFRecommender


@dataclass
class HybridConfig:
    cf_weight: float = 0.7
    content_weight: float = 0.3
    candidate_k: int = 200


class HybridRecommender:
    def __init__(
        self,
        cf: CFRecommender,
        content: ContentRecommender,
        config: HybridConfig | None = None,
    ) -> None:
        self.cf = cf
        self.content = content
        self.config = config or HybridConfig()

    def recommend(
        self,
        user_id: str,
        n: int = 10,
        exclude_rated: bool = True,
    ) -> list[dict[str, float]]:
        scores = self.cf.score_items(user_id, exclude_rated=exclude_rated)
        if scores.size == 0:
            return []

        candidate_idx = self.cf.top_indices(scores, self.config.candidate_k)
        candidate_movie_ids = [int(self.cf.index_item[idx]) for idx in candidate_idx]

        profile = self._build_profile(user_id)
        if profile is None:
            return self._format_results(candidate_idx, scores, None)

        content_map = self.content.similarity_to_profile(profile, candidate_movie_ids)
        if not content_map:
            return self._format_results(candidate_idx, scores, None)

        content_scores = np.array(
            [content_map.get(mid, 0.0) for mid in candidate_movie_ids],
            dtype=np.float32,
        )
        content_scores = (content_scores + 1.0) / 2.0
        cf_norm = self._min_max(scores[candidate_idx])
        final_scores = (
            self.config.cf_weight * cf_norm
            + self.config.content_weight * content_scores
        )

        order = np.argsort(-final_scores)[:n]
        top_idx = [candidate_idx[i] for i in order]
        return self._format_results(top_idx, scores, final_scores[order])

    def _build_profile(self, user_id: str):
        if user_id not in self.cf.user_index:
            return None
        user_idx = self.cf.user_index[user_id]
        rated_items = self.cf.rated_items.get(user_idx, [])
        if not rated_items:
            return None
        movie_ids = [int(self.cf.index_item[item_idx]) for item_idx in rated_items]
        return self.content.profile_from_movie_ids(movie_ids)

    @staticmethod
    def _min_max(values: Iterable[float]) -> np.ndarray:
        arr = np.asarray(values, dtype=np.float32)
        if arr.size == 0:
            return arr
        min_val = float(arr.min())
        max_val = float(arr.max())
        if max_val == min_val:
            return np.ones_like(arr)
        return (arr - min_val) / (max_val - min_val)

    def _format_results(
        self,
        indices: list[int],
        cf_scores: np.ndarray,
        hybrid_scores: np.ndarray | None,
    ) -> list[dict[str, float]]:
        results = []
        for pos, idx in enumerate(indices):
            entry = {
                "movie_id": self.cf.index_item[idx],
                "cf_score": float(cf_scores[idx]),
            }
            if hybrid_scores is not None:
                entry["hybrid_score"] = float(hybrid_scores[pos])
            results.append(entry)
        return results
