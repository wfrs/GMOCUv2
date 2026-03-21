"""Attachment and file extraction helpers."""

from pathlib import Path

from ..models import Attachment, get_session


def insert_attachment(db_path: str, plasmid_id: int, file_path: str, filename: str) -> None:
    """Read a file from disk and store it as a BLOB attachment."""
    with open(file_path, "rb") as file:
        blob_data = file.read()

    session = get_session(db_path)
    try:
        attachment = Attachment(plasmid_id=plasmid_id, file_blob=blob_data, filename=filename)
        session.add(attachment)
        session.commit()
    finally:
        session.close()


def read_attachment(db_path: str, attach_id: int, filename: str, output_dir: str) -> str:
    """Write an attachment BLOB to disk. Returns the output file path."""
    session = get_session(db_path)
    try:
        attachment = session.query(Attachment).filter_by(id=attach_id).first()
        if attachment is None or attachment.file_blob is None:
            raise FileNotFoundError("There is no attachment to download.")
        output_path = str(Path(output_dir) / filename)
        with open(output_path, "wb") as file:
            file.write(attachment.file_blob)
        return output_path
    finally:
        session.close()
