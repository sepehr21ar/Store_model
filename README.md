# Prism Analytics

Prism is a private, multi-user analytics workspace built with FastAPI, SQLAlchemy, pandas, and LangChain. Users register, upload data files, explore typed columns, build charts and dashboards, and chat with an AI analyst grounded in their own dataset.

## Features

- JWT registration and login with PBKDF2 password hashing
- Strict per-user ownership for datasets, dashboards, and chat history
- Excel (`.xlsx`, `.xls`), CSV, TSV, and delimited TXT imports
- Automatic delimiter and common text-encoding handling
- Automatic numeric, category, and date column detection
- Dataset quality metrics for completeness, missing cells, and duplicate rows
- Dataset summaries and raw/sum/average/count/min/max analysis
- Bar and line charts with saved dashboards
- A separate private dashboard page for every imported file
- A fast 50-row preview with an optional full-row viewer
- Ownership-safe dataset deletion and authenticated CSV export
- Persistent dataset-specific AI conversations through LangChain and Cohere
- Responsive frontend served directly by FastAPI
- SQLite local development and PostgreSQL production deployment

The product intentionally does not ask end users for database credentials or expose database-connection screens. Users add data through files only. `DATABASE_URL` is the application's own private storage and is configured by the developer or deployment platform.

## Run locally

Python 3.11+ is recommended.

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn src.main:app --reload
```

Open `http://127.0.0.1:8000`. API documentation is available at `http://127.0.0.1:8000/docs`.

The dependency installation step is required for Excel imports. In particular, `.xlsx` uses `openpyxl` and legacy `.xls` uses `xlrd`; both are included in `requirements.txt`.

## Configuration

SQLite is the default application database. For deployment, use PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@host:5432/prism
SECRET_KEY=replace-with-a-long-random-production-secret
```

Keep `SECRET_KEY` stable after users are created. Changing it invalidates active login tokens.

## AI configuration

Imports, charts, data exploration, and dashboards work without an AI key. AI chat requires:

```env
COHERE_API_KEY=your-key
COHERE_MODEL=command-a-03-2025
```

The assistant receives computed statistics, column metadata, top category values, a small row sample, and recent conversation history. It does not receive passwords or infrastructure credentials.

## File-import rules

- Maximum file size: 25 MB by default
- Maximum imported rows: 50,000
- The first row should contain unique column names
- Supported files: `.xlsx`, `.xls`, `.csv`, `.tsv`, and `.txt`
- CSV/TXT separators are detected automatically; UTF-8 and Latin-1 text are supported
- If the dataset-name field is empty, the uploaded filename becomes the dataset name

## Docker and FastAPI Cloud

```bash
docker build -t prism-analytics .
docker run --env-file .env -p 8000:8000 prism-analytics
```

For FastAPI Cloud, connect the repository, configure the variables from `.env.example`, and attach a managed PostgreSQL database. The container reads `PORT` automatically and creates application tables during startup.

## Architecture

```text
Browser SPA
    | Bearer JWT
FastAPI API
    |-- authentication and per-user authorization
    |-- pandas file import, profiling, and aggregation
    |-- SQLAlchemy dataset, dashboard, and chat storage
    `-- LangChain/Cohere data analyst
             |
SQLite locally / PostgreSQL in production
```

The current JSON row store is suitable for moderate datasets. A future large-data version can preserve the API and move dataset rows to Parquet/object storage with DuckDB, ClickHouse, or a cloud warehouse.
