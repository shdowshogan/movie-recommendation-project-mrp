from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, create_engine
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

movielens_tmdb_map = Table(
    "movielens_tmdb_map",
    metadata,
    Column("movielens_movie_id", Integer, primary_key=True),
    Column("tmdb_id", Integer, nullable=False, unique=True),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow),
)

tmdb_movies = Table(
    "tmdb_movies",
    metadata,
    Column("tmdb_id", Integer, primary_key=True),
    Column("title", Text, nullable=False),
    Column("release_date", String(16)),
    Column("genres", JSONB, nullable=False, default=list),
    Column("cast", JSONB, nullable=False, default=list),
    Column("director", Text),
    Column("keywords", JSONB, nullable=False, default=list),
    Column("overview", Text),
    Column("content_text", Text),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow),
)


def get_db_url() -> str:
    db_url = os.getenv("MLR_DB_URL")
    if not db_url:
        raise RuntimeError("MLR_DB_URL is not set")
    return db_url


def get_engine(db_url: str | None = None):
    return create_engine(db_url or get_db_url(), future=True)


def init_db(engine) -> None:
    metadata.create_all(engine)
