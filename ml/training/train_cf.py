from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

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


def build_matrix(
    ratings: list[tuple[str, str, float]],
    user_index: dict[str, int],
    item_index: dict[str, int],
) -> tuple[np.ndarray, np.ndarray, dict[int, set[int]]]:
    num_users = len(user_index)
    num_items = len(item_index)
    matrix = np.zeros((num_users, num_items), dtype=np.float32)
    mask = np.zeros((num_users, num_items), dtype=bool)
    rated_items: dict[int, set[int]] = {}

    for user_id, movie_id, rating in ratings:
        u_idx = user_index[user_id]
        i_idx = item_index[movie_id]
        matrix[u_idx, i_idx] = rating
        mask[u_idx, i_idx] = True
        rated_items.setdefault(u_idx, set()).add(i_idx)

    return matrix, mask, rated_items


def compute_means(matrix: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    num_users, num_items = matrix.shape
    user_means = np.zeros(num_users, dtype=np.float32)
    item_means = np.zeros(num_items, dtype=np.float32)

    rating_sum = float(matrix[mask].sum())
    rating_count = int(mask.sum())
    global_mean = rating_sum / rating_count if rating_count else 0.0

    for u_idx in range(num_users):
        if mask[u_idx].any():
            user_means[u_idx] = matrix[u_idx][mask[u_idx]].mean()
        else:
            user_means[u_idx] = global_mean

    for i_idx in range(num_items):
        if mask[:, i_idx].any():
            item_means[i_idx] = matrix[:, i_idx][mask[:, i_idx]].mean()
        else:
            item_means[i_idx] = global_mean

    return user_means, item_means, global_mean


def train_svd(
    matrix: np.ndarray,
    mask: np.ndarray,
    rank: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    user_means, _item_means, _global_mean = compute_means(matrix, mask)
    centered = matrix - user_means[:, None]
    centered[~mask] = 0.0

    u_mat, s_vals, v_mat = np.linalg.svd(centered, full_matrices=False)
    k = min(rank, s_vals.shape[0])
    return (
        u_mat[:, :k].astype(np.float32),
        s_vals[:k].astype(np.float32),
        v_mat[:k, :].astype(np.float32),
    )


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
    matrix, mask, rated_items = build_matrix(ratings, user_index, item_index)
    user_means, item_means, global_mean = compute_means(matrix, mask)
    u_mat, s_vals, v_mat = train_svd(matrix, mask, SVD_RANK)

    index_user = {idx: user_id for user_id, idx in user_index.items()}
    index_item = {idx: movie_id for movie_id, idx in item_index.items()}
    rated_items_serializable = {idx: sorted(items) for idx, items in rated_items.items()}

    model = {
        "user_index": user_index,
        "item_index": item_index,
        "index_user": index_user,
        "index_item": index_item,
        "U": u_mat,
        "S": s_vals,
        "Vt": v_mat,
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
