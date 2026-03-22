"""Smoke tests for the extracted business logic against the example database."""

import sqlite3
import shutil
from pathlib import Path

import pytest
import pandas as pd

from app.bootstrap import ensure_database_ready, prepare_runtime_database
from app.application import features as feature_service
from app.application import ice_credentials as credentials_service
from app.application import imports as import_service
from app.application import attachments as attachment_service
from app.application import legacy_mutations as legacy_mutation_service
from app.application import lookups as lookup_service
from app.application.normalization import sanitize_annotation
from app.application import organism_lists as organism_list_service
from app.application import organisms as organism_service
from app.application import plasmids as plasmid_service
from app.application import reports as report_service
from app.application import settings as settings_service
from app.application import validation as validation_service
from app.migrations import CURRENT_SCHEMA_VERSION, inspect_database, migrate_database_if_needed
from app.models import get_engine, get_session
from app.database import read_settings, get_db_version, backup_database, init_db
from app.schemas import (
    FeatureCreate,
    FeatureUpdate,
    GMOCreate,
    GMOUpdate,
    IceCredentialsCreate,
    IceCredentialsUpdate,
    OrganismFavouriteCreate,
    OrganismCreate,
    OrganismSelectionCreate,
    OrganismUpdate,
    PlasmidCreate,
    PlasmidUpdate,
    SettingsUpdate,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_DB = REPO_ROOT / "example" / "GMOCU-0.7" / "gmocu.db"
LEGACY_DB_04 = REPO_ROOT / "example" / "GMOCU-0.4" / "gmocu.db"
ACTIVE_BACKUP_DB = REPO_ROOT / "example" / "250615_gmocu_backup_sciebo.db"


@pytest.fixture
def db_path(tmp_path):
    """Copy the example database to a temp dir so tests don't modify the original."""
    dest = tmp_path / "gmocu.db"
    shutil.copy(EXAMPLE_DB, dest)
    ensure_database_ready(str(dest))
    return str(dest)


@pytest.fixture
def fresh_db(tmp_path):
    """Create a brand new database from scratch."""
    dest = str(tmp_path / "fresh.db")
    init_db(dest)
    return dest


class TestModels:
    def test_tables_reflect(self, db_path):
        ensure_database_ready(db_path)
        engine = get_engine(db_path)
        from sqlalchemy import inspect
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        expected = [
            "plasmids", "plasmid_statuses", "attachments", "cassettes",
            "gmos", "organism_selections", "organism_favourites",
            "features", "organisms", "app_settings", "ice_credentials",
            "schema_meta",
        ]
        for t in expected:
            assert t in table_names, f"Missing table: {t}"

    def test_session_query(self, db_path):
        session = get_session(db_path)
        from app.models import Plasmid, Feature, Organism
        plasmids = session.query(Plasmid).all()
        assert len(plasmids) > 0
        features = session.query(Feature).all()
        assert len(features) > 0
        organisms = session.query(Organism).all()
        assert len(organisms) > 0
        session.close()


class TestDatabase:
    def test_read_settings(self, db_path):
        s = read_settings(db_path)
        assert isinstance(s, dict)
        assert "user_name" in s
        assert "initials" in s
        assert "ice_instance" in s

    def test_get_db_version(self, db_path):
        v = get_db_version(db_path)
        assert isinstance(v, float)

    def test_backup(self, db_path, tmp_path):
        backup_path = backup_database(db_path, str(tmp_path))
        assert Path(backup_path).exists()
        assert Path(backup_path).stat().st_size > 0

    def test_init_fresh_db(self, fresh_db):
        session = get_session(fresh_db)
        from app.models import SelectionValue, Settings, IceCredentials
        values = session.query(SelectionValue).all()
        assert len(values) == 4
        settings = session.query(Settings).first()
        assert settings is not None
        assert settings.style == "Reddit"
        credentials = session.query(IceCredentials).all()
        assert len(credentials) == 1
        assert settings.ice == credentials[0].id
        session.close()

    def test_bootstrap_is_idempotent(self, fresh_db):
        ensure_database_ready(fresh_db)
        ensure_database_ready(fresh_db)

        session = get_session(fresh_db)
        from app.models import SelectionValue, Settings, IceCredentials

        assert session.query(SelectionValue).count() == 4
        assert session.query(Settings).count() == 1
        assert session.query(IceCredentials).count() == 1
        session.close()

    def test_runtime_uses_separate_v2_default_name(self, tmp_path, monkeypatch):
        legacy_path = tmp_path / "gmocu.db"
        v2_path = tmp_path / "gmocu-v2.db"
        shutil.copy(EXAMPLE_DB, legacy_path)
        ensure_database_ready(str(legacy_path))

        import app.bootstrap as bootstrap_module

        monkeypatch.setattr(bootstrap_module, "LEGACY_DATABASE_PATH", legacy_path)
        monkeypatch.setattr(bootstrap_module, "DEFAULT_DATABASE_PATH", v2_path)

        prepare_runtime_database(str(v2_path))

        assert v2_path.exists()
        assert inspect_database(str(v2_path)).kind == "current"

    def test_inspect_active_backup_version(self):
        inspection = inspect_database(str(ACTIVE_BACKUP_DB))
        assert inspection.kind == "legacy"
        assert inspection.legacy_version == "0.72"

    def test_migrate_legacy_pre_05_database(self, tmp_path):
        migrated_db = tmp_path / "legacy-04.db"
        shutil.copy(LEGACY_DB_04, migrated_db)

        before = inspect_database(str(migrated_db))
        assert before.kind == "legacy"
        assert before.legacy_version == "pre-0.5"

        result = migrate_database_if_needed(str(migrated_db))
        assert result.migrated is True
        assert result.inspection.kind == "current"
        assert result.inspection.schema_version == CURRENT_SCHEMA_VERSION
        assert Path(result.backup_path).exists()

        session = get_session(str(migrated_db))
        try:
            from app.models import Feature, Organism, SchemaMeta

            metadata = session.query(SchemaMeta).order_by(SchemaMeta.id.desc()).first()
            assert metadata is not None
            assert metadata.schema_version == CURRENT_SCHEMA_VERSION
            assert metadata.migrated_from == "legacy:pre-0.5"

            feature = session.query(Feature).first()
            organism = session.query(Organism).first()
            assert hasattr(feature, "uid")
            assert hasattr(organism, "uid")
        finally:
            session.close()

        conn = sqlite3.connect(migrated_db)
        try:
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
            plasmid_date_type = conn.execute(
                "SELECT type FROM pragma_table_info('plasmids') WHERE name = 'recorded_on';"
            ).fetchone()
            gmo_generated_type = conn.execute(
                "SELECT type FROM pragma_table_info('gmos') WHERE name = 'created_on';"
            ).fetchone()
            gmo_destroyed_type = conn.execute(
                "SELECT type FROM pragma_table_info('gmos') WHERE name = 'destroyed_on';"
            ).fetchone()
            gmo_entry_type = conn.execute(
                "SELECT type FROM pragma_table_info('gmos') WHERE name = 'entry_date';"
            ).fetchone()
            assert feature_uid_type == ("VARCHAR(32)",)
            assert organism_uid_type == ("VARCHAR(32)",)
            assert plasmid_generated_type == ("TEXT",)
            assert plasmid_destroyed_type == ("TEXT",)
            assert plasmid_date_type == ("TEXT",)
            assert gmo_generated_type == ("TEXT",)
            assert gmo_destroyed_type == ("TEXT",)
            assert gmo_entry_type == ("TEXT",)
        finally:
            conn.close()

    def test_migrate_readonly_legacy_database(self, tmp_path):
        migrated_db = tmp_path / "legacy-readonly.db"
        shutil.copy(ACTIVE_BACKUP_DB, migrated_db)
        migrated_db.chmod(0o444)

        result = migrate_database_if_needed(str(migrated_db))
        assert result.migrated is True
        assert result.inspection.kind == "current"
        assert result.inspection.schema_version == CURRENT_SCHEMA_VERSION
        assert Path(result.backup_path).exists()

        conn = sqlite3.connect(migrated_db)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table';"
                )
            }
            assert "app_settings" in tables
            assert "organism_selections" in tables

            organism_columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info('organisms');").fetchall()
            }
            assert "risk_group" in organism_columns
            assert "RG" not in organism_columns
        finally:
            conn.close()


