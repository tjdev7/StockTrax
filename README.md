# 📈 Stock Tracker

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Stock Tracker** is a production-ready web service for managing a stock watchlist, fetching current prices with caching, and streaming real-time price updates over WebSockets. It is built with **FastAPI**, **SQLAlchemy + SQLite**, and **yfinance**, and is designed for **zero-downtime** deployments with multiple workers, health checks, and graceful shutdowns.

A single-page dashboard is bundled and served directly by the app — no separate frontend build required.

---

## ✨ Features

- **Watchlist management** — add/remove tickers, persisted in SQLite
- **Current price API** — 30-second TTL cache with `?force=true` to bypass
- **Real-time WebSocket streaming** — pushes price updates every 5 seconds per symbol
- **Bundled dashboard** — auto-reconnecting, multi-symbol WebSocket client at `/static/index.html`
- **Zero-downtime ready** — Gunicorn + Uvicorn workers, graceful shutdown, `/health` endpoint
- **Portable storage** — DB path anchored to project root, overridable via `DATABASE_URL`
- **Docker + Compose support** — one command to run locally or in production
- **Interactive docs** — Swagger UI at `/docs`, ReDoc at `/redoc`

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn (ASGI) |
| ORM | SQLAlchemy 2.x |
| Database | SQLite (swap for PostgreSQL via `DATABASE_URL`) |
| Price data | yfinance (Yahoo Finance) |
| Caching | cachetools (TTL cache) |
| WebSockets | Native FastAPI support |
| Production server | Gunicorn (Uvicorn workers) |
| Container | Docker + Docker Compose |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- `pip` and `venv`
- (Optional) Docker and Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/stock-tracker.git
cd stock-tracker
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the development server (auto-reload)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open the dashboard

Visit **http://localhost:8000/static/index.html**

> The root URL `/` returns 404 by design — there is no handler for it. The
> dashboard lives at `/static/index.html` and the API docs at `/docs`.

---

## 📁 Project Structure

```
stock_tracker/
├── main.py                 # FastAPI app, routes, WebSocket endpoint
├── database.py             # SQLAlchemy engine, session, StockDB model
├── models.py               # Pydantic request/response schemas
├── stock_service.py        # yfinance integration + TTL price cache
├── websocket_manager.py    # WebSocket connection registry + broadcast
├── static/
│   └── index.html          # Bundled dashboard (vanilla JS)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── render.yaml             # Render Blueprint for one-click deploy
├── .env.example
├── README.md
└── stocks.db               # Created at first startup (git-ignored)
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check — returns `{"status":"ok"}` |
| `POST` | `/stocks` | Add a ticker (body: `{"symbol":"AAPL"}`) |
| `GET` | `/stocks` | List all tracked tickers |
| `DELETE` | `/stocks/{symbol}` | Remove a ticker from the watchlist |
| `GET` | `/stocks/{symbol}/price` | Current price (cached 30s; use `?force=true` to refresh) |
| `WS` | `/ws/{symbol}` | Price stream — pushes updates every 5 seconds |

### Example requests

```bash
# Add AAPL
curl -X POST http://localhost:8000/stocks \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL"}'

# List watchlist
curl http://localhost:8000/stocks

# Get price (cached)
curl http://localhost:8000/stocks/AAPL/price

# Get price (force refresh)
curl "http://localhost:8000/stocks/AAPL/price?force=true"

# Remove
curl -X DELETE http://localhost:8000/stocks/AAPL
```

### WebSocket example

```javascript
// Browser console
const ws = new WebSocket("ws://localhost:8000/ws/AAPL");
ws.onmessage = (e) => console.log("Price:", e.data);
```

Or from the command line with [websocat](https://github.com/vi/websocat):

```bash
websocat ws://localhost:8000/ws/AAPL
```

---

## 🖥️ Dashboard

The bundled dashboard at `static/index.html`:

- Fetches the watchlist from `GET /stocks`
- Opens **one WebSocket per symbol** and updates prices in real time
- **Auto-reconnects** after 3 seconds if a socket drops
- Shows a green/red connection indicator per card
- Supports add/remove directly from the UI

No build step, no Node.js, no npm — just serve it from FastAPI.

---

## 🐳 Running with Docker

```bash
# Build and start
docker-compose up --build -d

# Tail logs
docker-compose logs -f

# Stop
docker-compose down
```

The service listens on `http://localhost:8000`. The SQLite file is persisted
via a bind mount (`./stocks.db:/app/stocks.db`).

---

## 🔄 Zero-Downtime Deployments

### Gunicorn (recommended production start command)

```bash
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --graceful-timeout 30 \
  --timeout 60 \
  --preload
```

