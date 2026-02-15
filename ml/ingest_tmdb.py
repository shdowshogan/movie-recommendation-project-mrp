from __future__ import annotations

import argparse
import csv
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
from sqlalchemy.dialects.postgresql import insert

from ml.config import MOVIES_FILE
from ml.db import get_engine, init_db, movielens_tmdb_map, tmdb_movies
from ml.tmdb_client import TMDBClient


TITLE_YEAR_RE = re.compile(r"^(?P<title>.*)\s+\((?P<year>\d{4})\)$")


def _parse_title_year(raw_title: str) -> tuple[str, str | None]:
    match = TITLE_YEAR_RE.match(raw_title.strip())
    if not match:
        return raw_title.strip(), None
    return match.group("title").strip(), match.group("year")


def _iter_movies(path: Path) -> Iterable[tuple[int, str, str | None]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            movie_id_raw = (row.get("movieId") or row.get("movie_id") or "").strip()
            title_raw = (row.get("title") or "").strip()
            if not movie_id_raw or not title_raw:
                continue
            movie_id = int(movie_id_raw)
            title, year = _parse_title_year(title_raw)
            yield movie_id, title, year


def _build_content_text(bundle: dict[str, object]) -> str:
    parts = [
        str(bundle.get("title") or ""),
        " ".join(bundle.get("genres") or []),
        " ".join(bundle.get("cast") or []),
        str(bundle.get("director") or ""),
        " ".join(bundle.get("keywords") or []),
        str(bundle.get("overview") or ""),
    ]
    return " ".join(part for part in parts if part).strip().lower()


def ingest(limit: int | None, sleep_s: float) -> None:
    engine = get_engine()
    init_db(engine)
    client = TMDBClient.from_env()

    if not MOVIES_FILE.exists():
        raise FileNotFoundError(f"movies file not found: {MOVIES_FILE}")

    with engine.begin() as conn:
        existing_rows = list(conn.execute(movielens_tmdb_map.select()))
        mapped = {row.movielens_movie_id for row in existing_rows}
        mapped_tmdb = {row.tmdb_id for row in existing_rows}

    count = 0
    errors = 0
    for movie_id, title, year in _iter_movies(MOVIES_FILE):
        if movie_id in mapped:
            continue

        try:
            results = client.search_movie(title=title, year=year)
            if not results:
                continue

            tmdb_id = results[0].get("id")
            if not tmdb_id:
                continue
            if int(tmdb_id) in mapped_tmdb:
                continue

            bundle = client.fetch_movie_bundle(int(tmdb_id))
            content_text = _build_content_text(bundle)
        except requests.exceptions.RequestException as exc:
            errors += 1
            if errors % 10 == 1:
                print(f"TMDB request error (sample): {exc}")
            time.sleep(sleep_s)
            continue

        with engine.begin() as conn:
            movie_stmt = insert(tmdb_movies).values(
                tmdb_id=int(tmdb_id),
                title=bundle.get("title") or title,
                release_date=bundle.get("release_date"),
                genres=bundle.get("genres") or [],
                cast=bundle.get("cast") or [],
                director=bundle.get("director"),
                keywords=bundle.get("keywords") or [],
                overview=bundle.get("overview"),
                content_text=content_text,
                updated_at=datetime.now(timezone.utc),
            )
            movie_stmt = movie_stmt.on_conflict_do_update(
                index_elements=[tmdb_movies.c.tmdb_id],
                set_={
                    "title": movie_stmt.excluded.title,
                    "release_date": movie_stmt.excluded.release_date,
                    "genres": movie_stmt.excluded.genres,
                    "cast": movie_stmt.excluded.cast,
                    "director": movie_stmt.excluded.director,
                    "keywords": movie_stmt.excluded.keywords,
                    "overview": movie_stmt.excluded.overview,
                    "content_text": movie_stmt.excluded.content_text,
                    "updated_at": movie_stmt.excluded.updated_at,
                },
            )
            conn.execute(movie_stmt)

            map_stmt = insert(movielens_tmdb_map).values(
                movielens_movie_id=movie_id,
                tmdb_id=int(tmdb_id),
                updated_at=datetime.now(timezone.utc),
            )
            map_stmt = map_stmt.on_conflict_do_update(
                index_elements=[movielens_tmdb_map.c.movielens_movie_id],
                set_={
                    "tmdb_id": map_stmt.excluded.tmdb_id,
                    "updated_at": map_stmt.excluded.updated_at,
                },
            )
            conn.execute(map_stmt)
            mapped_tmdb.add(int(tmdb_id))

        count += 1
        if limit and count >= limit:
            break
        time.sleep(sleep_s)

    print(f"Ingested {count} movies (errors: {errors})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest TMDB metadata")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of movies")
    parser.add_argument("--sleep", type=float, default=0.25, help="Sleep between requests")
    args = parser.parse_args()

    ingest(limit=args.limit, sleep_s=args.sleep)


if __name__ == "__main__":
    main()
