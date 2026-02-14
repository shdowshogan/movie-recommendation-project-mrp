from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from ml.inference.recommender import CFRecommender

app = FastAPI(title="CineMind API", version="0.1.0")

_MODEL: CFRecommender | None = None


class Recommendation(BaseModel):
    movie_id: str
    score: float
    title: str | None = None


class RecommendationResponse(BaseModel):
    user_id: str
    results: list[Recommendation]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _init_model() -> CFRecommender:
    model = CFRecommender.load()
    if os.getenv("INCLUDE_TITLES", "true").lower() in {"1", "true", "yes"}:
        model.load_titles()
    return model


@app.on_event("startup")
def load_model() -> None:
    global _MODEL
    _MODEL = _init_model()


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
