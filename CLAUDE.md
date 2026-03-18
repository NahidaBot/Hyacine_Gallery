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
- Package managers: **pnpm** (frontend), **uv** (Python). Never use npm/pip directly.
- Environment: WSL (Arch Linux). Never invoke Windows-side tools.

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

Frontend

cd frontend
pnpm install
pnpm dev          # dev server on :3000
pnpm build        # production build
pnpm lint         # ESLint

Docker (full stack)

docker compose up -d                       # production
docker compose -f docker-compose.yml -f docker-compose.dev.yml up  # dev

Database Schema

5 tables with proper tag normalization:

- artworks — Core entity. platform + pid unique constraint for deduplication.
- artwork_images — Per-page image records (url_original, url_thumb, storage_path, telegram_file_id). FK → artworks.
- tags — Independent tag entity with name (unique), type (general/character/artist/meta), alias_of_id (self-referential for merging).
- artwork_tags — Many-to-many join table (artwork_id, tag_id composite PK).
- bot_post_logs — Bot posting history, decoupled from artworks. Supports multi-bot/multi-channel.

API Routes

Public (gallery frontend)

- GET /api/artworks — Paginated list (?tag=&platform=&q=&page=&page_size=)
- GET /api/artworks/:id — Artwork detail (with images + tags)
- GET /api/artworks/random — Random artwork
- GET /api/tags — Tag list with counts (?type= filter)
- GET /api/tags/:name — Single tag detail
- GET /api/tags/:name/artworks — Artworks under a tag

Admin (requires X-Admin-Token header)

- POST /api/admin/artworks — Create artwork
- PUT /api/admin/artworks/:id — Update artwork
- DELETE /api/admin/artworks/:id — Delete artwork
- POST /api/admin/tags — Create tag
- PUT /api/admin/tags/:id — Update tag
- DELETE /api/admin/tags/:id — Delete tag

Current Status & Next Steps

Done

- Project skeleton (backend, frontend, bot worker, docker-compose)
- Database models with normalized tag system
- Pydantic schemas (request/response)
- Service layer (artwork CRUD, tag CRUD, get-or-create tags)
- API routes (public + admin)
- Frontend pages (gallery grid, artwork detail, tags)
- Frontend types and API client aligned with backend

Next

- Fix frontend Google Fonts issue (switch to local fonts or skip)
- Git initial commit (need git user config first)
- Set up PostgreSQL and run first Alembic migration
- Implement crawlers (Pixiv, Twitter, MiYouShe, BiliBili via gallery-dl)
- Import endpoint (POST /api/admin/artworks/import) — URL → crawler → create artwork
- Image storage service (local + S3)
- Admin panel frontend (/panel/[slug]/)
- Migrate Telegram bot handlers to use backend API
- Thumbnail generation pipeline