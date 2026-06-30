---
title: Store Management FastAPI
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
---

# Store Management FastAPI

A Docker-ready store management app for Hugging Face Spaces. The old Telegram bot and Gradio UI have been replaced with:

- FastAPI backend under `/api`
- Vanilla HTML, CSS, and JavaScript frontend served from `/`
- SQLite database initialization on startup
- Optional Cohere/LangChain SQL assistant when `COHERE_API_KEY` is configured

## Run Locally

```bash
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 7860
```

Open `http://localhost:7860`.

## Docker

```bash
docker build -t store-management .
docker run --rm -p 7860:7860 store-management
```

## Hugging Face Space

Create a Space with Docker SDK or keep this README front matter:

```yaml
sdk: docker
app_port: 7860
```

Then push the repository. The app listens on `0.0.0.0:7860`.

Runtime secrets can be added from the Space settings. Add `COHERE_API_KEY` only if you want to enable the Database Assistant tab.

## Persistence

The app automatically uses `/data/store.db` when a writable `/data` directory is available in the Space. Otherwise, it creates `src/store.db` inside the container. For long-term persistence on Hugging Face Spaces, attach persistent storage or use an external database.

## API

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/products`
- `POST /api/products`
- `PATCH /api/products/{product_id}/status`
- `GET /api/inventory`
- `POST /api/inventory`
- `POST /api/sales/store`
- `POST /api/sales/online`
- `GET /api/reports/sales`
- `POST /api/chat`
