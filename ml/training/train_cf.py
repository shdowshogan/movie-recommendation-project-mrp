from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

from ml.config import ARTIFACTS_DIR, MODEL_FILE, MIN_RATINGS_PER_USER, RATINGS_FILE, SVD_RANK
from ml.training.io import filter_sparse_users, load_ratings_csv


def build_mappings(
    ratings: list[tuple[str, str, float]],
) -> tuple[dict[str, int], dict[str, int]]:
    user_index: dict[str, int] = {}
    item_index: dict[str, int] = {}

    for user_id, movie_id, _rating in ratings:
        if user_id not in user_index:
            user_index[user_id] = len(user_index)
        if movie_id not in item_index:
            item_index[movie_id] = len(item_index)

    return user_index, item_index


def build_sparse_matrix(
    ratings: list[tuple[str, str, float]],
    user_index: dict[str, int],
    item_index: dict[str, int],
) -> tuple[csr_matrix, np.ndarray, np.ndarray, np.ndarray, dict[int, set[int]]]:
    num_users = len(user_index)
    num_items = len(item_index)
    rows = np.empty(len(ratings), dtype=np.int32)
    cols = np.empty(len(ratings), dtype=np.int32)
    data = np.empty(len(ratings), dtype=np.float32)
    rated_items: dict[int, set[int]] = {}

    for idx, (user_id, movie_id, rating) in enumerate(ratings):
        u_idx = user_index[user_id]
        i_idx = item_index[movie_id]
        rows[idx] = u_idx
        cols[idx] = i_idx
        data[idx] = rating
        rated_items.setdefault(u_idx, set()).add(i_idx)

    matrix = csr_matrix((data, (rows, cols)), shape=(num_users, num_items))
    return matrix, rows, cols, data, rated_items


def compute_means(
    rows: np.ndarray,
    cols: np.ndarray,
    data: np.ndarray,
    num_users: int,
    num_items: int,
) -> tuple[np.ndarray, np.ndarray, float]:
    rating_count = int(data.size)
    global_mean = float(data.mean()) if rating_count else 0.0

    user_sum = np.bincount(rows, weights=data, minlength=num_users).astype(np.float32)
    user_count = np.bincount(rows, minlength=num_users).astype(np.float32)
    user_means = np.full(num_users, global_mean, dtype=np.float32)
    np.divide(user_sum, user_count, out=user_means, where=user_count > 0)

    item_sum = np.bincount(cols, weights=data, minlength=num_items).astype(np.float32)
    item_count = np.bincount(cols, minlength=num_items).astype(np.float32)
    item_means = np.full(num_items, global_mean, dtype=np.float32)
    np.divide(item_sum, item_count, out=item_means, where=item_count > 0)

    return user_means, item_means, global_mean


def train_svd(
    matrix: csr_matrix,
    rows: np.ndarray,
    cols: np.ndarray,
    data: np.ndarray,
    rank: int,
) -> tuple[np.ndarray, np.ndarray]:
    num_users, num_items = matrix.shape
    user_means, _item_means, _global_mean = compute_means(rows, cols, data, num_users, num_items)

    centered_data = data - user_means[rows]
    centered = csr_matrix((centered_data, (rows, cols)), shape=matrix.shape)

    max_rank = max(1, min(num_users, num_items) - 1)
    k = min(rank, max_rank)
    svd = TruncatedSVD(n_components=k, random_state=42)
    user_factors = svd.fit_transform(centered).astype(np.float32)
    item_factors = svd.components_.astype(np.float32)
    return user_factors, item_factors


def save_model(path: Path, model: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(model, handle)


def main() -> None:
    ratings = load_ratings_csv(RATINGS_FILE)
    ratings = filter_sparse_users(ratings, MIN_RATINGS_PER_USER)
    if not ratings:
        raise ValueError("No ratings available after filtering")

    user_index, item_index = build_mappings(ratings)
    matrix, rows, cols, data, rated_items = build_sparse_matrix(ratings, user_index, item_index)
    user_means, item_means, global_mean = compute_means(
        rows,
        cols,
        data,
        matrix.shape[0],
        matrix.shape[1],
    )
    user_factors, item_factors = train_svd(matrix, rows, cols, data, SVD_RANK)

    index_user = {idx: user_id for user_id, idx in user_index.items()}
    index_item = {idx: movie_id for movie_id, idx in item_index.items()}
    rated_items_serializable = {idx: sorted(items) for idx, items in rated_items.items()}

    model = {
        "user_index": user_index,
        "item_index": item_index,
        "index_user": index_user,
        "index_item": index_item,
        "user_factors": user_factors,
        "item_factors": item_factors,
        "user_means": user_means,
        "item_means": item_means,
        "global_mean": global_mean,
        "rated_items": rated_items_serializable,
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    save_model(MODEL_FILE, model)

    print("Saved model:", MODEL_FILE)
    print("Users:", len(user_index), "Items:", len(item_index))


if __name__ == "__main__":
    main()
