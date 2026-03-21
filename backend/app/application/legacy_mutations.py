"""Legacy mutation helpers kept for compatibility with the old workflow model."""

import re
import sqlite3
from datetime import date


def update_cassettes(db_path: str, old2new: dict[str, str]) -> None:
    """Rename annotation references inside all cassette content strings."""
    conn = sqlite3.connect(db_path)
    cur_read = conn.cursor()
    cur_write = conn.cursor()
    try:
        cur_read.execute("SELECT id, content FROM cassettes")
        for cassette_id, content in cur_read:
            for old, new in old2new.items():
                if old in content:
                    old_escaped = re.sub(r"\(", r"\(", old)
                    old_escaped = re.sub(r"\)", r"\)", old_escaped)
                    new_content = re.sub(
                        r"(?<=-)" + old_escaped + r"(?=[-\[])",
                        new,
                        "-" + content + "-",
                    ).strip("-")
                    cur_write.execute(
                        "UPDATE cassettes SET content=? WHERE id=?",
                        (new_content, cassette_id),
                    )
        conn.commit()
    finally:
        conn.close()


def update_aliases(db_path: str, old2new: dict[str, str]) -> None:
    """Rename annotation references inside all plasmid alias strings."""
    conn = sqlite3.connect(db_path)
    cur_read = conn.cursor()
    cur_write = conn.cursor()
    try:
        cur_read.execute("SELECT id, alias FROM plasmids")
        for plasmid_id, alias in cur_read:
            if alias in ("", None):
                continue
            for old, new in old2new.items():
                if old in alias:
                    old_escaped = re.sub(r"\(", r"\(", old)
                    old_escaped = re.sub(r"\)", r"\)", old_escaped)
                    new_content = re.sub(
                        r"(?<=-)" + old_escaped + r"(?=[-\[])",
                        new,
                        "-" + alias + "-",
                    ).strip("-")
                    cur_write.execute(
                        "UPDATE plasmids SET alias=? WHERE id=?",
                        (new_content, plasmid_id),
                    )
        conn.commit()
    finally:
        conn.close()


def add_gmo(
    db_path: str,
    plasmid_id: int,
    organism_sel_id: int,
    target_rg: int,
    approval: str,
    generated_date: str,
    destroyed_date: str,
) -> None:
    """Add a GMO record for a plasmid and selected organism."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT organism_name FROM organism_selections WHERE id = ?",
            (organism_sel_id,),
        )
        organism_name = cursor.fetchone()[0]

        destroyed_display = destroyed_date if destroyed_date else "tbd"
        gmo_summary = (
            f"RG {target_rg}   |   Approval: {approval}   |   "
            f"{generated_date}   -   {destroyed_display}   |   "
            f"{organism_name.ljust(30)}"
        )

        cursor.execute(
            "INSERT INTO gmos (organism_name, plasmid_id, target_risk_group, summary, "
            "created_on, destroyed_on, approval) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                organism_name,
                plasmid_id,
                target_rg,
                gmo_summary,
                generated_date,
                destroyed_date,
                approval,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def destroy_gmo(db_path: str, organism_id: int, destruction_date: str) -> None:
    """Set the destruction date on a GMO record."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT summary FROM gmos WHERE id = ?", (organism_id,))
        summary = cursor.fetchone()[0]
        summary = summary.replace("tbd", destruction_date)
        cursor.execute(
            "UPDATE gmos SET summary = ?, destroyed_on = ? WHERE id = ?",
            (summary, destruction_date, organism_id),
        )
        conn.commit()
    finally:
        conn.close()


def duplicate_plasmid(db_path: str, plasmid_id: int, duplicate_gmos: bool = False) -> int:
    """Duplicate a plasmid with its cassettes and optionally GMOs."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO plasmids (name, alias, purpose, summary, clone, backbone_vector) "
            "SELECT name, alias, purpose, summary, clone, backbone_vector "
            "FROM plasmids WHERE id = ?",
            (plasmid_id,),
        )
        cursor.execute("SELECT MAX(id) FROM plasmids")
        new_id = cursor.fetchone()[0]
        conn.commit()

        cursor.execute("SELECT content FROM cassettes WHERE plasmid_id = ?", (plasmid_id,))
        for (content,) in cursor.fetchall():
            cursor.execute(
                "INSERT INTO cassettes (content, plasmid_id) VALUES (?, ?)",
                (content, new_id),
            )
        conn.commit()

        if duplicate_gmos:
            today = date.today().strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT organism_name, target_risk_group, approval FROM gmos WHERE plasmid_id = ?",
                (plasmid_id,),
            )
            for organism_name, rg, approval in cursor.fetchall():
                gmo_summary = (
                    f"RG {rg}   |   Approval: {approval}   |   "
                    f"{today}   -   tbd   |   {organism_name.ljust(30)}"
                )
                cursor.execute(
                    "INSERT INTO gmos (organism_name, plasmid_id, target_risk_group, "
                    "summary, approval, created_on) VALUES (?, ?, ?, ?, ?, ?)",
                    (organism_name, new_id, rg, gmo_summary, approval, today),
                )
            conn.commit()

        return new_id
    finally:
        conn.close()
