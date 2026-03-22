const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Types ---

export interface PlasmidListItem {
  id: number;
  name: string;
  alias: string | null;
  status_id: number | null;
  clone: string | null;
  backbone_vector: string | null;
  marker: string | null;
  target_organism_selection_id: number | null;
  target_risk_group: number | null;
  created_on: string | null;
  destroyed_on: string | null;
  recorded_on: string | null;
}

export interface Plasmid extends PlasmidListItem {
  genbank_content: string | null;
  purpose: string | null;
  summary: string | null;
  genbank_filename: string | null;
  cassettes: Cassette[];
  gmos: GMO[];
  attachments: AttachmentMeta[];
}

export interface Cassette {
  id: number;
  content: string | null;
}

export interface GMO {
  id: number;
  organism_name: string | null;
  summary: string | null;
  approval: string | null;
  target_risk_group: number | null;
  created_on: string | null;
  destroyed_on: string | null;
}

export interface AttachmentMeta {
  id: number;
  filename: string | null;
}

export interface Feature {
  id: number;
  annotation: string | null;
  alias: string | null;
  risk: string | null;
  organism: string | null;
  uid: string | null;
}

export interface Organism {
  id: number;
  full_name: string | null;
  short_name: string | null;
  risk_group: string | null;
  uid: string | null;
}

export interface Settings {
  id: number;
  name: string | null;
  initials: string | null;
  email: string | null;
  institution: string | null;
  ice_credentials_id: number | null;
  duplicate_gmos: number | null;
  upload_completed: number | null;
  upload_abi: number | null;
  scale: number | null;
  font_size: number | null;
  theme: string | null;
  horizontal_layout: number | null;
  use_ice: number | null;
  use_file_browser: number | null;
  use_gdrive: number | null;
  glossary_sheet_id: string | null;
  drive_folder_id: string | null;
  zip_files: number | null;
  autosync: number | null;
}

export interface OrganismSelectionItem {
  id: number;
  organism_name: string | null;
}

export interface OrganismFavouriteItem {
  id: number;
  organism_name: string | null;
}

export interface IceCredentials {
  id: number;
  alias: string | null;
  ice_instance: string | null;
  ice_token_client: string | null;
  ice_token: string | null;
  file_browser_instance: string | null;
  file_browser_user: string | null;
  file_browser_password: string | null;
}

// --- API functions ---

export const plasmids = {
  list: (search?: string) => request<PlasmidListItem[]>(`/plasmids/${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  get: (id: number) => request<Plasmid>(`/plasmids/${id}`),
  create: (data: Partial<Plasmid>) => request<Plasmid>('/plasmids/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Partial<Plasmid>) => request<Plasmid>(`/plasmids/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/plasmids/${id}`, { method: 'DELETE' }),
  duplicate: (id: number) => request<Plasmid>(`/plasmids/${id}/duplicate`, { method: 'POST' }),
  // Cassettes
  addCassette: (plasmidId: number) => request<Cassette>(`/plasmids/${plasmidId}/cassettes`, { method: 'POST' }),
  updateCassette: (cassetteId: number, content: string) => request<Cassette>(`/plasmids/cassettes/${cassetteId}`, { method: 'PATCH', body: JSON.stringify({ content }) }),
  deleteCassette: (cassetteId: number) => request<void>(`/plasmids/cassettes/${cassetteId}`, { method: 'DELETE' }),
  // GMOs
  addGmo: (
    plasmidId: number,
    data: {
      organism_name: string;
      approval?: string;
      target_risk_group?: number;
      created_on?: string | null;
      destroyed_on?: string | null;
    },
  ) =>
    request<GMO>(`/plasmids/${plasmidId}/gmos`, { method: 'POST', body: JSON.stringify(data) }),
  updateGmo: (
    gmoId: number,
    data: {
      organism_name?: string | null;
      approval?: string | null;
      target_risk_group?: number | null;
      created_on?: string | null;
      destroyed_on?: string | null;
    },
  ) => request<GMO>(`/plasmids/gmos/${gmoId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteGmo: (gmoId: number) => request<void>(`/plasmids/gmos/${gmoId}`, { method: 'DELETE' }),
  destroyGmo: (gmoId: number) => request<GMO>(`/plasmids/gmos/${gmoId}/destroy`, { method: 'PATCH' }),
  // GenBank
  uploadGenbank: (plasmidId: number, genbank_filename: string, genbank_content: string) =>
    request<Plasmid>(`/plasmids/${plasmidId}/genbank`, { method: 'PUT', body: JSON.stringify({ genbank_filename, genbank_content }) }),
  deleteGenbank: (plasmidId: number) => request<Plasmid>(`/plasmids/${plasmidId}/genbank`, { method: 'DELETE' }),
  // Attachments
  uploadAttachment: async (plasmidId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`/api/plasmids/${plasmidId}/attachments`, { method: 'POST', body: formData });
    if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || res.statusText); }
    return res.json() as Promise<AttachmentMeta>;
  },
  deleteAttachment: (attachId: number) => request<void>(`/plasmids/attachments/${attachId}`, { method: 'DELETE' }),
};

