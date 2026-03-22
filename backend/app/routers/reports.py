"""Reports API routes — Formblatt Z download and validation."""

import io
import sqlite3
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..application import reports as reports_service
from ..application import validation as validation_service
from ..config import DATABASE_PATH
from ..models import Feature, get_db

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/formblatt-z/validate")
def validate_formblatt():
    """Return validation status and any issues that would block a correct export."""
    db_path = str(DATABASE_PATH)
    features_check = validation_service.check_features(db_path)
    organisms_check = validation_service.check_organisms(db_path)

    issues: list[str] = []
    for m in features_check.get("missing", []):
        issues.append(f"Feature not in glossary: {m}")
    for m in organisms_check.get("missing_pairs", []):
        issues.append(f"Organism not in glossary: {m}")

    conn = sqlite3.connect(db_path)
    try:
        gmo_count = int(
            pd.read_sql_query("SELECT COUNT(*) AS n FROM gmos", conn)["n"][0]
        )
    finally:
        conn.close()

    return {
        "ready": len(issues) == 0,
        "issues": issues,
        "gmo_count": gmo_count,
    }


@router.get("/formblatt-z/rows")
def get_formblatt_rows(lang: str = Query("de")):
    """Return Formblatt-Z data as a JSON array of row objects."""
    if lang not in ("de", "en"):
        lang = "de"
    df = reports_service.generate_formblatt(str(DATABASE_PATH), lang=lang)
    return df.to_dict(orient="records")


@router.get("/formblatt-z")
def download_formblatt(lang: str = Query("de")):
    """Generate and stream the Formblatt-Z Excel file."""
    if lang not in ("de", "en"):
        lang = "de"

    db_path = str(DATABASE_PATH)
    df = reports_service.generate_formblatt(db_path, lang=lang)

    # Read institution name for the printed footer
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT institution FROM app_settings LIMIT 1").fetchone()
        institution = row[0] if row and row[0] else ""
    finally:
        conn.close()

    buf = io.BytesIO()
    today = date.today().strftime("%Y-%m-%d")

    writer = pd.ExcelWriter(buf, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Sheet1", header=False, index=False, startrow=1)

    workbook = writer.book
    worksheet = writer.sheets["Sheet1"]

    header_fmt = workbook.add_format({
        "bold": True, "text_wrap": True, "align": "center",
        "border": 1, "bg_color": "#D3D3D3",
    })
    cell_fmt = workbook.add_format({"text_wrap": True, "border": 1})

    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_fmt)

    footer_text = f"Formblatt Z, {institution}" if institution else "Formblatt Z"
    worksheet.set_footer(footer_text)
    worksheet.set_landscape()
    worksheet.repeat_rows(0)
    worksheet.set_paper(9)       # A4
    worksheet.fit_to_pages(1, 0) # 1 page wide, as tall as needed

    col_widths = [4, 30, 12, 16, 9, 13, 28, 25, 15, 5, 9, 15, 13, 10]
    for i, w in enumerate(col_widths):
        worksheet.set_column(i, i, w, cell_fmt)

    writer.close()
    buf.seek(0)

    filename = f"Formblatt-Z_{today}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _df_to_xlsx_stream(df: pd.DataFrame) -> io.BytesIO:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="xlsxwriter")
    buf.seek(0)
    return buf


@router.get("/plasmid-list")
def download_plasmid_list():
    """Generate and stream the plasmid list Excel file."""
    db_path = str(DATABASE_PATH)
    df = reports_service.generate_plasmid_list(db_path)

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT initials FROM app_settings LIMIT 1").fetchone()
        initials = row[0] if row and row[0] else ""
    finally:
        conn.close()

    buf = io.BytesIO()
    today = date.today().strftime("%Y-%m-%d")

    writer = pd.ExcelWriter(buf, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Sheet1", header=False, index=False, startrow=1)

    workbook = writer.book
    worksheet = writer.sheets["Sheet1"]

    header_fmt = workbook.add_format({
        "bold": True, "text_wrap": True, "align": "center",
        "border": 1, "bg_color": "#D3D3D3",
    })
    cell_fmt = workbook.add_format({"text_wrap": True, "border": 1})

    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_fmt)

    footer_text = f"{initials} Plasmid list, date: {today}" if initials else f"Plasmid list, date: {today}"
    worksheet.set_footer(footer_text)
    worksheet.set_landscape()
    worksheet.repeat_rows(0)
    worksheet.set_paper(9)
    worksheet.fit_to_pages(1, 0)

    col_widths = [6, 14, 60, 6, 14, 60, 60, 10, 10]
    for i, w in enumerate(col_widths):
        worksheet.set_column(i, i, w, cell_fmt)

    writer.close()
    buf.seek(0)

    filename = f"Plasmidlist_{today}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/health")
def get_health_report():
    """Run all three data quality checks and return combined results."""
    db_path = str(DATABASE_PATH)
    return {
        "features": validation_service.check_features(db_path),
        "organisms": validation_service.check_organisms(db_path),
        "plasmids": validation_service.check_plasmids(db_path),
    }


@router.get("/features/export-all")
def export_features_all():
    """Export all features as Excel."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    try:
        df = pd.read_sql_query(
            "SELECT annotation, alias, risk, organism, uid FROM features", conn
        )
    finally:
        conn.close()
    today = date.today().strftime("%Y-%m-%d")
    return StreamingResponse(
        _df_to_xlsx_stream(df),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="features_all_{today}.xlsx"'},
    )


@router.get("/features/export-used")
def export_features_used():
    """Export features that are actually used in cassettes as Excel."""
    try:
        df = reports_service.get_used_features_df(str(DATABASE_PATH))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    today = date.today().strftime("%Y-%m-%d")
    return StreamingResponse(
        _df_to_xlsx_stream(df),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="features_used_{today}.xlsx"'},
    )


@router.post("/features/import")
async def import_features(file: UploadFile, db: Session = Depends(get_db)):
    """Import features from an Excel file (upsert by annotation)."""
    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read Excel file: {e}")

    df.columns = [str(c).strip().lower() for c in df.columns]
    if "annotation" not in df.columns:
        raise HTTPException(status_code=400, detail="Excel file must have an 'annotation' column")

    created = updated = skipped = 0
    for _, row in df.iterrows():
        annotation = str(row.get("annotation", "")).strip()
        if not annotation or annotation.lower() == "nan":
            skipped += 1
            continue

        existing = db.query(Feature).filter(Feature.annotation == annotation).first()
        if existing:
            for field in ("alias", "risk", "organism", "uid"):
                if field in df.columns:
                    val = row.get(field)
                    if pd.notna(val):
                        setattr(existing, field, str(val).strip())
            updated += 1
        else:
            def _str(col: str) -> str | None:
                if col not in df.columns:
                    return None
                v = row.get(col)
                return str(v).strip() if pd.notna(v) else None

            db.add(Feature(
                annotation=annotation,
                alias=_str("alias"),
                risk=_str("risk"),
                organism=_str("organism"),
                uid=_str("uid"),
            ))
            created += 1

    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}
