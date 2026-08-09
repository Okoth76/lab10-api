# TechVault Inventory API

FastAPI + SQLModel inventory API for products, categories, and
suppliers, with a pytest suite, GitHub Actions CI/CD pipeline, and
Render deployment config.

## Project structure

```
product-api/
├── main.py                    # app, routes, error handlers, /health, /metrics
├── models/
│   └── product.py             # SQLModel table + create/update schemas
├── database/
│   └── session.py             # engine + get_session dependency
├── tests/
│   ├── conftest.py            # isolated in-memory SQLite fixtures per test
│   ├── test_categories.py
│   ├── test_products.py
│   ├── test_suppliers.py
│   ├── test_bulk_operations.py   # bulk-update + adjust-stock
│   ├── test_errors.py            # global exception handler shapes
│   ├── test_integration.py       # Exercise 1: full CRUD flow
│   └── test_performance.py       # Exercise 2: pytest-benchmark
├── locustfile.py              # Exercise 2: real HTTP load test
├── .github/workflows/ci.yml   # lint -> test (matrix) -> build/push -> deploy
├── Dockerfile
├── requirements.txt
└── pyproject.toml             # ruff + black config
```

## What was fixed from the original code

**Route ordering bug:** `PATCH /products/{product_id}` was declared
before `PATCH /products/bulk-update` and `PATCH /products/adjust-stock`.
FastAPI/Starlette match routes in declaration order, so requests to
those two endpoints were being captured by `{product_id}` first
(trying to parse `"bulk-update"` as an int → 422). Fixed by moving the
literal-path routes above the parameterized one. **This bug affected
the deployed API directly, independent of testing** — worth knowing
if you've deployed this before.

**Duplicate `StockAdjustment` model:** it was imported from
`models/product.py` and then redefined identically in `main.py`,
silently shadowing the import. Removed the duplicate.

**`datetime.utcnow()`** is deprecated in current Python; switched to
timezone-aware `datetime.now(UTC)` throughout.

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# create .env (or edit the one included) — sqlite for local dev:
echo 'DATABASE_URL=sqlite:///./techvault.db' > .env

uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API docs, or
`http://localhost:8000/health` for the health check.

## Running tests

```bash
# full suite with coverage
pytest tests/ -v --cov=. --cov-report=term-missing

# skip the benchmark tests (they're slower and non-deterministic in CI)
pytest tests/ -v --ignore=tests/test_performance.py

# just the benchmarks
pytest tests/test_performance.py --benchmark-only
```

45 tests, 96% coverage as of this writing.

### Load testing (Exercise 2)

Start the API, then in another terminal:

```bash
locust -f locustfile.py --host http://localhost:8000
```

Open `http://localhost:8089`, set concurrent users / spawn rate, and
watch requests/sec, latency, and failure rate live. This is a better
signal for "how many requests/sec can it handle" than the in-process
pytest-benchmark numbers, since it goes over real HTTP.

### Linting

```bash
pip install ruff black
ruff check .
black --check .
```

Config lives in `pyproject.toml`. `B008` (calling `Depends()` in an
argument default) is intentionally ignored — that's the standard
FastAPI dependency-injection idiom, not a bug.

## CI/CD pipeline (`.github/workflows/ci.yml`)

Runs on every push to `main`/`develop` and every PR into `main`:

1. **lint** — ruff + black, fails fast before the test matrix runs
2. **test** — pytest against a real Postgres 16 service container, on
   both Python 3.11 and 3.12 (Exercise 3), with coverage uploaded to
   Codecov
3. **build-and-push** — only on push to `main`, after tests pass on
   every matrix version: builds the Docker image and pushes
   `latest` + the commit SHA to Docker Hub
4. **deploy** — triggers a Render deploy hook, waits, then curls
   `/health` on the live service to confirm it came up

### Required GitHub secrets

| Secret | Purpose |
|---|---|
| `DOCKER_USERNAME` | Docker Hub username |
| `DOCKER_PASSWORD` | Docker Hub access token (not your password) |
| `RENDER_DEPLOY_HOOK_URL` | Render service → Settings → Deploy Hook |
| `RENDER_SERVICE_URL` | your live URL, e.g. `https://techvault-api.onrender.com` |

Codecov upload doesn't require a token for public repos; for a
private repo add `CODECOV_TOKEN` as a secret and reference it in the
workflow.

## Deploying to Render

**Option A — Dashboard**
1. Push this repo to GitHub.
2. render.com → New → Web Service → connect the repo.
3. Environment: **Docker** (it'll pick up the `Dockerfile` automatically).
4. Add environment variables:
   - `DATABASE_URL` — use Render's managed PostgreSQL connection string
   - Anything else your deployment needs (e.g. `LOG_FILE`)
5. Deploy. Render gives you a deploy hook URL under Settings you can
   put in `RENDER_DEPLOY_HOOK_URL` for the CI pipeline above.

**Option B — Fly.io**
```bash
fly launch          # detects the Dockerfile, generates fly.toml
fly secrets set DATABASE_URL=postgresql://...
fly deploy
```

## Monitoring

- `GET /health` — liveness probe: status, uptime, version, Python
  version. Point your uptime monitor (Render's own health check, or
  an external one like UptimeRobot) at this.
- `GET /metrics` — basic inventory counts (products/categories/suppliers)
  plus uptime. No auth is enforced on this API currently, so if you
  add authentication later, lock this endpoint down to admins first.

The app also logs every request (method, path, status, duration) via
a middleware in `main.py`, at `INFO` level to stdout — Render and
most PaaS providers capture stdout logs automatically.

## Notes / things worth doing next

- **No authentication exists on this API yet.** The original lab
  handout assumes a `/register` + `/login` + JWT flow, but your
  actual `main.py`/`models/product.py` don't implement one — every
  endpoint (including `/metrics`) is currently open. If that's
  intentional for now, fine, but it's worth deciding deliberately
  before this goes further than a lab exercise.
- CI runs the test suite against Postgres (matching production) but
  local dev defaults to SQLite for convenience — the test suite
  itself uses an isolated in-memory SQLite DB either way, so it's
  fast and doesn't touch whatever `DATABASE_URL` points to.
