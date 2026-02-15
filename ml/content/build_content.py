from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
from scipy.sparse import save_npz
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy import select

from ml.config import ARTIFACTS_DIR
from ml.db import get_engine, init_db, movielens_tmdb_map, tmdb_movies


def build_vectorizer(max_features: int | None, min_df: int) -> TfidfVectorizer:
    return TfidfVectorizer(max_features=max_features, min_df=min_df)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build content TF-IDF matrix")
    parser.add_argument("--max-features", type=int, default=50000)
    parser.add_argument("--min-df", type=int, default=2)
    args = parser.parse_args()

    engine = get_engine()
    init_db(engine)

    stmt = (
        select(
            movielens_tmdb_map.c.movielens_movie_id,
            movielens_tmdb_map.c.tmdb_id,
            tmdb_movies.c.content_text,
        )
        .join(tmdb_movies, movielens_tmdb_map.c.tmdb_id == tmdb_movies.c.tmdb_id)
        .where(tmdb_movies.c.content_text.isnot(None))
    )

    movie_ids: list[int] = []
    tmdb_ids: list[int] = []
    content_texts: list[str] = []

    with engine.begin() as conn:
        for row in conn.execute(stmt):
            movie_ids.append(int(row.movielens_movie_id))
            tmdb_ids.append(int(row.tmdb_id))
            content_texts.append(row.content_text or "")

    if not movie_ids:
        raise RuntimeError("No TMDB content_text records found. Run ingest_tmdb first.")

    vectorizer = build_vectorizer(args.max_features, args.min_df)
    matrix = vectorizer.fit_transform(content_texts)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    vectorizer_path = ARTIFACTS_DIR / "content_vectorizer.pkl"
    matrix_path = ARTIFACTS_DIR / "content_matrix.npz"
    index_path = ARTIFACTS_DIR / "content_index.json"

    joblib.dump(vectorizer, vectorizer_path)
    save_npz(matrix_path, matrix)

    with index_path.open("w", encoding="utf-8") as handle:
        json.dump({"movie_ids": movie_ids, "tmdb_ids": tmdb_ids}, handle)

    print("Saved vectorizer:", vectorizer_path)
    print("Saved matrix:", matrix_path)
    print("Saved index:", index_path)
    print("Rows:", len(movie_ids), "Features:", matrix.shape[1])


if __name__ == "__main__":
    main()
