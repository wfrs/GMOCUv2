"""Database import inspection, activation, and live job progress helpers."""

from __future__ import annotations

import shutil
import sqlite3
import threading
import uuid
from datetime import datetime, UTC
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from ..bootstrap import ensure_database_ready, prepare_runtime_database
from ..migrations import CURRENT_SCHEMA_VERSION, inspect_database

COUNT_TABLE_CANDIDATES = {
    "plasmids": ("plasmids", "Plasmids"),
    "features": ("features", "Features"),
    "organisms": ("organisms", "Organisms"),
    "gmos": ("gmos", "GMOs"),
    "cassettes": ("cassettes", "Cassettes"),
    "attachments": ("attachments", "Attachments"),
    "organism_selections": ("organism_selections", "OrganismSelection"),
    "organism_favourites": ("organism_favourites", "OrganismFavourites"),
}

_IMPORT_JOBS: dict[str, dict[str, Any]] = {}
_IMPORT_JOBS_LOCK = threading.Lock()


def inspect_uploaded_database(
    *,
    filename: str,
    contents: bytes,
    destination_path: str,
) -> dict[str, Any]:
    temp_path = _write_temp_database(contents, Path(destination_path).parent)
    try:
        return _build_import_report(
            db_path=temp_path,
            filename=filename,
            file_size_bytes=len(contents),
            destination_path=destination_path,
        )
    finally:
        temp_path.unlink(missing_ok=True)


def activate_uploaded_database(
    *,
    filename: str,
    contents: bytes,
    destination_path: str,
) -> dict[str, Any]:
    temp_path = _write_temp_database(contents, Path(destination_path).parent)
    import_report = _build_import_report(
        db_path=temp_path,
        filename=filename,
        file_size_bytes=len(contents),
        destination_path=destination_path,
    )
    try:
        return _activate_database_from_temp(
            temp_path=temp_path,
            import_report=import_report,
            destination_path=destination_path,
        )
    finally:
        temp_path.unlink(missing_ok=True)


def create_import_job(
    *,
    filename: str,
    contents: bytes,
    destination_path: str,
) -> dict[str, Any]:
    temp_path = _write_temp_database(contents, Path(destination_path).parent)
    import_report = _build_import_report(
        db_path=temp_path,
        filename=filename,
        file_size_bytes=len(contents),
        destination_path=destination_path,
    )

    job_id = uuid.uuid4().hex
    steps = [
        {**step, "status": "pending", "started_at": None, "finished_at": None}
        for step in import_report["planned_steps"]
    ]
    job = {
        "job_id": job_id,
        "status": "queued",
        "error": None,
        "report": import_report,
        "result": None,
        "active_step_id": None,
        "steps": steps,
        "created_at": _now(),
        "started_at": None,
        "finished_at": None,
        "_temp_path": str(temp_path),
        "_destination_path": destination_path,
    }

    with _IMPORT_JOBS_LOCK:
        _IMPORT_JOBS[job_id] = job

    thread = threading.Thread(target=_run_import_job, args=(job_id,), daemon=True)
    thread.start()
    return _public_job(job)


def get_import_job(job_id: str) -> dict[str, Any]:
    with _IMPORT_JOBS_LOCK:
        job = _IMPORT_JOBS.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return _public_job(job)


def _run_import_job(job_id: str) -> None:
    with _IMPORT_JOBS_LOCK:
        job = _IMPORT_JOBS[job_id]
        job["status"] = "running"
        job["started_at"] = _now()

    try:
        _complete_step(job_id, "inspect")

        validation_step = "migrate" if job["report"]["inspection"]["kind"] == "legacy" else "validate"
        _start_step(job_id, validation_step)
        ensure_database_ready(job["_temp_path"])
        _complete_step(job_id, validation_step)

        _start_step(job_id, "backup")
        backup_path = _backup_active_database(job["_destination_path"])
        _complete_step(job_id, "backup")

        _start_step(job_id, "activate")
        shutil.move(job["_temp_path"], job["_destination_path"])
        job["_temp_path"] = None
        _complete_step(job_id, "activate")

        _start_step(job_id, "bootstrap")
        prepare_runtime_database(job["_destination_path"])
        _complete_step(job_id, "bootstrap")

        destination = Path(job["_destination_path"])
        activated_report = _build_import_report(
            db_path=destination,
            filename=destination.name,
            file_size_bytes=destination.stat().st_size if destination.exists() else None,
            destination_path=job["_destination_path"],
        )
        completed_steps = [
            step["label"]
            for step in job["steps"]
            if step["status"] == "completed"
        ]

        result = {
            "status": "ok",
            "message": "Database replaced successfully",
            "backup_path": backup_path,
            "import_report": job["report"],
            "activated_report": activated_report,
            "completed_steps": completed_steps,
        }
        with _IMPORT_JOBS_LOCK:
            live_job = _IMPORT_JOBS[job_id]
            live_job["status"] = "completed"
            live_job["result"] = result
            live_job["active_step_id"] = None
            live_job["finished_at"] = _now()
    except Exception as exc:
        with _IMPORT_JOBS_LOCK:
            live_job = _IMPORT_JOBS[job_id]
            active_step_id = live_job["active_step_id"]
            if active_step_id:
                _mark_step(live_job, active_step_id, "failed")
            live_job["status"] = "failed"
            live_job["error"] = str(exc)
            live_job["finished_at"] = _now()
            live_job["active_step_id"] = None
    finally:
        with _IMPORT_JOBS_LOCK:
            temp_path = _IMPORT_JOBS[job_id].get("_temp_path")
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def _activate_database_from_temp(
    *,
    temp_path: Path,
    import_report: dict[str, Any],
    destination_path: str,
) -> dict[str, Any]:
    ensure_database_ready(str(temp_path))
    backup_path = _backup_active_database(destination_path)
    shutil.move(str(temp_path), destination_path)
    prepare_runtime_database(destination_path)

    destination = Path(destination_path)
    activated_report = _build_import_report(
        db_path=destination,
        filename=destination.name,
        file_size_bytes=destination.stat().st_size if destination.exists() else None,
        destination_path=destination_path,
    )
    return {
        "status": "ok",
        "message": "Database replaced successfully",
        "backup_path": backup_path,
        "import_report": import_report,
        "activated_report": activated_report,
        "completed_steps": [step["label"] for step in import_report["planned_steps"]],
    }


