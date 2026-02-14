# ML Module (CineMind)

This package contains **training** and **inference** code for recommendations. Training is **offline** only; the API should load artifacts for inference.

## Structure

- `training/` Offline training jobs.
- `inference/` Runtime inference utilities.
- `data/` Local datasets (not tracked).
- `artifacts/` Saved models and mappings.
- `models/` Future model checkpoints.

## Data format

`ratings.csv` must include:

```
user_id,movie_id,rating
```

Optional columns are ignored.

## Train (offline)

From repo root:

```
python -m ml.training.train_cf
```

Environment variables:

- `MLR_DATA_DIR` (default: `ml/data`)
- `MLR_ARTIFACTS_DIR` (default: `ml/artifacts`)
- `MLR_MODEL_FILE` (default: `ml/artifacts/cf_model.pkl`)
- `MLR_SVD_RANK` (default: `50`)
- `MLR_MIN_RATINGS_PER_USER` (default: `3`)

## Inference usage

```
from ml.inference.recommender import CFRecommender

model = CFRecommender.load()
recommendations = model.recommend(user_id="123", n=10)
```
