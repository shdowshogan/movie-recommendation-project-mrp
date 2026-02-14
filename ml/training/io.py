from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


def load_ratings_csv(path: Path) -> list[tuple[str, str, float]]:
    ratings: list[tuple[str, str, float]] = []
    if not path.exists():
        raise FileNotFoundError(f"Ratings file not found: {path}")

    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("ratings.csv must include a header row")
        for row in reader:
            user_id = (row.get("user_id") or "").strip()
            movie_id = (row.get("movie_id") or "").strip()
            rating_raw = (row.get("rating") or "").strip()
            if not user_id or not movie_id or not rating_raw:
                continue
            try:
                rating = float(rating_raw)
            except ValueError:
                continue
            ratings.append((user_id, movie_id, rating))

    return ratings


def filter_sparse_users(
    ratings: Iterable[tuple[str, str, float]],
    min_ratings: int,
) -> list[tuple[str, str, float]]:
    if min_ratings <= 1:
        return list(ratings)

    counts: dict[str, int] = {}
    for user_id, _movie_id, _rating in ratings:
        counts[user_id] = counts.get(user_id, 0) + 1

    return [row for row in ratings if counts[row[0]] >= min_ratings]
