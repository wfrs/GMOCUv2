# GMOCU Backend

FastAPI backend for the GMOCU web application.

## Stack

- FastAPI
- SQLAlchemy
- SQLite
- pandas / openpyxl / xlsxwriter for import and export workflows

## Layout

- `app/main.py`: app entrypoint
- `app/models.py`: SQLAlchemy models for the v2 schema
- `app/migrations.py`: legacy database inspection and migration
- `app/routers/`: HTTP routes
- `app/application/`: service-layer business logic
- `tests/`: backend tests

## Environment

Use the repo-root virtualenv:

```bash
source ../.venv/bin/activate
```

Install/update backend dependencies:

```bash
../.venv/bin/pip install -e ".[dev]"
```

## Run

```bash
../.venv/bin/uvicorn app.main:app --reload
```

Docs are exposed at:

- `http://localhost:8000/api/docs`

## Test

```bash
env PYTHONPYCACHEPREFIX=/tmp/pycache ../.venv/bin/pytest -q
```

## Database Behavior

- The backend uses `~/GMOCU/gmocu-v2.db` by default.
- The legacy app keeps using `~/GMOCU/gmocu.db`, so the v2 backend no longer shares the same default filename.
- Set `GMOCU_DATABASE` to point to a different database file.
- Legacy GMOCU databases are migrated into the current schema automatically.
- Database upload through the API validates and migrates the file before activation.

## Notes

- The backend is designed as a small monolith, not a multi-service system.
- `core.py` is kept only as a compatibility facade; active behavior lives in `app/application/`.