export const features = {
  list: (search?: string) => request<Feature[]>(`/features/${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  get: (id: number) => request<Feature>(`/features/${id}`),
  create: (data: Partial<Feature>) => request<Feature>('/features/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Partial<Feature>) => request<Feature>(`/features/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/features/${id}`, { method: 'DELETE' }),
};

export const organisms = {
  list: (search?: string) => request<Organism[]>(`/organisms/${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  get: (id: number) => request<Organism>(`/organisms/${id}`),
  create: (data: Partial<Organism>) => request<Organism>('/organisms/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Partial<Organism>) => request<Organism>(`/organisms/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/organisms/${id}`, { method: 'DELETE' }),
};

export const settings = {
  get: () => request<Settings>('/settings/'),
  update: (data: Partial<Settings>) => request<Settings>('/settings/', { method: 'PATCH', body: JSON.stringify(data) }),
};

export const organismSelections = {
  list: () => request<OrganismSelectionItem[]>('/organism-selections/'),
  create: (organism_name: string) => request<OrganismSelectionItem>('/organism-selections/', { method: 'POST', body: JSON.stringify({ organism_name }) }),
  delete: (id: number) => request<void>(`/organism-selections/${id}`, { method: 'DELETE' }),
};

export const organismFavourites = {
  list: () => request<OrganismFavouriteItem[]>('/organism-favourites/'),
  create: (organism_name: string) => request<OrganismFavouriteItem>('/organism-favourites/', { method: 'POST', body: JSON.stringify({ organism_name }) }),
  delete: (id: number) => request<void>(`/organism-favourites/${id}`, { method: 'DELETE' }),
};

export const iceCredentials = {
  list: () => request<IceCredentials[]>('/ice-credentials/'),
  create: (data: Partial<IceCredentials>) => request<IceCredentials>('/ice-credentials/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Partial<IceCredentials>) => request<IceCredentials>(`/ice-credentials/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/ice-credentials/${id}`, { method: 'DELETE' }),
};

export interface ActivityLog {
  id: number;
  action: string;       // "create" | "update" | "delete"
  entity_type: string;  // "plasmid" | "feature" | "organism"
  entity_id: number;
  entity_name: string | null;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
  timestamp: string | null;
}

export const activityLog = {
  list: (entity_type?: string) =>
    request<ActivityLog[]>(`/activity/${entity_type ? `?entity_type=${encodeURIComponent(entity_type)}` : ''}`),
};

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
}

export interface DatabaseImportStep {
  id: string;
  label: string;
  detail: string;
}

export interface DatabaseImportReport {
  filename: string;
  file_size_bytes: number | null;
  destination_path: string;
  inspection: {
    kind: string;
    legacy_version: string | null;
    schema_version: number | null;
    target_schema_version: number;
  };
  counts: {
    plasmids: number;
    features: number;
    organisms: number;
    gmos: number;
    cassettes: number;
    attachments: number;
    organism_selections: number;
    organism_favourites: number;
  };
  planned_steps: DatabaseImportStep[];
}

export interface DatabaseImportResult {
  status: string;
  message: string;
  backup_path: string | null;
  import_report: DatabaseImportReport;
  activated_report: DatabaseImportReport;
  completed_steps: string[];
}

export interface DatabaseImportJobStep extends DatabaseImportStep {
  status: "pending" | "running" | "completed" | "failed";
  started_at: string | null;
  finished_at: string | null;
}

export interface DatabaseImportJob {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  error: string | null;
  report: DatabaseImportReport;
  result: DatabaseImportResult | null;
  active_step_id: string | null;
  steps: DatabaseImportJobStep[];
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface FormblattValidation {
  ready: boolean;
  issues: string[];
  gmo_count: number;
}

export interface HealthReport {
  features: {
    complete: boolean;
    missing: string[];
    redundant: string[];
    duplicates: string[];
    has_empty_fields: boolean;
  };
  organisms: {
    complete: boolean;
    missing_pairs: string[];
    redundant: string[];
    duplicates: string[];
  };
  plasmids: {
    duplicates: string[];
    no_backbone: string[];
    no_cassettes: string[];
    no_gmos: string[];
  };
}

export type FormblattLang = 'de' | 'en';

export interface FormblattRow {
  // German keys (lang=de) — values differ by lang but keys always match the chosen lang
  [key: string]: string | number | null;
}

export const FORMBLATT_COLUMNS_DE = [
  'Nr.', 'Spender Bezeichnung', 'Spender RG',
  'Empfänger Bezeichnung', 'Empfänger RG',
  'Ausgangsvektor Bezeichnung',
  'Übertragene Nukleinsäure Bezeichnung',
  'Übertragene Nukleinsäure Gefährdungspotential',
  'GVO Bezeichnung', 'GVO RG', 'GVO Zulassung',
  'GVO erzeugt/erhalten am', 'GVO entsorgt am',
  'Datum des Eintrags',
] as const;

export const FORMBLATT_COLUMNS_EN = [
  'No', 'Donor designation', 'Donor RG',
  'Recipient designation', 'Recipient RG',
  'Source vector designation',
  'Transferred nucleic acid designation',
  'Transferred nucleic acid risk potential',
  'GMO name', 'GMO RG', 'GMO approval',
  'GMO generated', 'GMO disposal', 'Entry date',
] as const;

export const reports = {
  validateFormblatt: () => request<FormblattValidation>('/reports/formblatt-z/validate'),
  rows: (lang: FormblattLang) => request<FormblattRow[]>(`/reports/formblatt-z/rows?lang=${lang}`),
  downloadUrl: (lang: FormblattLang) => `/api/reports/formblatt-z?lang=${lang}`,
  plasmidListUrl: () => '/api/reports/plasmid-list',
  health: () => request<HealthReport>('/reports/health'),
};

export const database = {
  health: () => request<HealthResponse>('/health'),
  inspect: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/database/inspect', { method: 'POST', body: formData });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || detail.error || res.statusText);
    }
    return res.json() as Promise<DatabaseImportReport>;
  },
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/database/upload', { method: 'POST', body: formData });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || detail.error || res.statusText);
    }
    return res.json() as Promise<DatabaseImportResult>;
  },
  startImportJob: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/database/import-jobs', { method: 'POST', body: formData });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || detail.error || res.statusText);
    }
    return res.json() as Promise<DatabaseImportJob>;
  },
  getImportJob: (jobId: string) => request<DatabaseImportJob>(`/database/import-jobs/${jobId}`),
};
