from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
from scipy.sparse import csr_matrix, load_npz
from sklearn.preprocessing import normalize

from ml.config import ARTIFACTS_DIR


class ContentRecommender:
    def __init__(self, matrix: csr_matrix, movie_ids: list[int]) -> None:
        self.matrix = matrix
        self.movie_ids = movie_ids
        self.movie_index = {movie_id: idx for idx, movie_id in enumerate(movie_ids)}
        self.matrix_norm = normalize(self.matrix, axis=1)

    @classmethod
    def load(
        cls,
        artifacts_dir: Path = ARTIFACTS_DIR,
    ) -> "ContentRecommender":
        matrix = load_npz(artifacts_dir / "content_matrix.npz")
        index_path = artifacts_dir / "content_index.json"
        with index_path.open("r", encoding="utf-8") as handle:
            index = json.load(handle)
        movie_ids = [int(mid) for mid in index.get("movie_ids", [])]
        return cls(matrix=matrix.tocsr(), movie_ids=movie_ids)

    def profile_from_movie_ids(self, movie_ids: Iterable[int]) -> csr_matrix | None:
        indices = [self.movie_index[mid] for mid in movie_ids if mid in self.movie_index]
        if not indices:
            return None
        profile = np.asarray(self.matrix[indices].mean(axis=0))
        return normalize(profile)

    def similarity_to_profile(
        self,
        profile: csr_matrix,
        candidate_movie_ids: Iterable[int],
    ) -> dict[int, float]:
        idx_list = [self.movie_index[mid] for mid in candidate_movie_ids if mid in self.movie_index]
        if not idx_list:
            return {}
        candidate_matrix = self.matrix_norm[idx_list]
        scores = candidate_matrix @ profile.T
        score_list = np.asarray(scores).ravel().astype(np.float32)
        movie_ids = [self.movie_ids[idx] for idx in idx_list]
        return {movie_id: float(score) for movie_id, score in zip(movie_ids, score_list)}

    def recommend_from_profile(
        self,
        profile: csr_matrix,
        n: int,
        exclude_movie_ids: Iterable[int] | None = None,
    ) -> list[dict[str, float]]:
        if n <= 0:
            return []

        scores = self.matrix_norm @ profile.T
        score_list = np.asarray(scores).ravel().astype(np.float32)

        if exclude_movie_ids:
            for movie_id in exclude_movie_ids:
                idx = self.movie_index.get(movie_id)
                if idx is not None:
                    score_list[idx] = -np.inf

        n = min(n, score_list.size)
        top_idx = np.argpartition(-score_list, n - 1)[:n]
        top_idx = sorted(top_idx, key=lambda idx: score_list[idx], reverse=True)

        return [
            {"movie_id": str(self.movie_ids[idx]), "content_score": float(score_list[idx])}
            for idx in top_idx
        ]
