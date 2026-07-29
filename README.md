# Prism Analytics

Prism is a private, multi-user analytics workspace. Register an account, upload a file, explore its quality and values, build charts, save chart dashboards, export CSV, and ask an AI analyst questions grounded in a profile of your selected dataset.

The application is a FastAPI backend with a responsive, dependency-free single-page frontend served from the same service.

## What it does

- Creates accounts and authenticates users with signed JWT access tokens
- Keeps datasets, dashboards, and chat history private to their owner
- Imports Excel (`.xlsx`, `.xls`), CSV, TSV, and delimited TXT files
- Detects numeric fields and otherwise treats fields as categorical
- Calculates rows, columns, completeness, missing cells, duplicate rows, and numeric summaries
- Searches and sorts the private dataset library
- Previews datasets in 50-row pages and supports CSV export
- Builds bar, line, area, pie, scatter, and histogram charts using raw, sum, average, count, minimum, or maximum values
- Saves multiple chart configurations to a named private dashboard and supports dashboard deletion
- Provides optional AI chat using dataset metadata, summary statistics, top category values, an eight-row sample, and recent chat context

> Prism does not connect to end-user databases. Users import files only. `DATABASE_URL` configures Prism's own application database.

## Stack

- FastAPI, Uvicorn, SQLAlchemy, and Pydantic
- pandas with `openpyxl` and `xlrd` for file imports
- SQLite for local development; PostgreSQL for deployment
- A vanilla HTML/CSS/JavaScript frontend
- LangChain's OpenAI-compatible client for the optional GAP AI provider

## Run locally

Python 3.11+ is recommended.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn src.main:app --reload
```

Open `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

`openpyxl` is required for `.xlsx` files and `xlrd` for legacy `.xls` files; both are included in `requirements.txt`.

## Configuration

Copy `.env.example` to `.env` and set production values before deploying:

```env
# SQLite is the local default. Use PostgreSQL in production.
DATABASE_URL=sqlite:///./analytics.db

# Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_KEY=replace-with-a-long-random-production-secret
ACCESS_TOKEN_MINUTES=1440

# Comma-separated browser origins. Leave blank when serving the frontend together with this API.
CORS_ALLOW_ORIGINS=http://localhost:8000
MAX_UPLOAD_MB=25

# Optional: enables AI chat through https://api.gapgpt.app/v1
GAP=
```

Use a PostgreSQL URL such as `postgresql://user:password@host:5432/prism` in production. The app automatically converts standard PostgreSQL URLs to SQLAlchemy's `psycopg` driver format.

Keep `SECRET_KEY` stable: changing it invalidates existing login tokens. Never commit `.env` or a real AI key.

## Import limits and behavior

- Maximum upload size: `MAX_UPLOAD_MB` (25 MB by default)
- Maximum imported rows: 50,000 per dataset
- Column names must be unique; the first file row should be the header
- CSV and TXT files use pandas delimiter detection; TSV uses tab separation
- Text imports first use UTF-8 with BOM support and retry as Latin-1 when needed
- Empty files and empty datasets are rejected
- Blank dataset names fall back to the uploaded filename

Each imported row is stored as JSON in the application database. This is convenient for small and moderate datasets, but it is the main constraint to consider when scaling.

## API overview

All endpoints except registration, login, and health require an `Authorization: Bearer <token>` header.

| Area | Endpoints |
| --- | --- |
| Health | `GET /api/health` |
| Authentication | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Datasets | `GET /api/datasets`, `POST /api/datasets/upload`, `GET` / `DELETE /api/datasets/{dataset_id}` |
| Dataset data | `GET /api/datasets/{dataset_id}/rows`, `GET /api/datasets/{dataset_id}/export` |
| Charts | `POST /api/datasets/{dataset_id}/chart` |
| Dashboards | `GET` / `POST /api/dashboards`, `PUT` / `DELETE /api/dashboards/{dashboard_id}` |
| AI chat | `POST /api/chat`, `GET /api/chat/{dataset_id}` |

Use `/docs` for request schemas and executable endpoint documentation.

## Docker

```bash
docker build -t prism-analytics .
docker run --env-file .env -p 8000:8000 prism-analytics
```

The container uses `PORT` (default `8000`). For a production platform, set `DATABASE_URL` to a managed PostgreSQL database, set a strong `SECRET_KEY`, and configure `CORS_ALLOW_ORIGINS` if the frontend is hosted separately.

## Architecture

```text
Browser SPA
  | Bearer JWT
  v
FastAPI API
  |-- authentication and ownership checks
  |-- pandas import, profiling, aggregation, and CSV export
  |-- SQLAlchemy storage for datasets, rows, dashboards, and chat
  `-- optional GAP AI analyst
           |
 SQLite locally / PostgreSQL in production
```

## Performance roadmap

For the current 50,000-row limit, use PostgreSQL in production and keep uploads within the configured limit. The highest-impact next improvements are:

1. A composite database index on dataset rows (`dataset_id`, `position`) and 50-row browser pagination are included to keep previews fast.
2. Store large datasets as Parquet in object storage and query them with DuckDB, ClickHouse, or a warehouse instead of rebuilding a pandas DataFrame from JSON rows for every analysis request.
3. Move imports, profiling, and AI requests to a durable background-job system such as Celery/RQ with Redis so they do not block web workers.
4. Run multiple Uvicorn workers behind a reverse proxy and cache reusable dataset summaries and chart results.

Prioritize the next two items before increasing the import limit.
