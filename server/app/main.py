from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from ml.inference.content import ContentRecommender
from ml.inference.hybrid import HybridConfig, HybridRecommender
from ml.inference.recommender import CFRecommender

app = FastAPI(title="CineMind API", version="0.1.0")

_MODEL: CFRecommender | None = None
_CONTENT: ContentRecommender | None = None
_HYBRID: HybridRecommender | None = None


class Recommendation(BaseModel):
    movie_id: str
    score: float
    title: str | None = None


class HybridRecommendation(BaseModel):
    movie_id: str
    cf_score: float
    hybrid_score: float | None = None
    title: str | None = None


class RecommendationResponse(BaseModel):
    user_id: str
    results: list[Recommendation]


class HybridRecommendationResponse(BaseModel):
    user_id: str
    results: list[HybridRecommendation]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


@app.on_event("startup")
def load_model() -> None:
    global _MODEL, _CONTENT, _HYBRID
    _MODEL = _init_model()
    _HYBRID = _init_hybrid(_MODEL)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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

    return HybridRecommendationResponse(user_id=user_id, results=results)
