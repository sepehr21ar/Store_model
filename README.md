---
title: Store Management FastAPI
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
---

# Store Management 

Store Management FastAPI is a small inventory and sales management web app. It provides a FastAPI backend, a vanilla HTML/CSS/JavaScript frontend, and a PostgreSQL database schema for products, stock, store sales, online sales, and action logs.

The app is prepared for Docker and Hugging Face Spaces. It listens on port `7860`.

## Features

- Dashboard with product, inventory, sales, and inventory value metrics.
- Full product CRUD with active/inactive status management.
- Inventory add, set, list, and remove actions by product ID.
- Product IDs are resequenced after a permanent product delete so remaining products stay ordered.
- Store sale and online sale recording.
- PostgreSQL trigger-based stock deduction when sales are recorded.
- Sales and inventory reports with browser-rendered charts.
- Optional database assistant powered by Cohere and LangChain.
- Static frontend served directly by FastAPI.

## Project Structure

```text
.
├── Dockerfile
├── requirements.txt
├── README.md
└── src
    ├── main.py                  # FastAPI app, routes, static frontend serving
    ├── init_db.py               # PostgreSQL connection URL and schema initialization
    ├── store.py                 # Store, inventory, sales, and report logic
    ├── llm_sql.py               # Optional SQL assistant using Cohere/LangChain
    ├── store_schema_postgres.sql
    └── static
        ├── index.html
        ├── app.js
        └── styles.css
```

## Requirements

- Python 3.12 or compatible Python 3 version.
- PostgreSQL database.
- Docker, if you want to run the container.
- Optional Cohere API key for the assistant tab.

## Environment Variables

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Required:

```env
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

Optional:

```env
COHERE_API_KEY=your_cohere_api_key
COHERE_MODEL=command-a-03-2025
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:7860
```

Notes:

- `DATABASE_URL` is required. The app does not use SQLite.
- The database schema is initialized automatically when the FastAPI app starts.
- `COHERE_API_KEY` is only needed for the Database Assistant tab.

## Run Locally

Install dependencies:

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
```

Start the app:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 7860
```

Open:

```text
http://localhost:7860
```

Health check:

```text
http://localhost:7860/api/health
```
Open:

```text
http://localhost:7860
```

Health check:

```text
http://localhost:7860/api/health
```

## Run With Docker

The Dockerfile:

- Uses `python:3.12-slim`.
- Installs packages from `requirements.txt`.
- Copies the application into `/home/user/app`.
- Runs as a non-root user.
- Starts `uvicorn src.main:app` on `0.0.0.0:7860`.

Build the image:
## Run With Docker

The Dockerfile:

- Uses `python:3.12-slim`.
- Installs packages from `requirements.txt`.
- Copies the application into `/home/user/app`.
- Runs as a non-root user.
- Starts `uvicorn src.main:app` on `0.0.0.0:7860`.

Build the image:

```bash
docker build -t store-management .
```

Run the container with your environment file:

```bash
docker run --rm --env-file .env -p 7860:7860 store-management
```

Run the container with your environment file:

```bash
docker run --rm --env-file .env -p 7860:7860 store-management
```

Open:

```text
http://localhost:7860
```

Important: this Docker image runs the FastAPI app only. PostgreSQL must be reachable through `DATABASE_URL`; the container does not start a local Postgres service.

The `.dockerignore` file excludes `.env`, so secrets are not copied into the image. Pass them at runtime with `--env-file .env` locally, or configure them as platform secrets in production.

## Hugging Face Spaces

This repository includes Hugging Face Spaces front matter for Docker:
Open:

```text
http://localhost:7860
```

Important: this Docker image runs the FastAPI app only. PostgreSQL must be reachable through `DATABASE_URL`; the container does not start a local Postgres service.

The `.dockerignore` file excludes `.env`, so secrets are not copied into the image. Pass them at runtime with `--env-file .env` locally, or configure them as platform secrets in production.

## Hugging Face Spaces

This repository includes Hugging Face Spaces front matter for Docker:

```yaml
sdk: docker
app_port: 7860
```

To deploy:

1. Create a Hugging Face Space with the Docker SDK.
2. Push this repository to the Space.
3. Add `DATABASE_URL` in the Space secrets.
4. Optionally add `COHERE_API_KEY` and `COHERE_MODEL` for the assistant.

The app listens on `0.0.0.0:7860`, which matches the Space configuration.

## Database

The schema file is [src/store_schema_postgres.sql](src/store_schema_postgres.sql). It creates:

- `products`
- `storage`
- `store_sales`
- `online_sales`
- `action_logs`

It also creates triggers for `store_sales` and `online_sales`. When a sale is inserted, PostgreSQL checks that the product exists, is active, and has enough stock, then deducts the sold quantity from `storage`.

Seed data is inserted for four sample products:

- Laptop Pro
- Smartphone X
- Headphones
- Smartwatch

## API Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Check API and database mode. |
| `GET` | `/api/dashboard` | Summary metrics for the dashboard. |
| `GET` | `/api/products` | List products with inventory and sales totals. |
| `GET` | `/api/products/{product_id}` | Get one product with inventory and sales totals. |
| `POST` | `/api/products` | Create a new product. |
| `PUT` | `/api/products/{product_id}` | Update a product name and price. |
| `PATCH` | `/api/products/{product_id}/status` | Activate or deactivate a product. |
| `DELETE` | `/api/products/{product_id}` | Permanently delete a product, related rows, and resequence remaining product IDs. |
| `GET` | `/api/inventory` | List inventory quantities. |
| `POST` | `/api/inventory` | Add stock for a product. |
| `PUT` | `/api/inventory` | Set a product stock quantity exactly. |
| `DELETE` | `/api/inventory/{product_id}` | Remove a product stock row. |
| `POST` | `/api/sales/store` | Record a physical store sale. |
| `POST` | `/api/sales/online` | Record an online sale. |
| `GET` | `/api/reports/sales` | Get sales and inventory report rows. |
| `POST` | `/api/chat` | Ask the optional database assistant a question. |

## Example API Requests

Create a product:

```bash
curl -X POST http://localhost:7860/api/products \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Keyboard\",\"price\":80}"
```

Add inventory:

```bash
curl -X POST http://localhost:7860/api/inventory \
  -H "Content-Type: application/json" \
  -d "{\"product_id\":1,\"quantity\":5}"
```

Record a store sale:

```bash
curl -X POST http://localhost:7860/api/sales/store \
  -H "Content-Type: application/json" \
  -d "{\"product_id\":1,\"quantity\":2}"
```

## Docker Readiness Notes

From the code, the project is Docker-ready for a single FastAPI web container. For the container to work at runtime, make sure:

- `DATABASE_URL` is configured.
- The PostgreSQL host allows connections from the container or hosting platform.
- The app can create/update the schema on startup using [src/store_schema_postgres.sql](src/store_schema_postgres.sql).
- `COHERE_API_KEY` is configured only if you want the assistant feature.
