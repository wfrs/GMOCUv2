# GMOCU

GMOCU is a local-first plasmid database and GMO documentation application.

The current codebase is a web rewrite of the legacy desktop application:

- `frontend/`: React + TypeScript + Vite UI
- `backend/`: FastAPI + SQLAlchemy backend
- `legacy/`: legacy desktop code kept for reference and migration support
- `example/`: sample databases and import files

## Current State

This repo now runs on a native v2 backend schema with built-in migration from legacy GMOCU database files.

Key points:

- legacy `.db` files are accepted and upgraded into the current schema
- the backend uses Python/FastAPI and SQLite
- the frontend talks to a v2 API with consistent field naming
- backend tests, frontend lint, frontend build, and CI are in place

## Quick Start

### 1. Python environment

Use the repo-root virtualenv:

```bash
source .venv/bin/activate
```

If it does not exist yet:

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e "./backend[dev]"
```

### 2. Frontend dependencies

```bash
cd frontend
npm ci
```

### 3. Run the app

Backend:

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

Default frontend URL:

- `http://localhost:5173`

Default backend API URL:

- `http://localhost:8000/api`

## Common Commands

Backend tests:

```bash
cd backend
env PYTHONPYCACHEPREFIX=/tmp/pycache ../.venv/bin/pytest -q
```

Frontend lint:

```bash
cd frontend
npm run lint
```

Frontend production build:

```bash
cd frontend
npm run build
```

## Database Notes

- Runtime storage is a local SQLite database.
- The backend can migrate legacy GMOCU databases during startup or upload.
- The active user database defaults to `~/GMOCU/gmocu-v2.db`.
- The legacy desktop app still uses `~/GMOCU/gmocu.db`, so the filenames are now separated on purpose.
- Example databases in `example/` are useful for testing migration paths.

## Repository Guide

- [backend/README.md](/Users/wfrs/code/gmocu/gmocu/backend/README.md): backend setup, tests, API/dev notes
- [frontend/README.md](/Users/wfrs/code/gmocu/gmocu/frontend/README.md): frontend setup, lint, build, and dev notes

## CI

GitHub Actions runs:

- backend tests
- frontend lint
- frontend build

Workflow file:

- [.github/workflows/ci.yml](/Users/wfrs/code/gmocu/gmocu/.github/workflows/ci.yml)

## Git Workflow

### Conventional commits

Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
feat: add new feature
fix: correct a bug
chore: maintenance, dependency updates, tooling
docs: documentation only
refactor: code change with no behaviour change
```

### Automatic versioning

A `commit-msg` hook automatically bumps the app version based on the commit prefix:

| Prefix | Bump | Example |
|--------|------|---------|
| `feat:` | MINOR (x.**Y**.0) | 2.2.0 → 2.3.0 |
| `fix:` | PATCH (x.y.**Z**) | 2.2.0 → 2.2.1 |
| anything else | none | — |

The hook updates `backend/app/config.py`, `backend/pyproject.toml`, and `frontend/package.json` in the same commit — no separate version bump commits needed.

The hooks live in `.githooks/`. After cloning, activate them once with:

```bash
git config core.hooksPath .githooks
```
