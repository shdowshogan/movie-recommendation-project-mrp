# Deployment Guide (Vercel + Render)

This project is split into:
- `client/` (Next.js frontend)
- `server/` + `ml/` (FastAPI backend + ML code)

Recommended production setup:
- Frontend on **Vercel**
- Backend on **Render Web Service**
- PostgreSQL on **Render PostgreSQL**

---

## 1) Backend deploy on Render (No Blueprint required)

Use this manual setup if Blueprint is paid/unavailable on your plan.

If Blueprint is available later, you can optionally use `render.yaml`, but it is not required.

### A. Create PostgreSQL database
1. In Render, create a new **PostgreSQL** instance.
2. Copy the **Internal Database URL** (or external URL if needed).

### B. Create Web Service
1. Create a new **Web Service** from this GitHub repo.
2. Use these settings:
   - **Environment**: `Python`
   - **Build Command**:
     ```bash
     pip install -r server/requirements.txt && pip install -r ml/requirements.txt
     ```
   - **Start Command**:
     ```bash
     PYTHONPATH=. uvicorn app.main:app --app-dir server --host 0.0.0.0 --port $PORT
     ```

### C. Set backend environment variables
Use these keys in Render:
- `TMDB_API_KEY` = your TMDB key
- `MLR_DB_URL` = your Render Postgres URL
- `JWT_SECRET` = long random secret
- `MLR_DB_INIT` = `true`
- `INCLUDE_TITLES` = `true`
- `AUTH_COOKIE_SECURE` = `true`
- `AUTH_COOKIE_SAMESITE` = `lax`
- `CORS_ALLOW_ORIGINS` = your frontend URL(s), comma-separated
  - Example: `https://your-app.vercel.app`

### D. Verify backend
Open:
- `https://<your-render-backend>/health`

Expect:
```json
{"status":"ok"}
```

---

## 2) Frontend deploy on Vercel

1. Import the same GitHub repo into Vercel.
2. Set **Root Directory** to `client`.
3. Add environment variables in Vercel project settings:
   - `NEXT_PUBLIC_API_BASE` = `/api`
   - `BACKEND_URL` = `https://<your-render-backend>`

Why this setup:
- Browser calls `"/api/..."` on your Vercel domain.
- Next.js rewrite proxies to Render backend.
- This keeps auth cookie flow much more reliable.

4. Deploy.

---

## 3) Final checks

After both are live:
1. Open your Vercel URL.
2. Try register/login.
3. Test:
   - Search
   - Discover (trending/upcoming/filtered)
   - Generate recommendations
4. If login fails, recheck:
   - `AUTH_COOKIE_SECURE=true`
   - `AUTH_COOKIE_SAMESITE=lax`
   - `NEXT_PUBLIC_API_BASE=/api`
   - `BACKEND_URL` is correct

---

## 4) Local env files

You can copy templates:
- `server/.env.example` -> `server/.env`
- `client/.env.example` -> `client/.env.local`

For local development, keep:
- `NEXT_PUBLIC_API_BASE=http://localhost:8000`
- `BACKEND_URL=http://localhost:8000`

---

## Notes

- Backend expects ML artifacts in `ml/artifacts/` and data in `ml/data/`.
- Ensure those required files are available in your deployment source.
- If you rotate domains, update `CORS_ALLOW_ORIGINS` and redeploy backend.