class TestCore:
    def test_get_feature_annotations(self, db_path):
        annotations = lookup_service.get_feature_annotations(db_path)
        assert isinstance(annotations, list)
        assert len(annotations) > 0
        assert annotations == sorted(annotations)

    def test_get_organism_short_names(self, db_path):
        names = lookup_service.get_organism_short_names(db_path)
        assert isinstance(names, list)
        assert len(names) > 0
        assert names == sorted(names)

    def test_check_plasmids(self, db_path):
        result = validation_service.check_plasmids(db_path)
        assert "duplicates" in result
        assert "no_backbone" in result
        assert "no_cassettes" in result
        assert "no_gmos" in result

    def test_check_features(self, db_path):
        result = validation_service.check_features(db_path)
        assert "complete" in result
        assert "missing" in result
        assert "redundant" in result
        assert "duplicates" in result
        assert isinstance(result["complete"], bool)

    def test_check_organisms(self, db_path):
        result = validation_service.check_organisms(db_path)
        assert "complete" in result
        assert "missing_pairs" in result
        assert "redundant" in result
        assert "duplicates" in result

    def test_generate_plasmid_list(self, db_path):
        df = report_service.generate_plasmid_list(db_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "Plasmid name" in df.columns

    def test_generate_formblatt(self, db_path):
        df = report_service.generate_formblatt(db_path, lang='de')
        assert isinstance(df, pd.DataFrame)
        assert "GVO Bezeichnung" in df.columns

    def test_generate_formblatt_english(self, db_path):
        df = report_service.generate_formblatt(db_path, lang='en')
        assert isinstance(df, pd.DataFrame)
        assert "GMO name" in df.columns

    def test_sanitize_annotation(self):
        assert sanitize_annotation("my-feature") == "my_feature"
        assert sanitize_annotation("feat[v1]") == "feat(v1)"
        assert sanitize_annotation("has space") == "has_space"

    def test_duplicate_plasmid(self, db_path):
        session = get_session(db_path)
        from app.models import Plasmid
        original = session.query(Plasmid).first()
        original_id = original.id
        original_name = original.name
        session.close()

        new_id = legacy_mutation_service.duplicate_plasmid(db_path, original_id)
        assert new_id != original_id

        session = get_session(db_path)
        new_plasmid = session.query(Plasmid).filter_by(id=new_id).first()
        assert new_plasmid.name == original_name
        session.close()

    def test_add_features_from_dataframe(self, db_path):
        df = pd.DataFrame({
            "annotation": ["Test_Feature_XYZ"],
            "alias": ["test alias"],
            "risk": ["No Risk"],
            "organism": ["E.coli"],
        })
        added, skipped = import_service.add_features_from_dataframe(db_path, df)
        assert "Test_Feature_XYZ" in added
        assert len(skipped) == 0

        # importing again should skip
        added2, skipped2 = import_service.add_features_from_dataframe(db_path, df)
        assert len(added2) == 0
        assert "Test_Feature_XYZ" in skipped2

    def test_add_organisms_from_dataframe(self, db_path):
        df = pd.DataFrame({
            "short_name": ["T.test"],
            "full_name": ["Testus testus"],
            "risk_group": [1],
        })
        added = import_service.add_organisms_from_dataframe(db_path, df)
        assert "T.test" in added

        # importing again should skip
        added2 = import_service.add_organisms_from_dataframe(db_path, df)
        assert len(added2) == 0


class TestPlasmidApplication:
    def test_create_update_and_duplicate_plasmid(self, fresh_db):
        session = get_session(fresh_db)
        try:
            created = plasmid_service.create_plasmid(session, PlasmidCreate(name="pTEST001"))
            assert created.name == "pTEST001"
            assert len(created.cassettes) == 1
            assert created.cassettes[0].content == "Empty"

            updated = plasmid_service.update_plasmid(
                session,
                created.id,
                PlasmidUpdate(alias="alias-1", target_risk_group=2),
            )
            assert updated.alias == "alias-1"
            assert updated.target_risk_group == 2

            duplicated = plasmid_service.duplicate_plasmid(session, created.id)
            assert duplicated.id != created.id
            assert duplicated.name == "pTEST001 (copy)"
            assert len(duplicated.cassettes) == 1
        finally:
            session.close()

    def test_update_plasmid_dates_and_gmo_fields(self, fresh_db):
        session = get_session(fresh_db)
        try:
            selection = organism_list_service.create_selection(session, "AgTu")
            created = plasmid_service.create_plasmid(session, PlasmidCreate(name="pTEST002"))
            updated = plasmid_service.update_plasmid(
                session,
                created.id,
                PlasmidUpdate(
                    recorded_on="2024-02-12",
                    target_organism_selection_id=selection.id,
                ),
            )
            assert updated.recorded_on == "2024-02-12"
            assert updated.target_organism_selection_id == selection.id

            gmo = plasmid_service.add_gmo(
                session,
                created.id,
                GMOCreate(
                    organism_name="E. coli",
                    approval="S1",
                    target_risk_group=1,
                    created_on="2024-01-23",
                ),
            )
            assert gmo.created_on == "2024-01-23"

            gmo = plasmid_service.update_gmo(
                session,
                gmo.id,
                GMOUpdate(
                    approval="S2",
                    target_risk_group=2,
                    destroyed_on="2024-02-05",
                ),
            )
            assert gmo.approval == "S2"
            assert gmo.target_risk_group == 2
            assert gmo.destroyed_on == "2024-02-05"
            assert "2024-02-05" in (gmo.summary or "")
        finally:
            session.close()


class TestReferenceApplication:
    def test_lookup_service_returns_sorted_names(self, db_path):
        annotations = lookup_service.get_feature_annotations(db_path)
        assert isinstance(annotations, list)
        assert annotations == sorted(annotations)

        organisms = lookup_service.get_organism_short_names(db_path)
        assert isinstance(organisms, list)
        assert organisms == sorted(organisms)

    def test_validation_service_checks_existing_example_data(self, db_path):
        plasmid_result = validation_service.check_plasmids(db_path)
        assert "duplicates" in plasmid_result
        assert "no_backbone" in plasmid_result
        assert "no_cassettes" in plasmid_result
        assert "no_gmos" in plasmid_result

        feature_result = validation_service.check_features(db_path)
        assert "complete" in feature_result
        assert "missing" in feature_result
        assert "redundant" in feature_result
        assert "duplicates" in feature_result

        organism_result = validation_service.check_organisms(db_path)
        assert "complete" in organism_result
        assert "missing_pairs" in organism_result
        assert "redundant" in organism_result
        assert "duplicates" in organism_result

    def test_import_service_adds_features_and_organisms_from_dataframes(self, fresh_db):
        feature_df = pd.DataFrame(
            {
                "annotation": ["Test Feature-XYZ"],
                "alias": ["test alias"],
                "risk": ["No Risk"],
                "organism": ["E.coli"],
            }
        )
        added_features, skipped_features = import_service.add_features_from_dataframe(
            fresh_db,
            feature_df,
        )
        assert "Test_Feature_XYZ" in added_features
        assert skipped_features == []

        organism_df = pd.DataFrame(
            {
                "short_name": ["T.test"],
                "full_name": ["Testus testus"],
                "risk_group": [1],
            }
        )
        added_organisms = import_service.add_organisms_from_dataframe(fresh_db, organism_df)
        assert "T.test" in added_organisms

    def test_import_service_imports_plasmid_from_other_database(self, fresh_db):
        importable = import_service.get_importable_plasmids(fresh_db, str(EXAMPLE_DB))
        assert len(importable) > 0

        selected_name = importable[0]
        result = import_service.import_plasmids(fresh_db, str(EXAMPLE_DB), [selected_name])
        assert result["imported_count"] == 1

        session = get_session(fresh_db)
        try:
            from app.models import Plasmid

            imported = session.query(Plasmid).filter_by(name=selected_name).first()
            assert imported is not None
        finally:
            session.close()

    def test_report_service_generates_formblatt_and_plasmid_list(self, db_path):
        formblatt = report_service.generate_formblatt(db_path, lang="de")
        assert isinstance(formblatt, pd.DataFrame)
        assert "GVO Bezeichnung" in formblatt.columns

        formblatt_en = report_service.generate_formblatt(db_path, lang="en")
        assert isinstance(formblatt_en, pd.DataFrame)
        assert "GMO name" in formblatt_en.columns

        plasmid_list = report_service.generate_plasmid_list(db_path)
        assert isinstance(plasmid_list, pd.DataFrame)
        assert "Plasmid name" in plasmid_list.columns

    def test_report_service_exports_feature_excel(self, db_path, tmp_path):
        output_path = tmp_path / "features.xlsx"
        report_service.export_all_features(db_path, str(output_path))
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_feature_service_crud(self, fresh_db):
        session = get_session(fresh_db)
        try:
            feature = feature_service.create_feature(
                session,
                FeatureCreate(annotation="Feature_A", alias="Alias A"),
            )
            assert feature.annotation == "Feature_A"

            updated = feature_service.update_feature(
                session,
                feature.id,
                FeatureUpdate(risk="Risk", organism="E.coli"),
            )
            assert updated.risk == "Risk"
            assert updated.organism == "E.coli"

            listed = feature_service.list_features(session, search="Feature")
            assert any(item.id == feature.id for item in listed)

            feature_service.delete_feature(session, feature.id)
            assert not any(item.id == feature.id for item in feature_service.list_features(session))
        finally:
            session.close()

    def test_organism_service_crud(self, fresh_db):
        session = get_session(fresh_db)
        try:
            organism = organism_service.create_organism(
                session,
                OrganismCreate(full_name="Escherichia coli", short_name="E. coli", risk_group="1"),
            )
            assert organism.short_name == "E. coli"

            updated = organism_service.update_organism(
                session,
                organism.id,
                OrganismUpdate(risk_group="2"),
            )
            assert updated.risk_group == "2"

            listed = organism_service.list_organisms(session, search="Escherichia")
            assert any(item.id == organism.id for item in listed)

            organism_service.delete_organism(session, organism.id)
            assert not any(item.id == organism.id for item in organism_service.list_organisms(session))
        finally:
            session.close()

    def test_settings_service_update(self, fresh_db):
        session = get_session(fresh_db)
        try:
            settings = settings_service.get_settings(session)
            assert settings.style == "Reddit"

            updated = settings_service.update_settings(
                session,
                SettingsUpdate(name="New User", autosync=1),
            )
            assert updated.name == "New User"
            assert updated.autosync == 1
        finally:
            session.close()

    def test_attachment_service_round_trip(self, fresh_db, tmp_path):
        session = get_session(fresh_db)
        try:
            created = plasmid_service.create_plasmid(session, PlasmidCreate(name="pTESTATT"))
            plasmid_id = created.id
        finally:
            session.close()

        source_path = tmp_path / "note.txt"
        source_path.write_text("hello attachment", encoding="utf-8")

        attachment_service.insert_attachment(
            fresh_db,
            plasmid_id,
            str(source_path),
            "note.txt",
        )

        session = get_session(fresh_db)
        try:
            from app.models import Attachment

            stored = session.query(Attachment).filter_by(plasmid_id=plasmid_id).first()
            assert stored is not None
            output_dir = tmp_path / "downloaded"
            output_dir.mkdir()
            out_path = attachment_service.read_attachment(
                fresh_db,
                stored.id,
                "note.txt",
                str(output_dir),
            )
            assert Path(out_path).read_text(encoding="utf-8") == "hello attachment"
        finally:
            session.close()

    def test_organism_list_services(self, fresh_db):
        session = get_session(fresh_db)
        try:
            selection = organism_list_service.create_selection(
                session,
                OrganismSelectionCreate(organism_name="B. subtilis").organism_name,
            )
            favourite = organism_list_service.create_favourite(
                session,
                OrganismFavouriteCreate(organism_name="E. coli").organism_name,
            )

            assert any(
                item.id == selection.id
                for item in organism_list_service.list_selections(session)
            )
            assert any(
                item.id == favourite.id
                for item in organism_list_service.list_favourites(session)
            )

            organism_list_service.delete_selection(session, selection.id)
            organism_list_service.delete_favourite(session, favourite.id)

            assert not any(
                item.id == selection.id
                for item in organism_list_service.list_selections(session)
            )
            assert not any(
                item.id == favourite.id
                for item in organism_list_service.list_favourites(session)
            )
        finally:
            session.close()

    def test_credentials_service_crud(self, fresh_db):
        session = get_session(fresh_db)
        try:
            created = credentials_service.create_credentials(
                session,
                IceCredentialsCreate(
                    alias="ICE staging",
                    ice_instance="https://example.org/ice",
                ),
            )
            assert created.alias == "ICE staging"

            updated = credentials_service.update_credentials(
                session,
                created.id,
                IceCredentialsUpdate(file_browser_user="alice"),
            )
            assert updated.file_browser_user == "alice"
            assert any(item.id == created.id for item in credentials_service.list_credentials(session))

            credentials_service.delete_credentials(session, created.id)
            assert not any(item.id == created.id for item in credentials_service.list_credentials(session))
        finally:
            session.close()

    def test_legacy_mutation_helpers(self, fresh_db):
        session = get_session(fresh_db)
        try:
            from app.models import Cassette, GMO, Plasmid

            plasmid = plasmid_service.create_plasmid(session, PlasmidCreate(name="pLEG001"))
            plasmid_id = plasmid.id
            plasmid_service.update_plasmid(
                session,
                plasmid_id,
                PlasmidUpdate(alias="old_feature-helper", backbone_vector="bb"),
            )
            cassette = session.query(Cassette).filter_by(plasmid_id=plasmid_id).first()
            cassette.content = "old_feature-helper"
            session.commit()
        finally:
            session.close()

        organism_list_session = get_session(fresh_db)
        try:
            selection = organism_list_service.create_selection(organism_list_session, "E. coli")
            selection_id = selection.id
        finally:
            organism_list_session.close()

        legacy_mutation_service.add_gmo(
            fresh_db,
            plasmid_id,
            selection_id,
            1,
            "S1",
            "2024-01-01",
            "",
        )
        legacy_mutation_service.update_cassettes(fresh_db, {"old_feature": "new_feature"})
        legacy_mutation_service.update_aliases(fresh_db, {"old_feature": "new_feature"})

        session = get_session(fresh_db)
        try:
            from app.models import Cassette, GMO, Plasmid

            cassette = session.query(Cassette).filter_by(plasmid_id=plasmid_id).first()
            updated_plasmid = session.query(Plasmid).filter_by(id=plasmid_id).first()
            gmo = session.query(GMO).filter_by(plasmid_id=plasmid_id).first()

            assert cassette.content == "new_feature-helper"
            assert updated_plasmid.alias == "new_feature-helper"
            assert gmo is not None

            legacy_mutation_service.destroy_gmo(fresh_db, gmo.id, "2024-02-01")
            duplicated_id = legacy_mutation_service.duplicate_plasmid(
                fresh_db,
                plasmid_id,
                duplicate_gmos=True,
            )
        finally:
            session.close()

        session = get_session(fresh_db)
        try:
            from app.models import GMO, Plasmid

            duplicated = session.query(Plasmid).filter_by(id=duplicated_id).first()
            duplicated_gmos = session.query(GMO).filter_by(plasmid_id=duplicated_id).all()
            original_gmo = session.query(GMO).filter_by(plasmid_id=plasmid_id).first()

            assert duplicated is not None
            assert duplicated.id != plasmid_id
            assert len(duplicated_gmos) == 1
            assert original_gmo.destroyed_on == "2024-02-01"
        finally:
            session.close()

    def test_add_and_destroy_gmo(self, fresh_db):
        session = get_session(fresh_db)
        try:
            created = plasmid_service.create_plasmid(session, PlasmidCreate(name="pTEST002"))
            gmo = plasmid_service.add_gmo(
                session,
                created.id,
                GMOCreate(organism_name="E. coli", approval="S1", target_risk_group=1),
            )
            assert gmo.organism_name == "E. coli"
            assert gmo.created_on is not None

            destroyed = plasmid_service.destroy_gmo(session, gmo.id)
            assert destroyed.destroyed_on is not None
        finally:
            session.close()
