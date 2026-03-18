# Hyacine Gallery

Full-stack image gallery application with web frontend, admin panel, multi-platform crawlers, and multi-bot integration.

## Tech Stack

- **Backend**: Python 3.14+, FastAPI, SQLAlchemy (async), Alembic, uv, Ruff, mypy
- **Frontend**: Next.js 16 (App Router), TypeScript (strict), Tailwind CSS 4, React 19, pnpm
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Bots**: python-telegram-bot (independent worker process)
- **Crawlers**: gallery-dl + platform-specific API clients (httpx)
- **Deployment**: Docker Compose

## Project Structure

- `backend/` — FastAPI backend (Python)
- `frontend/` — Next.js frontend (TypeScript)
- `bots/telegram/` — Telegram bot worker (Python)
- `docker-compose.yml` — Production services
- `docker-compose.dev.yml` — Development overrides

## Conventions

- Python: snake_case files/variables/functions, PascalCase classes. Ruff for lint+format, mypy strict.
- TypeScript: PascalCase component files, camelCase others. ESLint + Prettier.
- API routes: kebab-case plural nouns (`/api/artworks`).
- DB tables: snake_case plural (`artworks`, `artwork_tags`).
- Git: conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).
- Branches: `feat/short-desc`, `fix/short-desc` from `dev`.

## Commands

### Backend
```bash
cd backend
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn app.main:app --reload              # dev server on :8000
alembic upgrade head                       # run migrations
alembic revision --autogenerate -m "msg"   # create migration
ruff check . && ruff format .              # lint + format
mypy app/                                  # type check
```

### Frontend
```bash
cd frontend
pnpm install
pnpm dev          # dev server on :3000
pnpm build        # production build
pnpm lint         # ESLint
```

### Docker (full stack)
```bash
docker compose up -d                       # production
docker compose -f docker-compose.yml -f docker-compose.dev.yml up  # dev
```
