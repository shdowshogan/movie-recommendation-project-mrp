# CineMind API (FastAPI)

## Run (dev)

From repo root:

```
python -m venv .venv
.venv\Scripts\pip install -r server\requirements.txt
.venv\Scripts\pip install -r ml\requirements.txt
set PYTHONPATH=.
.venv\Scripts\uvicorn app.main:app --reload --app-dir server
```

## Endpoints

- `GET /health`
- `GET /recommendations/{user_id}?n=10&include_titles=true`

## Notes

- Model artifacts must exist at `ml/artifacts/cf_model.pkl`.
- Movie titles are loaded from `ml/data/movie.csv`.
- Set `INCLUDE_TITLES=false` to skip loading titles on startup.
