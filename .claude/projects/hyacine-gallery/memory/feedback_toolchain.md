---
name: toolchain-preferences
description: Project toolchain preferences — pnpm for frontend, uv for Python, latest versions
type: feedback
---

Use pnpm (not npm/yarn) as the frontend package manager, and uv (not pip/poetry) as the Python package manager.
Target Python 3.14+ and Next.js 16 (latest).
WSL environment — never invoke Windows-side tools (e.g. Windows npm/node via /mnt paths).

**Why:** User explicitly set these preferences for the hyacine_gallery project. WSL environment is fresh, Windows tools are incompatible.

**How to apply:** All frontend commands should use `pnpm` instead of `npm`. All Python dependency/venv commands should use `uv`. Always check Linux-native tool availability, never fall back to Windows paths.