def _backup_active_database(destination_path: str) -> str | None:
    destination = Path(destination_path)
    if not destination.exists():
        return None
    backup = destination.with_suffix(".db.bak")
    shutil.copy2(destination, backup)
    return str(backup)


def _write_temp_database(contents: bytes, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        dir=str(directory),
        prefix="gmocu-upload-",
        suffix=".db",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(contents)
    return temp_path


def _build_import_report(
    *,
    db_path: Path,
    filename: str,
    file_size_bytes: int | None,
    destination_path: str,
) -> dict[str, Any]:
    inspection = inspect_database(str(db_path))
    counts = _collect_counts(db_path)

    return {
        "filename": filename,
        "file_size_bytes": file_size_bytes,
        "destination_path": destination_path,
        "inspection": {
            "kind": inspection.kind,
            "legacy_version": inspection.legacy_version,
            "schema_version": inspection.schema_version,
            "target_schema_version": CURRENT_SCHEMA_VERSION,
        },
        "counts": counts,
        "planned_steps": _planned_steps(inspection.kind),
    }


def _collect_counts(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    try:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table';"
            ).fetchall()
        }
        counts: dict[str, int] = {}
        for key, candidates in COUNT_TABLE_CANDIDATES.items():
            table_name = next((name for name in candidates if name in table_names), None)
            if table_name is None:
                counts[key] = 0
                continue
            counts[key] = int(
                conn.execute(f'SELECT COUNT(*) FROM "{table_name}";').fetchone()[0]
            )
        return counts
    finally:
        conn.close()


def _planned_steps(kind: str) -> list[dict[str, str]]:
    steps = [
        {
            "id": "inspect",
            "label": "Inspect uploaded database",
            "detail": "Read the schema, detect the version, and count imported records.",
        },
    ]

    if kind == "legacy":
        steps.append(
            {
                "id": "migrate",
                "label": "Migrate legacy schema to GMOCU v2",
                "detail": "Convert old legacy tables and columns into the current v2 schema.",
            }
        )
    else:
        steps.append(
            {
                "id": "validate",
                "label": "Validate current schema",
                "detail": "Confirm the uploaded database is already in a usable v2 format.",
            }
        )

    steps.extend(
        [
            {
                "id": "backup",
                "label": "Backup current active database",
                "detail": "Create a safety copy of the currently active v2 database before replacing it.",
            },
            {
                "id": "activate",
                "label": "Activate imported database",
                "detail": "Replace the active database file with the imported database.",
            },
            {
                "id": "bootstrap",
                "label": "Reinitialize runtime state",
                "detail": "Seed defaults if needed and reopen the runtime against the imported database.",
            },
        ]
    )
    return steps


def _start_step(job_id: str, step_id: str) -> None:
    with _IMPORT_JOBS_LOCK:
        job = _IMPORT_JOBS[job_id]
        job["active_step_id"] = step_id
        _mark_step(job, step_id, "running")


def _complete_step(job_id: str, step_id: str) -> None:
    with _IMPORT_JOBS_LOCK:
        job = _IMPORT_JOBS[job_id]
        _mark_step(job, step_id, "completed")
        if job["active_step_id"] == step_id:
            job["active_step_id"] = None


def _mark_step(job: dict[str, Any], step_id: str, status: str) -> None:
    timestamp = _now()
    for step in job["steps"]:
        if step["id"] != step_id:
            continue
        if step["started_at"] is None:
            step["started_at"] = timestamp
        step["status"] = status
        if status in {"completed", "failed"}:
            step["finished_at"] = timestamp
        return


def _public_job(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "error": job["error"],
        "report": job["report"],
        "result": job["result"],
        "active_step_id": job["active_step_id"],
        "steps": [
            {
                "id": step["id"],
                "label": step["label"],
                "detail": step["detail"],
                "status": step["status"],
                "started_at": step["started_at"],
                "finished_at": step["finished_at"],
            }
            for step in job["steps"]
        ],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
    }


def _now() -> str:
    return datetime.now(UTC).isoformat()