When you send `SIGTERM` to the master process, each worker finishes its
in-flight requests before exiting — no dropped connections.

### Rolling updates with a reverse proxy

For true zero-downtime during deploys, put **Nginx** or **Traefik** in front
of two or more app instances. The proxy health-checks each backend and only
routes to healthy ones; you then start a new instance, wait for `/health`,
and drain the old one.

Minimal Nginx upstream example:

```nginx
upstream stock_api_backend {
    least_conn;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;
    keepalive 64;
}

server {
    listen 80;
    server_name your_domain.com;

    location /ws/ {
        proxy_pass http://stock_api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 600s;
    }

    location / {
        proxy_pass http://stock_api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Reload gracefully with `nginx -t && systemctl reload nginx` — no dropped
requests. Traefik users can skip the config file entirely and use Docker
labels for automatic service discovery.

---

## ☁️ Deploying to Render

This repo includes a `render.yaml` Blueprint for one-click deployment.

### Steps

1. Push the project to GitHub.
2. In the Render dashboard, click **New + → Blueprint** and select your repo.
3. Render reads `render.yaml` and provisions the service automatically.

### `render.yaml` (included)

```yaml
services:
  - type: web
    name: stock-tracker
    runtime: python
    plan: starter          # Paid plan required for persistent disks
    region: oregon
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --preload
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      # Uncomment when a persistent disk is attached:
      # - key: DATABASE_URL
      #   value: sqlite:////var/data/stocks.db
    # disk:
    #   name: stock-tracker-data
    #   mountPath: /var/data
    #   sizeGB: 1
```

### ⚠️ Important notes for Render

- **Persistent disk required for SQLite.** Without one, `stocks.db` is lost
  on every deploy. Attaching a disk is a paid-plan feature and pins you to a
  **single instance** (disks can't be shared across servers).
- **Free tier spins down** after 15 minutes of inactivity. Your WebSocket
  clients will disconnect and the next request triggers a cold start.
- **WebSockets are fully supported** on Render web services.

---

## ⚙️ Configuration

All settings are read from environment variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///<project_root>/stocks.db` | Full SQLAlchemy connection string. Use `sqlite:////absolute/path.db` (four slashes) for absolute paths, or a PostgreSQL URL. |
| `PYTHON_VERSION` | — | Read by Render to select the Python runtime |

Copy `.env.example` to `.env` for local overrides:

```bash
cp .env.example .env
```

---

## 🧯 Troubleshooting

### `ModuleNotFoundError: No module named 'cachetools'`

Missing dependency. Install it and add to `requirements.txt`:

```bash
pip install cachetools
# add to requirements.txt:
# cachetools==5.5.0
```

### `sqlite3.OperationalError: unable to open database file`

The DB path couldn't be resolved or written. Three common causes:

1. **Relative path issue** — `database.py` anchors the path to the file's
   own directory (`Path(__file__).resolve().parent`), so this should not
   occur with the current version. If you customized the path, make sure
   it's absolute.
2. **macOS TCC / privacy protection** — if the project lives under
   `~/Documents`, `~/Desktop`, `~/Downloads`, or `~/Library`, macOS can
   silently block writes from Terminal-launched processes. Either move the
   project to `~/code` (or similar), or grant **Full Disk Access** to
   Terminal in *System Settings → Privacy & Security*, then fully restart
   Terminal.
3. **Directory permissions** — verify with `touch stocks.db && rm stocks.db`.
   If that fails, fix with `chmod u+w .`.

### `NameError: name 'Column' is not defined`

`database.py` is missing the SQLAlchemy imports. The import line must be:

```python
from sqlalchemy import create_engine, Column, String, DateTime
```

Not just `create_engine`.

### `GET /` returns 404

Expected — there is no root route. Use `/static/index.html` for the
dashboard or `/docs` for the API explorer.

### `yfinance` returns empty data

Yahoo Finance occasionally rate-limits or changes its API. The service
returns `404 Price not available` when this happens. Retry with
`?force=true`, or consider swapping in a paid data provider.

---

## 🧪 Testing

Tests aren't included yet, but the app is easy to exercise:

```bash
pip install pytest httpx
pytest tests/
```

Suggested coverage: `/health`, add/list/delete flow, price caching
behavior, WebSocket handshake.

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -am 'Add feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com) — modern, fast web framework
- [yfinance](https://github.com/ranaroussi/yfinance) — free stock data
- [SQLAlchemy](https://www.sqlalchemy.org) — Python SQL toolkit
- [cachetools](https://github.com/tkem/cachetools) — TTL caching

---

## 📬 Contact

Open an issue or reach out at [your-email@example.com](mailto:your-email@example.com).

**Happy tracking! 📊**