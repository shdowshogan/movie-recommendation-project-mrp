from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class TMDBClient:
    api_key: str
    base_url: str = "https://api.themoviedb.org/3"
    timeout_s: int = 30
    session: requests.Session = field(init=False)

    def __post_init__(self) -> None:
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.6,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    @classmethod
    def from_env(cls) -> "TMDBClient":
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            raise RuntimeError("TMDB_API_KEY is not set")
        timeout_s = int(os.getenv("TMDB_TIMEOUT", "30"))
        return cls(api_key=api_key, timeout_s=timeout_s)

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        params["api_key"] = self.api_key
        resp = self.session.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        return resp.json()

    def search_movie(self, title: str, year: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query": title}
        if year:
            params["year"] = year
        data = self._get("/search/movie", **params)
        return data.get("results", [])

    def movie_details(self, tmdb_id: int) -> dict[str, Any]:
        return self._get(f"/movie/{tmdb_id}")

    def movie_credits(self, tmdb_id: int) -> dict[str, Any]:
        return self._get(f"/movie/{tmdb_id}/credits")

    def movie_keywords(self, tmdb_id: int) -> dict[str, Any]:
        return self._get(f"/movie/{tmdb_id}/keywords")

    def trending_movies(self, window: str = "week") -> list[dict[str, Any]]:
        data = self._get(f"/trending/movie/{window}")
        return data.get("results", [])

    def upcoming_movies(self) -> list[dict[str, Any]]:
        data = self._get("/movie/upcoming")
        return data.get("results", [])

    def fetch_movie_bundle(self, tmdb_id: int, cast_limit: int = 10) -> dict[str, Any]:
        details = self.movie_details(tmdb_id)
        credits = self.movie_credits(tmdb_id)
        keywords = self.movie_keywords(tmdb_id)

        genres = [g.get("name", "") for g in details.get("genres", []) if g.get("name")]
        cast = [c.get("name", "") for c in credits.get("cast", []) if c.get("name")]
        cast = cast[:cast_limit]

        director = None
        for crew in credits.get("crew", []) or []:
            if crew.get("job") == "Director":
                director = crew.get("name")
                break

        keyword_list = []
        for item in keywords.get("keywords", []) or []:
            name = item.get("name")
            if name:
                keyword_list.append(name)

        return {
            "title": details.get("title") or "",
            "release_date": details.get("release_date"),
            "genres": genres,
            "cast": cast,
            "director": director,
            "keywords": keyword_list,
            "overview": details.get("overview"),
        }
