from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Cookie, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
import jwt

from ml.inference.content import ContentRecommender
from ml.inference.hybrid import HybridConfig, HybridRecommender
from ml.inference.recommender import CFRecommender
from ml.config import MOVIES_FILE, RATINGS_FILE
from ml.db import get_engine, init_db, movielens_tmdb_map, users
from ml.training.io import get_user_ratings as get_user_ratings_rows
from ml.tmdb_client import TMDBClient
from sqlalchemy import insert, select
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

_AUTH_COOKIE_NAME = "access_token"
_AUTH_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
_AUTH_ALG = "HS256"
_AUTH_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "4320"))
_AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() in {
    "1",
    "true",
    "yes",
}
_PWD_CONTEXT = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


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


class BrowseResult(BaseModel):
    tmdb_id: int
    title: str
    year: str | None = None
    poster_url: str | None = None
    overview: str | None = None


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


class UserRating(BaseModel):
    movie_id: str
    rating: float
    title: str | None = None
    poster_url: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserOut


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


def _create_access_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": now + timedelta(minutes=_AUTH_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _AUTH_SECRET, algorithm=_AUTH_ALG)


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=_AUTH_EXPIRE_MINUTES * 60,
        path="/",
    )


def _user_from_row(row) -> UserOut:
    data = row._mapping
    return UserOut(
        id=int(data["id"]),
        email=str(data["email"]),
        created_at=data["created_at"],
    )


def _get_user_by_email(email: str) -> UserOut | None:
    if _ENGINE is None:
        return None
    with _ENGINE.begin() as conn:
        row = conn.execute(select(users).where(users.c.email == email)).first()
    return _user_from_row(row) if row else None


def _get_user_by_id(user_id: int) -> UserOut | None:
    if _ENGINE is None:
        return None
    with _ENGINE.begin() as conn:
        row = conn.execute(select(users).where(users.c.id == user_id)).first()
    return _user_from_row(row) if row else None


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
        if os.getenv("MLR_DB_INIT", "true").lower() in {"1", "true", "yes"}:
            init_db(_ENGINE)
    except RuntimeError:
        _ENGINE = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, response: Response) -> AuthResponse:
    if _ENGINE is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    email = payload.email.strip().lower()
    with _ENGINE.begin() as conn:
        existing = conn.execute(select(users).where(users.c.email == email)).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        password_hash = _PWD_CONTEXT.hash(payload.password)
        row = conn.execute(
            insert(users)
            .values(email=email, password_hash=password_hash)
            .returning(users.c.id, users.c.email, users.c.created_at)
        ).first()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user = _user_from_row(row)
    token = _create_access_token(user.id, user.email)
    _set_auth_cookie(response, token)
    return AuthResponse(user=user)


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response) -> AuthResponse:
    if _ENGINE is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    email = payload.email.strip().lower()
    with _ENGINE.begin() as conn:
        row = conn.execute(select(users).where(users.c.email == email)).first()

    if not row:
        raise HTTPException(status_code=401, detail="Email not found")

    data = row._mapping
    if not _PWD_CONTEXT.verify(payload.password, data["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    user = _user_from_row(row)
    token = _create_access_token(user.id, user.email)
    _set_auth_cookie(response, token)
    return AuthResponse(user=user)


@app.post("/auth/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(_AUTH_COOKIE_NAME, path="/")
    return {"status": "ok"}


@app.get("/auth/me", response_model=AuthResponse)
def me(access_token: str | None = Cookie(default=None, alias=_AUTH_COOKIE_NAME)) -> AuthResponse:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(access_token, _AUTH_SECRET, algorithms=[_AUTH_ALG])
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = _get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return AuthResponse(user=user)


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


@app.get("/tmdb/trending", response_model=list[BrowseResult])
def get_trending_movies(
    limit: int = Query(12, ge=1, le=40),
    window: str = Query("week", pattern="^(day|week)$"),
) -> list[BrowseResult]:
    if _TMDB is None:
        raise HTTPException(status_code=503, detail="TMDB API key not configured")

    results = _TMDB.trending_movies(window=window)
    payload: list[BrowseResult] = []
    for item in results[:limit]:
        release_date = item.get("release_date") or ""
        year = release_date.split("-")[0] if release_date else None
        poster_path = item.get("poster_path")
        poster_url = (
            f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else None
        )
        payload.append(
            BrowseResult(
                tmdb_id=int(item.get("id")),
                title=item.get("title") or "",
                year=year,
                poster_url=poster_url,
                overview=item.get("overview"),
            )
        )
    return payload


@app.get("/tmdb/upcoming", response_model=list[BrowseResult])
def get_upcoming_movies(
    limit: int = Query(12, ge=1, le=40),
) -> list[BrowseResult]:
    if _TMDB is None:
        raise HTTPException(status_code=503, detail="TMDB API key not configured")

    results = _TMDB.upcoming_movies()
    payload: list[BrowseResult] = []
    for item in results[:limit]:
        release_date = item.get("release_date") or ""
        year = release_date.split("-")[0] if release_date else None
        poster_path = item.get("poster_path")
        poster_url = (
            f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else None
        )
        payload.append(
            BrowseResult(
                tmdb_id=int(item.get("id")),
                title=item.get("title") or "",
                year=year,
                poster_url=poster_url,
                overview=item.get("overview"),
            )
        )
    return payload


@app.get("/users/{user_id}/ratings", response_model=list[UserRating])
def get_user_liked_movies(
    user_id: str,
    limit: int = Query(6, ge=1, le=40),
    min_rating: float = Query(4.0, ge=0.0, le=5.0),
) -> list[UserRating]:
    try:
        rows = get_user_ratings_rows(
            user_id=user_id,
            ratings_path=RATINGS_FILE,
            movies_path=MOVIES_FILE,
            limit=None,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    filtered = [row for row in rows if float(row.get("rating", 0)) >= min_rating]
    filtered = filtered[:limit]

    results: list[dict[str, Any]] = []
    for row in filtered:
        results.append(
            {
                "movie_id": str(row.get("movie_id")),
                "rating": float(row.get("rating", 0)),
                "title": row.get("title") or None,
            }
        )

    tmdb_map = _map_movielens_to_tmdb([item["movie_id"] for item in results])
    if tmdb_map:
        for item in results:
            tmdb_id = tmdb_map.get(item["movie_id"])
            if tmdb_id:
                item["poster_url"] = _poster_url_for_tmdb(tmdb_id)

    return results


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

    candidate_k = int(os.getenv("SEED_HYBRID_CANDIDATE_K", "200"))
    content_results = _HYBRID.content.recommend_from_profile(
        profile,
        n=max(payload.n, candidate_k),
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

    results.sort(key=lambda item: item["hybrid_score"], reverse=True)
    results = results[: payload.n]

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
