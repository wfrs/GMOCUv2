"""GMOCU 2.0 — FastAPI backend."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .application.database_import import (
    activate_uploaded_database,
    create_import_job,
    get_import_job,
    inspect_uploaded_database,
)
from .bootstrap import prepare_runtime_database
from .config import APP_NAME, VERSION, DATABASE_PATH
from .routers import plasmids, features, organisms, settings, organism_selections, ice_credentials, activity_logs, reports


@asynccontextmanager
async def lifespan(_: FastAPI):
    prepare_runtime_database(str(DATABASE_PATH))
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        version=VERSION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Vite dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(plasmids.router, prefix="/api")
    app.include_router(features.router, prefix="/api")
    app.include_router(organisms.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    app.include_router(organism_selections.router, prefix="/api")
    app.include_router(ice_credentials.router, prefix="/api")
    app.include_router(activity_logs.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    return app


app = create_app()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": VERSION,
        "database": str(DATABASE_PATH),
    }


@app.post("/api/database/upload")
async def upload_database(file: UploadFile = File(...)):
    """Replace the current database with an uploaded .db file.

    The old database is backed up before overwriting.
    """
    if not file.filename or not file.filename.endswith(".db"):
        return {"error": "File must be a .db file"}

    contents = await file.read()
    return activate_uploaded_database(
        filename=file.filename,
        contents=contents,
        destination_path=str(DATABASE_PATH),
    )


@app.post("/api/database/inspect")
async def inspect_database_upload(file: UploadFile = File(...)):
    """Inspect an uploaded .db file before import."""
    if not file.filename or not file.filename.endswith(".db"):
        return {"error": "File must be a .db file"}

    contents = await file.read()
    return inspect_uploaded_database(
        filename=file.filename,
        contents=contents,
        destination_path=str(DATABASE_PATH),
    )


@app.post("/api/database/import-jobs")
async def create_database_import_job(file: UploadFile = File(...)):
    """Create a live database import job for an uploaded .db file."""
    if not file.filename or not file.filename.endswith(".db"):
        return {"error": "File must be a .db file"}

    contents = await file.read()
    return create_import_job(
        filename=file.filename,
        contents=contents,
        destination_path=str(DATABASE_PATH),
    )


@app.get("/api/database/import-jobs/{job_id}")
def get_database_import_job(job_id: str):
    """Return live status for a database import job."""
    try:
        return get_import_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Import job not found") from exc
