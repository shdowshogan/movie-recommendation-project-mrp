from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("MLR_DATA_DIR", str(ROOT_DIR / "data")))
ARTIFACTS_DIR = Path(os.getenv("MLR_ARTIFACTS_DIR", str(ROOT_DIR / "artifacts")))
MODEL_FILE = Path(os.getenv("MLR_MODEL_FILE", str(ARTIFACTS_DIR / "cf_model.pkl")))
CONTENT_MATRIX_FILE = Path(
	os.getenv("MLR_CONTENT_MATRIX", str(ARTIFACTS_DIR / "content_matrix.npz"))
)
CONTENT_VECTORIZER_FILE = Path(
	os.getenv("MLR_CONTENT_VECTORIZER", str(ARTIFACTS_DIR / "content_vectorizer.pkl"))
)
CONTENT_INDEX_FILE = Path(
	os.getenv("MLR_CONTENT_INDEX", str(ARTIFACTS_DIR / "content_index.json"))
)


def _default_ratings_file(data_dir: Path) -> Path:
	preferred = data_dir / "ratings.csv"
	if preferred.exists():
		return preferred
	fallback = data_dir / "rating.csv"
	if fallback.exists():
		return fallback
	return preferred


RATINGS_FILE = Path(os.getenv("MLR_RATINGS_FILE", str(_default_ratings_file(DATA_DIR))))


def _default_movies_file(data_dir: Path) -> Path:
	preferred = data_dir / "movie.csv"
	if preferred.exists():
		return preferred
	fallback = data_dir / "movies.csv"
	return fallback


MOVIES_FILE = Path(os.getenv("MLR_MOVIES_FILE", str(_default_movies_file(DATA_DIR))))

SVD_RANK = int(os.getenv("MLR_SVD_RANK", "50"))
MIN_RATINGS_PER_USER = int(os.getenv("MLR_MIN_RATINGS_PER_USER", "3"))
