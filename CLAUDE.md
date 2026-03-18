# Hyacine Gallery

Full-stack image gallery application with web frontend, admin panel, multi-platform crawlers, and multi-bot integration.

## Tech Stack

- **Backend**: Python 3.14+, FastAPI, SQLAlchemy (async), Alembic, uv, Ruff, mypy
- **Frontend**: Next.js 16 (App Router), TypeScript (strict), Tailwind CSS 4, React 19, pnpm
- **Database**: SQLite (dev) / PostgreSQL 16 (prod)
- **Cache/Queue**: Redis 7
- **Bots**: python-telegram-bot (independent worker process)
- **Crawlers**: Pixiv API, fxtwitter API, gallery-dl (generic fallback)
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
- Git: conventional commits with gitmoji (`:gitmoji: type: description`).
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
```

### Frontend
```bash
cd frontend
pnpm install
pnpm dev          # dev server on :3000
pnpm build        # production build
pnpm lint         # ESLint
```

### Telegram Bot
```bash
cd bots/telegram
uv venv && source .venv/bin/activate
uv pip install -e "."
python -m main    # start bot polling
```

### Docker (full stack)
```bash
docker compose up -d                       # production
docker compose -f docker-compose.yml -f docker-compose.dev.yml up  # dev
```

## Database Schema

5 tables with proper tag normalization:

- **artworks** — Core entity. platform + pid unique constraint for deduplication.
- **artwork_images** — Per-page image records (url_original, url_thumb, storage_path, telegram_file_id). FK → artworks.
- **tags** — Independent tag entity with name (unique), type (general/character/artist/meta), alias_of_id (self-referential for merging).
- **artwork_tags** — Many-to-many join table (artwork_id, tag_id composite PK).
- **bot_post_logs** — Bot posting history, decoupled from artworks. Supports multi-bot/multi-channel.

## API Routes

### Public (gallery frontend)

- GET /api/artworks — Paginated list (?tag=&platform=&q=&page=&page_size=)
- GET /api/artworks/:id — Artwork detail (with images + tags)
- GET /api/artworks/random — Random artwork
- GET /api/tags — Tag list with counts (?type= filter)
- GET /api/tags/:name — Single tag detail
- GET /api/tags/:name/artworks — Artworks under a tag

### Admin (requires X-Admin-Token header)

- POST /api/admin/artworks — Create artwork
- POST /api/admin/artworks/import — Import artwork by URL (crawl → dedup → create)
- PUT /api/admin/artworks/:id — Update artwork
- DELETE /api/admin/artworks/:id — Delete artwork
- POST /api/admin/tags — Create tag
- PUT /api/admin/tags/:id — Update tag
- DELETE /api/admin/tags/:id — Delete tag

## Crawlers

Dispatcher in `backend/app/crawlers/__init__.py` — first match wins:

1. **PixivCrawler** — `pixiv.net/artworks/*`, `phixiv.net/artworks/*` via Ajax API
2. **TwitterCrawler** — `twitter.com`, `x.com`, `fxtwitter.com`, `vxtwitter.com` via fxtwitter API
3. **GalleryDLCrawler** — Fallback for any URL, requires `gallery-dl` installed

## Frontend Pages

- `/` — Gallery grid (paginated)
- `/artwork/:id` — Artwork detail (images, tags, source link)
- `/tags` — Tag list with artwork counts
- `/panel/:slug/` — Admin dashboard
- `/panel/:slug/artworks` — Artwork management (list, search, import, delete)
- `/panel/:slug/artworks/:id` — Artwork edit (title, author, tags, flags)
- `/panel/:slug/tags` — Tag management (create, inline edit, delete)

## Telegram Bot Commands

- `/import <url> [#tag1 #tag2] [--post]` — Crawl URL and save artwork (admin only)
- `/post <artwork_id>` — Post artwork to channel (admin only)
- `/random` — Get a random artwork
- `/help` — Show available commands

## Current Status & Next Steps

### Done

- Project skeleton (backend, frontend, bot worker, docker-compose)
- Database models with normalized tag system + Alembic initial migration
- SQLite for development, PostgreSQL for production
- Pydantic schemas (request/response)
- Service layer (artwork CRUD, tag CRUD, get-or-create tags)
- API routes (public + admin + import)
- Crawlers (Pixiv, Twitter, gallery-dl fallback)
- Frontend pages (gallery grid, artwork detail, tags)
- Frontend admin panel (artworks CRUD, tags CRUD, URL import)
- Telegram bot handlers (import, post to channel, random)

### Next

- Image storage service (local + S3)
- Thumbnail generation pipeline
- MiYouShe / BiliBili crawlers
- Bot post logging (record to bot_post_logs)
- Search improvements (full-text search)
