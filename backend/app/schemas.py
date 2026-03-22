"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel


# --- Plasmids ---

class CassetteOut(BaseModel):
    id: int
    content: str | None = None

    model_config = {"from_attributes": True}


class GMOOut(BaseModel):
    id: int
    organism_name: str | None = None
    summary: str | None = None
    approval: str | None = None
    target_risk_group: int | None = None
    created_on: str | None = None
    destroyed_on: str | None = None

    model_config = {"from_attributes": True}


class AttachmentMeta(BaseModel):
    id: int
    filename: str | None = None

    model_config = {"from_attributes": True}


class PlasmidListOut(BaseModel):
    """Lightweight schema for list endpoint — no nested relationships."""
    id: int
    name: str | None = None
    alias: str | None = None
    status_id: int | None = None
    clone: str | None = None
    backbone_vector: str | None = None
    marker: str | None = None
    target_organism_selection_id: int | None = None
    target_risk_group: int | None = None
    created_on: str | None = None
    destroyed_on: str | None = None
    recorded_on: str | None = None

    model_config = {"from_attributes": True}


class PlasmidOut(BaseModel):
    id: int
    name: str | None = None
    alias: str | None = None
    status_id: int | None = None
    genbank_content: str | None = None
    purpose: str | None = None
    summary: str | None = None
    genbank_filename: str | None = None
    clone: str | None = None
    backbone_vector: str | None = None
    marker: str | None = None
    target_organism_selection_id: int | None = None
    target_risk_group: int | None = None
    created_on: str | None = None
    destroyed_on: str | None = None
    recorded_on: str | None = None
    cassettes: list[CassetteOut] = []
    gmos: list[GMOOut] = []
    attachments: list[AttachmentMeta] = []

    model_config = {"from_attributes": True}


class PlasmidCreate(BaseModel):
    name: str = "pXX000"
    alias: str | None = None
    status_id: int = 4
    purpose: str | None = None
    summary: str | None = None
    genbank_content: str | None = None
    genbank_filename: str | None = None
    clone: str | None = None
    backbone_vector: str | None = None
    marker: str | None = None
    target_organism_selection_id: int | None = None
    target_risk_group: int = 1
    recorded_on: str | None = None


class PlasmidUpdate(BaseModel):
    name: str | None = None
    alias: str | None = None
    status_id: int | None = None
    purpose: str | None = None
    summary: str | None = None
    genbank_content: str | None = None
    genbank_filename: str | None = None
    clone: str | None = None
    backbone_vector: str | None = None
    marker: str | None = None
    target_organism_selection_id: int | None = None
    target_risk_group: int | None = None
    created_on: str | None = None
    destroyed_on: str | None = None
    recorded_on: str | None = None


class CassetteUpdate(BaseModel):
    content: str


class GMOCreate(BaseModel):
    organism_name: str
    approval: str = "-"
    target_risk_group: int = 1
    created_on: str | None = None
    destroyed_on: str | None = None


class GMOUpdate(BaseModel):
    organism_name: str | None = None
    approval: str | None = None
    target_risk_group: int | None = None
    created_on: str | None = None
    destroyed_on: str | None = None


class GenBankUpload(BaseModel):
    genbank_filename: str
    genbank_content: str


# --- Features ---

class FeatureOut(BaseModel):
    id: int
    annotation: str | None = None
    alias: str | None = None
    risk: str | None = None
    organism: str | None = None
    uid: str | None = None

    model_config = {"from_attributes": True}


class FeatureCreate(BaseModel):
    annotation: str
    alias: str | None = None
    risk: str = "No Risk"
    organism: str | None = None


class FeatureUpdate(BaseModel):
    annotation: str | None = None
    alias: str | None = None
    risk: str | None = None
    organism: str | None = None


# --- Organisms ---

class OrganismOut(BaseModel):
    id: int
    full_name: str | None = None
    short_name: str | None = None
    risk_group: str | None = None
    uid: str | None = None

    model_config = {"from_attributes": True}


class OrganismCreate(BaseModel):
    full_name: str
    short_name: str
    risk_group: str = "1"


class OrganismUpdate(BaseModel):
    full_name: str | None = None
    short_name: str | None = None
    risk_group: str | None = None


# --- Settings ---

class SettingsOut(BaseModel):
    id: int
    name: str | None = None
    initials: str | None = None
    email: str | None = None
    institution: str | None = None
    ice_credentials_id: int | None = None
    duplicate_gmos: int | None = None
    upload_completed: int | None = None
    upload_abi: int | None = None
    scale: float | None = None
    font_size: int | None = None
    theme: str | None = None
    horizontal_layout: int | None = None
    use_ice: int | None = None
    use_file_browser: int | None = None
    use_gdrive: int | None = None
    glossary_sheet_id: str | None = None
    drive_folder_id: str | None = None
    zip_files: int | None = None
    autosync: int | None = None

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    name: str | None = None
    initials: str | None = None
    email: str | None = None
    institution: str | None = None
    ice_credentials_id: int | None = None
    duplicate_gmos: int | None = None
    upload_completed: int | None = None
    upload_abi: int | None = None
    scale: float | None = None
    font_size: int | None = None
    theme: str | None = None
    horizontal_layout: int | None = None
    use_ice: int | None = None
    use_file_browser: int | None = None
    use_gdrive: int | None = None
    glossary_sheet_id: str | None = None
    drive_folder_id: str | None = None
    zip_files: int | None = None
    autosync: int | None = None


# --- Organism selections / favourites ---

class OrganismSelectionOut(BaseModel):
    id: int
    organism_name: str | None = None

    model_config = {"from_attributes": True}


class OrganismSelectionCreate(BaseModel):
    organism_name: str


class OrganismFavouriteOut(BaseModel):
    id: int
    organism_name: str | None = None

    model_config = {"from_attributes": True}


class OrganismFavouriteCreate(BaseModel):
    organism_name: str


# --- Activity log ---

class ActivityLogOut(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: int
    entity_name: str | None = None
    field: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    timestamp: str | None = None

    model_config = {"from_attributes": True}


# --- ICE credentials ---

class IceCredentialsOut(BaseModel):
    id: int
    alias: str | None = None
    ice_instance: str | None = None
    ice_token_client: str | None = None
    ice_token: str | None = None
    file_browser_instance: str | None = None
    file_browser_user: str | None = None
    file_browser_password: str | None = None

    model_config = {"from_attributes": True}


class IceCredentialsCreate(BaseModel):
    alias: str
    ice_instance: str | None = None
    ice_token_client: str | None = None
    ice_token: str | None = None
    file_browser_instance: str | None = None
    file_browser_user: str | None = None
    file_browser_password: str | None = None


class IceCredentialsUpdate(BaseModel):
    alias: str | None = None
    ice_instance: str | None = None
    ice_token_client: str | None = None
    ice_token: str | None = None
    file_browser_instance: str | None = None
    file_browser_user: str | None = None
    file_browser_password: str | None = None
