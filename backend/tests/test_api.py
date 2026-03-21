"""HTTP-level API tests for the FastAPI application."""

import shutil
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app import main as main_module
from app.migrations import CURRENT_SCHEMA_VERSION


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_DB = REPO_ROOT / "example" / "GMOCU-0.7" / "gmocu.db"
LEGACY_DB_04 = REPO_ROOT / "example" / "GMOCU-0.4" / "gmocu.db"


def _make_client(monkeypatch, tmp_path) -> TestClient:
    db_path = tmp_path / "api-test.db"
    monkeypatch.setattr(main_module, "DATABASE_PATH", db_path)
    return TestClient(main_module.app)


def test_health_and_settings_endpoints_seed_database(monkeypatch, tmp_path):
    with _make_client(monkeypatch, tmp_path) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        body = health.json()
        assert body["status"] == "ok"
        assert body["database"].endswith("api-test.db")

        settings = client.get("/api/settings/")
        assert settings.status_code == 200
        settings_body = settings.json()
        assert settings_body["name"] == "Name"
        assert settings_body["autosync"] == 0


def test_startup_migrates_legacy_database(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy-startup.db"
    shutil.copy(LEGACY_DB_04, db_path)
    monkeypatch.setattr(main_module, "DATABASE_PATH", db_path)

    with TestClient(main_module.app) as client:
        settings = client.get("/api/settings/")
        assert settings.status_code == 200

        features = client.get("/api/features/")
        assert features.status_code == 200

    conn = sqlite3.connect(db_path)
    try:
        schema_version = conn.execute(
            "SELECT schema_version FROM schema_meta ORDER BY id DESC LIMIT 1;"
        ).fetchone()
        feature_uid_type = conn.execute(
            "SELECT type FROM pragma_table_info('features') WHERE name = 'uid';"
        ).fetchone()
        organism_uid_type = conn.execute(
            "SELECT type FROM pragma_table_info('organisms') WHERE name = 'uid';"
        ).fetchone()
        plasmid_generated_type = conn.execute(
            "SELECT type FROM pragma_table_info('plasmids') WHERE name = 'created_on';"
        ).fetchone()
        plasmid_destroyed_type = conn.execute(
            "SELECT type FROM pragma_table_info('plasmids') WHERE name = 'destroyed_on';"
        ).fetchone()
        gmo_generated_type = conn.execute(
            "SELECT type FROM pragma_table_info('gmos') WHERE name = 'created_on';"
        ).fetchone()
        gmo_destroyed_type = conn.execute(
            "SELECT type FROM pragma_table_info('gmos') WHERE name = 'destroyed_on';"
        ).fetchone()
        feature_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(features);").fetchall()
        }
        organism_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(organisms);").fetchall()
        }
        assert schema_version == (CURRENT_SCHEMA_VERSION,)
        assert feature_uid_type == ("VARCHAR(32)",)
        assert organism_uid_type == ("VARCHAR(32)",)
        assert plasmid_generated_type == ("TEXT",)
        assert plasmid_destroyed_type == ("TEXT",)
        assert gmo_generated_type == ("TEXT",)
        assert gmo_destroyed_type == ("TEXT",)
        assert {"uid", "synced"}.issubset(feature_columns)
        assert {"uid", "synced"}.issubset(organism_columns)
    finally:
        conn.close()


def test_settings_and_support_resource_api(monkeypatch, tmp_path):
    with _make_client(monkeypatch, tmp_path) as client:
        settings_update = client.patch(
            "/api/settings/",
            json={"name": "API User", "autosync": 1, "use_gdrive": 1},
        )
        assert settings_update.status_code == 200
        updated_settings = settings_update.json()
        assert updated_settings["name"] == "API User"
        assert updated_settings["autosync"] == 1
        assert updated_settings["use_gdrive"] == 1

        selection_create = client.post(
            "/api/organism-selections/",
            json={"organism_name": "E. coli"},
        )
        assert selection_create.status_code == 201
        selection = selection_create.json()

        selections_list = client.get("/api/organism-selections/")
        assert selections_list.status_code == 200
        assert any(item["id"] == selection["id"] for item in selections_list.json())

        selection_delete = client.delete(f"/api/organism-selections/{selection['id']}")
        assert selection_delete.status_code == 204

        favourite_create = client.post(
            "/api/organism-favourites/",
            json={"organism_name": "B. subtilis"},
        )
        assert favourite_create.status_code == 201
        favourite = favourite_create.json()

        favourites_list = client.get("/api/organism-favourites/")
        assert favourites_list.status_code == 200
        assert any(item["id"] == favourite["id"] for item in favourites_list.json())

        favourite_delete = client.delete(f"/api/organism-favourites/{favourite['id']}")
        assert favourite_delete.status_code == 204

        credentials_create = client.post(
            "/api/ice-credentials/",
            json={
                "alias": "ICE test",
                "ice_instance": "https://example.org/ice",
                "ice_token_client": "client-token",
            },
        )
        assert credentials_create.status_code == 201
        credentials = credentials_create.json()
        cred_id = credentials["id"]

        credentials_list = client.get("/api/ice-credentials/")
        assert credentials_list.status_code == 200
        assert any(item["id"] == cred_id for item in credentials_list.json())

        credentials_update = client.patch(
            f"/api/ice-credentials/{cred_id}",
            json={"file_browser_user": "alice", "file_browser_password": "secret"},
        )
        assert credentials_update.status_code == 200
        assert credentials_update.json()["file_browser_user"] == "alice"
        assert credentials_update.json()["file_browser_password"] == "secret"

        credentials_delete = client.delete(f"/api/ice-credentials/{cred_id}")
        assert credentials_delete.status_code == 204

        credentials_missing = client.patch(f"/api/ice-credentials/{cred_id}", json={"alias": "missing"})
        assert credentials_missing.status_code == 404


