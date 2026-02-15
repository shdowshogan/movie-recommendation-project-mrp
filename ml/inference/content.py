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
        profile = self.matrix[indices].mean(axis=0)
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
