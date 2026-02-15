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
            user_id = (row.get("user_id") or row.get("userId") or "").strip()
            movie_id = (row.get("movie_id") or row.get("movieId") or "").strip()
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


def load_movies_csv(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Movies file not found: {path}")

    titles: dict[str, str] = {}
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("movies.csv must include a header row")
        for row in reader:
            movie_id = (row.get("movie_id") or row.get("movieId") or "").strip()
            title = (row.get("title") or "").strip()
            if movie_id:
                titles[movie_id] = title

    return titles


def get_user_ratings(
    user_id: str,
    ratings_path: Path,
    movies_path: Path,
    limit: int | None = 20,
) -> list[dict[str, object]]:
    ratings = load_ratings_csv(ratings_path)
    titles = load_movies_csv(movies_path)

    rows = [row for row in ratings if row[0] == user_id]
    rows.sort(key=lambda item: item[2], reverse=True)
    if limit is not None:
        rows = rows[:limit]

    return [
        {
            "movie_id": movie_id,
            "rating": rating,
            "title": titles.get(movie_id, ""),
        }
        for _user_id, movie_id, rating in rows
    ]
