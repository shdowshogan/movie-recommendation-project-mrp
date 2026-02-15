from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ml.inference.content import ContentRecommender
from ml.inference.hybrid import HybridConfig, HybridRecommender
from ml.inference.recommender import CFRecommender
from ml.db import get_engine, movielens_tmdb_map
from ml.tmdb_client import TMDBClient
from sqlalchemy import select
from sklearn.preprocessing import normalize

app = FastAPI(title="CineMind API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_MODEL: CFRecommender | None = None
_HYBRID: HybridRecommender | None = None
_TMDB: TMDBClient | None = None
_ENGINE = None
_POSTER_CACHE: dict[int, str | None] = {}


class Recommendation(BaseModel):
    movie_id: str
    score: float
    title: str | None = None


class HybridRecommendation(BaseModel):
    movie_id: str
    cf_score: float
    hybrid_score: float | None = None
    title: str | None = None
    poster_url: str | None = None


class RecommendationResponse(BaseModel):
    user_id: str
    results: list[Recommendation]


class SearchResult(BaseModel):
    tmdb_id: int
    title: str
    year: str | None = None
    poster_url: str | None = None


class SeedRequest(BaseModel):
    tmdb_ids: list[int]
    n: int = 10


class SeedRecommendation(BaseModel):
    movie_id: str
    content_score: float
    title: str | None = None
    poster_url: str | None = None


class SeedHybridRecommendation(BaseModel):
    movie_id: str
    content_score: float
    cf_score: float
    hybrid_score: float
    title: str | None = None
    poster_url: str | None = None


class SeedRecommendationResponse(BaseModel):
    results: list[SeedRecommendation]


class SeedHybridRecommendationResponse(BaseModel):
    results: list[SeedHybridRecommendation]


class HybridRecommendationResponse(BaseModel):
    user_id: str
    results: list[HybridRecommendation]


def _init_model() -> CFRecommender:
    model = CFRecommender.load()
    if os.getenv("INCLUDE_TITLES", "true").lower() in {"1", "true", "yes"}:
        model.load_titles()
    return model


def _init_hybrid(model: CFRecommender) -> HybridRecommender:
    content = ContentRecommender.load()
    config = HybridConfig(
        cf_weight=float(os.getenv("HYBRID_CF_WEIGHT", "0.7")),
        content_weight=float(os.getenv("HYBRID_CONTENT_WEIGHT", "0.3")),
        candidate_k=int(os.getenv("HYBRID_CANDIDATE_K", "200")),
    )
    return HybridRecommender(model, content, config)


def _poster_url_for_tmdb(tmdb_id: int) -> str | None:
    if tmdb_id in _POSTER_CACHE:
        return _POSTER_CACHE[tmdb_id]
    if _TMDB is None:
        return None
    try:
        details = _TMDB.movie_details(tmdb_id)
    except Exception:
        _POSTER_CACHE[tmdb_id] = None
        return None
    poster_path = details.get("poster_path")
    if not poster_path:
        _POSTER_CACHE[tmdb_id] = None
        return None
    url = f"https://image.tmdb.org/t/p/w342{poster_path}"
    _POSTER_CACHE[tmdb_id] = url
    return url


def _map_movielens_to_tmdb(movie_ids: list[str]) -> dict[str, int]:
    if _ENGINE is None:
        return {}
    int_ids = []
    for movie_id in movie_ids:
        try:
            int_ids.append(int(movie_id))
        except ValueError:
            continue
    if not int_ids:
        return {}
    with _ENGINE.begin() as conn:
        rows = conn.execute(
            select(
                movielens_tmdb_map.c.movielens_movie_id,
                movielens_tmdb_map.c.tmdb_id,
            ).where(movielens_tmdb_map.c.movielens_movie_id.in_(int_ids))
        )
        return {str(row.movielens_movie_id): int(row.tmdb_id) for row in rows}


@app.on_event("startup")
def load_model() -> None:
    global _MODEL, _HYBRID, _TMDB
    _MODEL = _init_model()
    _HYBRID = _init_hybrid(_MODEL)
    try:
        _TMDB = TMDBClient.from_env()
    except RuntimeError:
        _TMDB = None
    try:
        global _ENGINE
        _ENGINE = get_engine()
    except RuntimeError:
        _ENGINE = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tmdb/search", response_model=list[SearchResult])
def search_tmdb(
    query: str = Query(..., min_length=2),
    limit: int = Query(8, ge=1, le=20),
) -> list[SearchResult]:
    if _TMDB is None:
        raise HTTPException(status_code=503, detail="TMDB API key not configured")

    results = _TMDB.search_movie(title=query)
    payload: list[SearchResult] = []
    for item in results[:limit]:
        release_date = item.get("release_date") or ""
        year = release_date.split("-")[0] if release_date else None
        poster_path = item.get("poster_path")
        poster_url = (
            f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        )
        payload.append(
            SearchResult(
                tmdb_id=int(item.get("id")),
                title=item.get("title") or "",
                year=year,
                poster_url=poster_url,
            )
        )
    return payload


@app.post("/recommendations/seed", response_model=SeedRecommendationResponse)
def get_seed_recommendations(payload: SeedRequest) -> SeedRecommendationResponse:
    if _HYBRID is None or _MODEL is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if _ENGINE is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    if not payload.tmdb_ids:
        raise HTTPException(status_code=400, detail="tmdb_ids is required")

    mapped_tmdb_ids = set()
    with _ENGINE.begin() as conn:
        rows = conn.execute(
            select(
                movielens_tmdb_map.c.movielens_movie_id,
                movielens_tmdb_map.c.tmdb_id,
            ).where(movielens_tmdb_map.c.tmdb_id.in_(payload.tmdb_ids))
        )
        movielens_ids = []
        for row in rows:
            movielens_ids.append(int(row.movielens_movie_id))
            mapped_tmdb_ids.add(int(row.tmdb_id))

    missing_tmdb_ids = [mid for mid in payload.tmdb_ids if mid not in mapped_tmdb_ids]
    text_profile = None
    if missing_tmdb_ids:
        if _TMDB is None:
            raise HTTPException(status_code=503, detail="TMDB API key not configured")
        texts = []
        for tmdb_id in missing_tmdb_ids:
            bundle = _TMDB.fetch_movie_bundle(tmdb_id)
            text_parts = [
                str(bundle.get("title") or ""),
                " ".join(bundle.get("genres") or []),
                " ".join(bundle.get("cast") or []),
                str(bundle.get("director") or ""),
                " ".join(bundle.get("keywords") or []),
                str(bundle.get("overview") or ""),
            ]
            texts.append(" ".join(part for part in text_parts if part).strip().lower())
        text_profile = _HYBRID.content.profile_from_texts(texts)

    mapped_profile = _HYBRID.content.profile_from_movie_ids(movielens_ids)
    if mapped_profile is None and text_profile is None:
        raise HTTPException(status_code=404, detail="No content profile available")

    if mapped_profile is None:
        profile = text_profile
    elif text_profile is None:
        profile = mapped_profile
    else:
        profile = normalize(mapped_profile + text_profile)

    results = _HYBRID.content.recommend_from_profile(
        profile,
        n=payload.n,
        exclude_movie_ids=movielens_ids,
    )

    if _MODEL._movie_titles is not None:
        for entry in results:
            entry["title"] = _MODEL._movie_titles.get(entry["movie_id"], "")

    tmdb_map = _map_movielens_to_tmdb([entry["movie_id"] for entry in results])
    if tmdb_map:
        for entry in results:
            tmdb_id = tmdb_map.get(entry["movie_id"])
            if tmdb_id:
                entry["poster_url"] = _poster_url_for_tmdb(tmdb_id)

    return SeedRecommendationResponse(results=results)


@app.post("/recommendations/seed-hybrid", response_model=SeedHybridRecommendationResponse)
def get_seed_hybrid_recommendations(payload: SeedRequest) -> SeedHybridRecommendationResponse:
    if _HYBRID is None or _MODEL is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if _ENGINE is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    if not payload.tmdb_ids:
        raise HTTPException(status_code=400, detail="tmdb_ids is required")

    mapped_tmdb_ids = set()
    with _ENGINE.begin() as conn:
        rows = conn.execute(
            select(
                movielens_tmdb_map.c.movielens_movie_id,
                movielens_tmdb_map.c.tmdb_id,
            ).where(movielens_tmdb_map.c.tmdb_id.in_(payload.tmdb_ids))
        )
        movielens_ids = []
        for row in rows:
            movielens_ids.append(int(row.movielens_movie_id))
            mapped_tmdb_ids.add(int(row.tmdb_id))

    missing_tmdb_ids = [mid for mid in payload.tmdb_ids if mid not in mapped_tmdb_ids]
    text_profile = None
    if missing_tmdb_ids:
        if _TMDB is None:
            raise HTTPException(status_code=503, detail="TMDB API key not configured")
        texts = []
        for tmdb_id in missing_tmdb_ids:
            bundle = _TMDB.fetch_movie_bundle(tmdb_id)
            text_parts = [
                str(bundle.get("title") or ""),
                " ".join(bundle.get("genres") or []),
                " ".join(bundle.get("cast") or []),
                str(bundle.get("director") or ""),
                " ".join(bundle.get("keywords") or []),
                str(bundle.get("overview") or ""),
            ]
            texts.append(" ".join(part for part in text_parts if part).strip().lower())
        text_profile = _HYBRID.content.profile_from_texts(texts)

    mapped_profile = _HYBRID.content.profile_from_movie_ids(movielens_ids)
    if mapped_profile is None and text_profile is None:
        raise HTTPException(status_code=404, detail="No content profile available")

    if mapped_profile is None:
        profile = text_profile
    elif text_profile is None:
        profile = mapped_profile
    else:
        profile = normalize(mapped_profile + text_profile)

    content_results = _HYBRID.content.recommend_from_profile(
        profile,
        n=payload.n,
        exclude_movie_ids=movielens_ids,
    )

    if not content_results:
        return SeedHybridRecommendationResponse(results=[])

    movie_ids = [entry["movie_id"] for entry in content_results]
    cf_scores = []
    for movie_id in movie_ids:
        try:
            idx = _MODEL.item_index.get(movie_id)
            if idx is None:
                cf_scores.append(_MODEL.global_mean)
            else:
                cf_scores.append(float(_MODEL.item_means[idx]))
        except Exception:
            cf_scores.append(_MODEL.global_mean)

    min_cf = min(cf_scores)
    max_cf = max(cf_scores)
    if max_cf == min_cf:
        cf_norm = [1.0 for _ in cf_scores]
    else:
        cf_norm = [(score - min_cf) / (max_cf - min_cf) for score in cf_scores]

    results = []
    for entry, cf_score, cf_scaled in zip(content_results, cf_scores, cf_norm):
        hybrid_score = 0.7 * cf_scaled + 0.3 * float(entry["content_score"])
        results.append(
            {
                "movie_id": entry["movie_id"],
                "content_score": float(entry["content_score"]),
                "cf_score": cf_score,
                "hybrid_score": float(hybrid_score),
            }
        )

    if _MODEL._movie_titles is not None:
        for entry in results:
            entry["title"] = _MODEL._movie_titles.get(entry["movie_id"], "")

    tmdb_map = _map_movielens_to_tmdb([entry["movie_id"] for entry in results])
    if tmdb_map:
        for entry in results:
            tmdb_id = tmdb_map.get(entry["movie_id"])
            if tmdb_id:
                entry["poster_url"] = _poster_url_for_tmdb(tmdb_id)

    return SeedHybridRecommendationResponse(results=results)


@app.get("/recommendations/{user_id}", response_model=RecommendationResponse)
def get_recommendations(
    user_id: str,
    n: int = Query(10, ge=1, le=100),
    include_titles: bool = True,
) -> RecommendationResponse:
    if _MODEL is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    results: list[dict[str, Any]] = _MODEL.recommend(
        user_id=user_id,
        n=n,
        include_titles=include_titles,
    )

    return RecommendationResponse(user_id=user_id, results=results)


@app.get("/recommendations/hybrid/{user_id}", response_model=HybridRecommendationResponse)
def get_hybrid_recommendations(
    user_id: str,
    n: int = Query(10, ge=1, le=100),
    include_titles: bool = True,
) -> HybridRecommendationResponse:
    if _HYBRID is None or _MODEL is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    results: list[dict[str, Any]] = _HYBRID.recommend(
        user_id=user_id,
        n=n,
    )

    if include_titles and _MODEL._movie_titles is not None:
        for entry in results:
            entry["title"] = _MODEL._movie_titles.get(entry["movie_id"], "")

    tmdb_map = _map_movielens_to_tmdb([entry["movie_id"] for entry in results])
    if tmdb_map:
        for entry in results:
            tmdb_id = tmdb_map.get(entry["movie_id"])
            if tmdb_id:
                entry["poster_url"] = _poster_url_for_tmdb(tmdb_id)

    return HybridRecommendationResponse(user_id=user_id, results=results)
