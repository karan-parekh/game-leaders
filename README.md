# Game Leaders

Game Leaders is a mobile-first live score tracker for local board-game groups. It uses a FastAPI backend, PostgreSQL persistence, SSE session updates, and a React/Vite frontend.

## Local development

Install Python dependencies and run the API:

```sh
uv sync --dev
uv run uvicorn app.main:app --reload
```

Run the full local topology with Docker:

```sh
docker compose up --build
```

The API is available at `http://localhost:8000`; the frontend is available at `http://localhost:5173`. Redis is available only in the optional scaling profile:

```sh
docker compose --profile scale up --build
```

Run tests with:

```sh
PYTHONPATH=. .venv/bin/pytest -q
```

The first version keeps PostgreSQL as the source of truth and uses an in-process SSE hub. Redis cache-aside reads and pub/sub fanout are intentionally deferred until read and deployment measurements justify them.
