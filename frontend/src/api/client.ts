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
  target_risk_group: number | null;
  created_on: string | null;
  destroyed_on: string | null;
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
  addGmo: (plasmidId: number, data: { organism_name: string; approval?: string; target_risk_group?: number }) =>
    request<GMO>(`/plasmids/${plasmidId}/gmos`, { method: 'POST', body: JSON.stringify(data) }),
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

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
}

export const database = {
  health: () => request<HealthResponse>('/health'),
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/database/upload', { method: 'POST', body: formData });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || detail.error || res.statusText);
    }
    return res.json();
  },
};