def test_feature_crud_api(monkeypatch, tmp_path):
    with _make_client(monkeypatch, tmp_path) as client:
        created = client.post(
            "/api/features/",
            json={
                "annotation": "Feature_API",
                "alias": "Feature Alias",
                "risk": "No Risk",
                "organism": "E. coli",
            },
        )
        assert created.status_code == 201
        feature = created.json()
        feature_id = feature["id"]
        assert feature["annotation"] == "Feature_API"

        listed = client.get("/api/features/", params={"search": "Feature_API"})
        assert listed.status_code == 200
        assert any(item["id"] == feature_id for item in listed.json())

        fetched = client.get(f"/api/features/{feature_id}")
        assert fetched.status_code == 200
        assert fetched.json()["alias"] == "Feature Alias"

        updated = client.patch(
            f"/api/features/{feature_id}",
            json={"risk": "Risk", "organism": "B. subtilis"},
        )
        assert updated.status_code == 200
        assert updated.json()["risk"] == "Risk"
        assert updated.json()["organism"] == "B. subtilis"

        deleted = client.delete(f"/api/features/{feature_id}")
        assert deleted.status_code == 204

        missing = client.get(f"/api/features/{feature_id}")
        assert missing.status_code == 404


def test_plasmid_nested_workflow_api(monkeypatch, tmp_path):
    with _make_client(monkeypatch, tmp_path) as client:
        plasmid_resp = client.post("/api/plasmids/", json={"name": "pAPI001"})
        assert plasmid_resp.status_code == 201
        plasmid = plasmid_resp.json()
        plasmid_id = plasmid["id"]
        assert plasmid["name"] == "pAPI001"
        assert len(plasmid["cassettes"]) == 1

        updated = client.patch(
            f"/api/plasmids/{plasmid_id}",
            json={"alias": "api-alias", "target_risk_group": 2, "backbone_vector": "pBBR1"},
        )
        assert updated.status_code == 200
        assert updated.json()["alias"] == "api-alias"
        assert updated.json()["target_risk_group"] == 2

        cassette_resp = client.post(f"/api/plasmids/{plasmid_id}/cassettes")
        assert cassette_resp.status_code == 201
        cassette_id = cassette_resp.json()["id"]

        cassette_update = client.patch(
            f"/api/plasmids/cassettes/{cassette_id}",
            json={"content": "Feature_A-Feature_B"},
        )
        assert cassette_update.status_code == 200
        assert cassette_update.json()["content"] == "Feature_A-Feature_B"

        gmo_resp = client.post(
            f"/api/plasmids/{plasmid_id}/gmos",
            json={"organism_name": "E. coli", "approval": "S1", "target_risk_group": 1},
        )
        assert gmo_resp.status_code == 201
        gmo = gmo_resp.json()
        assert gmo["organism_name"] == "E. coli"

        gmo_destroyed = client.patch(f"/api/plasmids/gmos/{gmo['id']}/destroy")
        assert gmo_destroyed.status_code == 200
        assert gmo_destroyed.json()["destroyed_on"] is not None

        genbank_upload = client.put(
            f"/api/plasmids/{plasmid_id}/genbank",
            json={"genbank_filename": "pAPI001.gb", "genbank_content": "LOCUS       pAPI001"},
        )
        assert genbank_upload.status_code == 200
        assert genbank_upload.json()["genbank_filename"] == "pAPI001.gb"

        genbank_download = client.get(f"/api/plasmids/{plasmid_id}/genbank")
        assert genbank_download.status_code == 200
        assert genbank_download.headers["content-disposition"].endswith('"pAPI001.gb"')

        attachment_upload = client.post(
            f"/api/plasmids/{plasmid_id}/attachments",
            files={"file": ("note.txt", b"hello api attachment", "text/plain")},
        )
        assert attachment_upload.status_code == 201
        attachment = attachment_upload.json()

        attachment_download = client.get(
            f"/api/plasmids/attachments/{attachment['id']}/download"
        )
        assert attachment_download.status_code == 200
        assert attachment_download.content == b"hello api attachment"

        duplicated = client.post(f"/api/plasmids/{plasmid_id}/duplicate")
        assert duplicated.status_code == 201
        assert duplicated.json()["name"] == "pAPI001 (copy)"

        delete_attachment = client.delete(f"/api/plasmids/attachments/{attachment['id']}")
        assert delete_attachment.status_code == 204

        delete_plasmid = client.delete(f"/api/plasmids/{plasmid_id}")
        assert delete_plasmid.status_code == 204


def test_database_upload_endpoint_replaces_database(monkeypatch, tmp_path):
    with _make_client(monkeypatch, tmp_path) as client:
        initial_list = client.get("/api/plasmids/")
        assert initial_list.status_code == 200
        assert initial_list.json() == []

        with LEGACY_DB_04.open("rb") as db_file:
            uploaded = client.post(
                "/api/database/upload",
                files={"file": ("gmocu.db", db_file, "application/octet-stream")},
            )
        assert uploaded.status_code == 200
        assert uploaded.json()["status"] == "ok"

        after_upload = client.get("/api/plasmids/")
        assert after_upload.status_code == 200
        assert len(after_upload.json()) > 0

        conn = sqlite3.connect(tmp_path / "api-test.db")
        try:
            metadata = conn.execute(
                """
                SELECT schema_version, migrated_from
                FROM schema_meta
                ORDER BY id DESC
                LIMIT 1;
                """
            ).fetchone()
            assert metadata == (CURRENT_SCHEMA_VERSION, "legacy:pre-0.5")
        finally:
            conn.close()
