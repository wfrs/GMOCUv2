"""SQLAlchemy models for the native v2 GMOCU schema."""

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, synonym

Base = declarative_base()


class PlasmidStatus(Base):
    __tablename__ = "plasmid_statuses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, default="Planned")

    value = synonym("name")


class Plasmid(Base):
    __tablename__ = "plasmids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, default="pXX000")
    alias = Column(Text)
    status_id = Column(Integer, ForeignKey("plasmid_statuses.id"), default=4)
    genbank_flag = Column(Text)
    purpose = Column(Text)
    summary = Column(Text)
    genbank_content = Column(Text)
    genbank_filename = Column(Text)
    attachment_id = Column(Integer)
    clone = Column(Text)
    backbone_vector = Column(Text)
    marker = Column(Text)
    target_organism_selection_id = Column(
        Integer,
        ForeignKey("organism_selections.id"),
    )
    target_risk_group = Column(Integer, default=1)
    created_on = Column(Text, default=text("date('now')"))
    destroyed_on = Column(Text)
    recorded_on = Column(Text, default=text("date('now')"))

    status_ref = relationship("PlasmidStatus", foreign_keys=[status_id])
    cassettes = relationship("Cassette", back_populates="plasmid", lazy="select")
    gmos = relationship("Gmo", back_populates="plasmid", lazy="select")
    attachments = relationship("Attachment", back_populates="plasmid", lazy="select")

    status = synonym("status_id")
    gb = synonym("genbank_flag")
    genebank = synonym("genbank_content")
    gb_name = synonym("genbank_filename")
    FKattachment = synonym("attachment_id")
    organism_selector = synonym("target_organism_selection_id")
    target_RG = synonym("target_risk_group")
    generated = synonym("created_on")
    destroyed = synonym("destroyed_on")
    date = synonym("recorded_on")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_blob = Column(LargeBinary)
    filename = Column(Text)
    plasmid_id = Column(Integer, ForeignKey("plasmids.id", onupdate="CASCADE"))

    plasmid = relationship("Plasmid", back_populates="attachments")

    attach_id = synonym("id")
    file = synonym("file_blob")
    Filename = synonym("filename")


class Cassette(Base):
    __tablename__ = "cassettes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, default="Empty")
    plasmid_id = Column(Integer, ForeignKey("plasmids.id", onupdate="CASCADE"))

    plasmid = relationship("Plasmid", back_populates="cassettes")

    cassette_id = synonym("id")


class Gmo(Base):
    __tablename__ = "gmos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    summary = Column(Text)
    organism_name = Column(Text)
    approval = Column(Text)
    plasmid_id = Column(Integer, ForeignKey("plasmids.id", onupdate="CASCADE"))
    target_risk_group = Column(Integer)
    created_on = Column(Text, default=text("date('now')"))
    destroyed_on = Column(Text)
    entry_date = Column(Text)

    plasmid = relationship("Plasmid", back_populates="gmos")

    organism_id = synonym("id")
    GMO_summary = synonym("summary")
    target_RG = synonym("target_risk_group")
    date_generated = synonym("created_on")
    date_destroyed = synonym("destroyed_on")


class OrganismSelection(Base):
    __tablename__ = "organism_selections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organism_name = Column(Text)

    orga_sel_id = synonym("id")


class OrganismFavourite(Base):
    __tablename__ = "organism_favourites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organism_name = Column(Text)

    orga_fav_id = synonym("id")
    organism_fav_name = synonym("organism_name")


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    annotation = Column(Text)
    alias = Column(Text)
    risk = Column(Text, default="No Risk")
    organism = Column(Text)
    uid = Column(
        String(32),
        nullable=False,
        default=text("lower(hex(randomblob(16)))"),
    )
    synced = Column(Integer, default=0)


class Organism(Base):
    __tablename__ = "organisms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(Text)
    short_name = Column(Text)
    risk_group = Column(Text)
    uid = Column(
        String(32),
        nullable=False,
        default=text("lower(hex(randomblob(16)))"),
    )
    synced = Column(Integer, default=0)

    RG = synonym("risk_group")


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text)
    initials = Column(Text)
    email = Column(Text)
    institution = Column(Text)
    ice_credentials_id = Column(Integer, ForeignKey("ice_credentials.id"))
    glossary_sheet_id = Column(Text)
    duplicate_gmos = Column(Integer, default=0)
    upload_completed = Column(Integer, default=0)
    upload_abi = Column(Integer, default=0)
    scale = Column(Float, default=1)
    font_size = Column(Integer, default=13)
    theme = Column(Text, default="Reddit")
    horizontal_layout = Column(Integer, default=1)
    use_ice = Column(Integer, default=0)
    use_file_browser = Column(Integer, default=0)
    use_gdrive = Column(Integer, default=0)
    drive_folder_id = Column(Text, default="ID from link")
    zip_files = Column(Integer, default=1)
    autosync = Column(Integer, default=0)
    date_format = Column(Text, default="eu")
    reduce_motion = Column(Integer, default=0)
    mono_genbank = Column(Integer, default=0)

    credentials = relationship("IceCredentials", foreign_keys=[ice_credentials_id])

    ice = synonym("ice_credentials_id")
    gdrive_glossary = synonym("glossary_sheet_id")
    style = synonym("theme")
    use_filebrowser = synonym("use_file_browser")
    gdrive_id = synonym("drive_folder_id")


class IceCredentials(Base):
    __tablename__ = "ice_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alias = Column(Text)
    ice_instance = Column(Text)
    ice_token_client = Column(Text)
    ice_token = Column(Text)
    file_browser_instance = Column(Text)
    file_browser_user = Column(Text)
    file_browser_password = Column(Text)

    filebrowser_instance = synonym("file_browser_instance")
    filebrowser_user = synonym("file_browser_user")
    filebrowser_pwd = synonym("file_browser_password")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    action      = Column(Text)     # "create" | "update" | "delete"
    entity_type = Column(Text)     # "plasmid" | "feature" | "organism"
    entity_id   = Column(Integer)
    entity_name = Column(Text)     # display name snapshot (survives deletion)
    field       = Column(Text)     # for "update": which field changed
    old_value   = Column(Text)     # previous value
    new_value   = Column(Text)     # new value
    timestamp   = Column(Text, default=text("datetime('now')"))


class SchemaMeta(Base):
    __tablename__ = "schema_meta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schema_version = Column(Integer, nullable=False)
    migrated_from = Column(Text)
    migrated_at = Column(Text, default=text("CURRENT_TIMESTAMP"))


# Compatibility aliases for the existing service/test layer.
SelectionValue = PlasmidStatus
GMO = Gmo
Settings = AppSettings


def get_engine(db_path: str):
    """Create a SQLAlchemy engine for the given SQLite database path."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(db_path: str):
    """Create a new session for the given database path."""
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


_engine = None
_SessionLocal = None


def init_engine(db_path: str):
    """Initialize the global engine and session factory."""
    global _engine, _SessionLocal
    _engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
