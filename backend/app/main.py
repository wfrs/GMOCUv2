"""GMOCU 2.0 — FastAPI backend."""

import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from .bootstrap import prepare_runtime_database
from .config import APP_NAME, VERSION, DATABASE_PATH
from .routers import plasmids, features, organisms, settings, organism_selections, ice_credentials


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
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        dir=str(DATABASE_PATH.parent),
        prefix="gmocu-upload-",
        suffix=".db",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(contents)

    try:
        # Validate and migrate the upload before it becomes the active database.
        prepare_runtime_database(str(temp_path))

        # Backup current database if it exists.
        if DATABASE_PATH.exists():
            backup = DATABASE_PATH.with_suffix(".db.bak")
            shutil.copy2(DATABASE_PATH, backup)

        shutil.move(str(temp_path), DATABASE_PATH)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    # Re-initialize runtime state against the activated database file.
    prepare_runtime_database(str(DATABASE_PATH))

    return {"status": "ok", "message": "Database replaced successfully"}
