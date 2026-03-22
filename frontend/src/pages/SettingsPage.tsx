import { useEffect, useState } from "react";
import {
  Plus, Trash2, Construction, Copy, Check,
  Sun, Moon, Monitor, ExternalLink, Tag,
  SlidersHorizontal, User, Leaf, Plug, Info,
  ALargeSmall, LayoutPanelLeft,
} from "lucide-react";
import {
  applyDbAppearance,
  applyLocalAppearance,
  getLocalAppearance,
  setLocalAppearance,
  type LocalAppearance,
} from "@/lib/appearance";
import { COLOR_PRESETS, swatchColor } from "@/lib/theme-colors";
import { useTheme } from "@/components/theme-context";
import { toast } from "sonner";
import {
  settings as settingsApi,
  organisms as organismsApi,
  organismSelections,
  organismFavourites,
  releases as releasesApi,
  type Settings,
  type Organism,
  type OrganismSelectionItem,
  type OrganismFavouriteItem,
  type ReleaseNote,
} from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ── Helpers ──────────────────────────────────────────────────────────────────

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
        checked ? "bg-primary" : "bg-input"
      }`}
    >
      <span
        className={`pointer-events-none block h-4 w-4 rounded-full bg-background shadow-lg ring-0 transition-transform ${
          checked ? "translate-x-4" : "translate-x-0"
        }`}
      />
    </button>
  );
}

function SettingsGroup({ label, children }: { label?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      {label && (
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground px-1">
          {label}
        </p>
      )}
      <div className="border rounded-xl overflow-hidden divide-y divide-border bg-card">
        {children}
      </div>
    </div>
  );
}

function SettingsRow({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3 gap-4">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-snug">{label}</p>
        {description && (
          <p className="text-xs text-muted-foreground mt-0.5 leading-snug">{description}</p>
        )}
      </div>
      {children && <div className="shrink-0">{children}</div>}
    </div>
  );
}

function SettingsInput({
  label,
  description,
  id,
  value,
  onChange,
  onBlur,
  type,
  placeholder,
}: {
  label: string;
  description?: string;
  id: string;
  value: string;
  onChange: (v: string) => void;
  onBlur: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div className="px-4 py-3 space-y-1.5">
      <Label htmlFor={id} className="text-sm font-medium">
        {label}
      </Label>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      <Input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={(e) => onBlur(e.target.value)}
      />
    </div>
  );
}

function ComingSoon({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 px-4 py-3">
      <Construction className="h-4 w-4 text-muted-foreground shrink-0" />
      <span className="text-sm text-muted-foreground flex-1">{label}</span>
      <Badge variant="outline" className="text-[10px] px-1.5 py-0 shrink-0">
        coming soon
      </Badge>
    </div>
  );
}

function SectionTitle({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mb-5">
      <h2 className="text-base font-semibold tracking-tight">{title}</h2>
      {description && (
        <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
      )}
    </div>
  );
}

function renderInline(text: string) {
  const parts = text.split(/\*\*(.*?)\*\*/g);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <strong key={i} className="font-semibold text-foreground">
        {part}
      </strong>
    ) : (
      part
    ),
  );
}

function ReleaseNoteBody({ notes }: { notes: string }) {
  const lines = notes.split(/\r?\n/);
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        if (line.startsWith("## ")) {
          return (
            <p key={i} className="text-xs font-semibold text-foreground pt-2 first:pt-0">
              {line.slice(3)}
            </p>
          );
        }
        if (line.startsWith("- ")) {
          return (
            <p key={i} className="text-xs text-muted-foreground flex gap-1.5">
              <span className="shrink-0 text-muted-foreground/60">•</span>
              <span>{renderInline(line.slice(2))}</span>
            </p>
          );
        }
        if (line.trim() === "") return null;
        return (
          <p key={i} className="text-xs text-muted-foreground">
            {renderInline(line)}
          </p>
        );
      })}
    </div>
  );
}

// ── Nav ──────────────────────────────────────────────────────────────────────

type NavSection = "general" | "profile" | "organisms" | "integrations" | "about";

const NAV_ITEMS: { id: NavSection; label: string; icon: React.ElementType }[] = [
  { id: "general",      label: "General",      icon: SlidersHorizontal },
  { id: "profile",      label: "Profile",      icon: User              },
  { id: "organisms",    label: "Organisms",    icon: Leaf              },
  { id: "integrations", label: "Integrations", icon: Plug              },
  { id: "about",        label: "About",        icon: Info              },
];

// ── Props ─────────────────────────────────────────────────────────────────────

interface SettingsPageProps {
  accentPresetId: string;
  onAccentChange: (id: string) => void;
}

// ── Main component ────────────────────────────────────────────────────────────

export default function SettingsPage({ accentPresetId, onAccentChange }: SettingsPageProps) {
  const { theme, setTheme } = useTheme();
  const [activeSection, setActiveSection] = useState<NavSection>("general");
  const [data, setData] = useState<Settings | null>(null);
  const [localAppearance, setLocalAppearanceState] = useState<LocalAppearance>(getLocalAppearance);
  const [loading, setLoading] = useState(true);
  const [allOrganisms, setAllOrganisms] = useState<Organism[]>([]);
  const [targetOrganisms, setTargetOrganisms] = useState<OrganismSelectionItem[]>([]);
  const [favOrganisms, setFavOrganisms] = useState<OrganismFavouriteItem[]>([]);
  const [targetCombo, setTargetCombo] = useState("");
  const [favCombo, setFavCombo] = useState("");
  const [releaseNotes, setReleaseNotes] = useState<ReleaseNote[]>([]);
  const [releasesLoading, setReleasesLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      settingsApi.get(),
      organismsApi.list(),
      organismSelections.list(),
      organismFavourites.list(),
    ])
      .then(([s, orgs, targets, favs]) => {
        setData(s);
        setAllOrganisms(orgs);
        setTargetOrganisms(targets);
        setFavOrganisms(favs);
      })
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load settings"))
      .finally(() => setLoading(false));

    releasesApi
      .list()
      .then(setReleaseNotes)
      .catch(() => {})
      .finally(() => setReleasesLoading(false));
  }, []);

  const updateField = async (field: string, value: string | number) => {
    if (!data) return;
    try {
      const updated = await settingsApi.update({ [field]: value });
      setData(updated);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to save");
    }
  };

  const toggleField = async (field: string, current: number | null) => {
    await updateField(field, current ? 0 : 1);
  };

  const updateDbAppearance = async (field: string, value: number) => {
    if (!data) return;
    try {
      const updated = await settingsApi.update({ [field]: value });
      setData(updated);
      applyDbAppearance(updated.font_size, updated.scale !== null ? updated.scale : null, updated.horizontal_layout);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to save");
    }
  };

  const updateLocal = (patch: Partial<LocalAppearance>) => {
    setLocalAppearance(patch);
    applyLocalAppearance();
    setLocalAppearanceState(getLocalAppearance());
  };

  const addTargetOrganism = async () => {
    if (!targetCombo) return;
    try {
      const created = await organismSelections.create(targetCombo);
      setTargetOrganisms((prev) => [...prev, created]);
      setTargetCombo("");
      toast.success(`Added "${targetCombo}" to target organisms`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to add");
    }
  };

  const removeTargetOrganism = async (id: number) => {
    try {
      await organismSelections.delete(id);
      setTargetOrganisms((prev) => prev.filter((o) => o.id !== id));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to remove");
    }
  };

  const addFavOrganism = async () => {
    if (!favCombo) return;
    try {
      const created = await organismFavourites.create(favCombo);
      setFavOrganisms((prev) => [...prev, created]);
      setFavCombo("");
      toast.success(`Added "${favCombo}" to favourites`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to add");
    }
  };

  const removeFavOrganism = async (id: number) => {
    try {
      await organismFavourites.delete(id);
      setFavOrganisms((prev) => prev.filter((o) => o.id !== id));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to remove");
    }
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Loading…
      </div>
    );
  }

  // ── Section content ─────────────────────────────────────────────────────────

  const sections: Record<NavSection, React.ReactNode> = {
    general: (
      <div className="space-y-6">
        <SectionTitle title="General" description="Appearance and behaviour settings." />

        <SettingsGroup label="Appearance">
          {/* Theme mode */}
          <div className="px-4 py-3 space-y-2">
            <p className="text-sm font-medium">Mode</p>
            <div className="grid grid-cols-3 gap-2">
              {([
                { id: "light",  label: "Light",  Icon: Sun     },
                { id: "system", label: "System", Icon: Monitor },
                { id: "dark",   label: "Dark",   Icon: Moon    },
              ] as const).map(({ id, label, Icon }) => {
                const isActive = theme === id;
                return (
                  <button
                    key={id}
                    onClick={() => setTheme(id)}
                    className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      isActive
                        ? "border-primary bg-primary/8 text-primary font-medium"
                        : "border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Accent colour */}
          <div className="px-4 py-3 space-y-2">
            <p className="text-sm font-medium">Accent Colour</p>
            <div className="grid grid-cols-6 gap-2">
              {COLOR_PRESETS.map((preset) => {
                const isActive = accentPresetId === preset.id;
                return (
                  <button
                    key={preset.id}
                    onClick={() => onAccentChange(preset.id)}
                    title={preset.name}
                    className={`flex flex-col items-center gap-1.5 rounded-lg p-2 transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      isActive ? "bg-accent ring-2 ring-primary" : "hover:bg-muted"
                    }`}
                  >
                    <span
                      className="flex h-7 w-7 items-center justify-center rounded-full shadow-sm ring-1 ring-black/10 dark:ring-white/10"
                      style={{ backgroundColor: swatchColor(preset) }}
                    >
                      {isActive && <Check className="h-3.5 w-3.5 text-white drop-shadow" />}
                    </span>
                    <span
                      className={`text-[10px] leading-none ${
                        isActive ? "text-foreground font-medium" : "text-muted-foreground"
                      }`}
                    >
                      {preset.name}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Font size */}
          <div className="px-4 py-3 space-y-2">
            <div className="flex items-center gap-2">
              <ALargeSmall className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm font-medium">Text Size</p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {([
                { idx: 0, label: "Small"  },
                { idx: 1, label: "Medium" },
                { idx: 2, label: "Large"  },
              ]).map(({ idx, label }) => {
                const isActive = (data.font_size ?? 1) === idx;
                return (
                  <button
                    key={idx}
                    onClick={() => updateDbAppearance("font_size", idx)}
                    className={`rounded-lg border px-3 py-2 text-sm transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      isActive
                        ? "border-primary bg-primary/8 text-primary font-medium"
                        : "border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Density */}
          <div className="px-4 py-3 space-y-2">
            <div className="flex items-center gap-2">
              <LayoutPanelLeft className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm font-medium">Density</p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {([
                { idx: 0, label: "Compact"     },
                { idx: 1, label: "Comfortable" },
                { idx: 2, label: "Spacious"    },
              ]).map(({ idx, label }) => {
                const isActive = Math.round(data.scale ?? 1) === idx;
                return (
                  <button
                    key={idx}
                    onClick={() => updateDbAppearance("scale", idx)}
                    className={`rounded-lg border px-3 py-2 text-sm transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      isActive
                        ? "border-primary bg-primary/8 text-primary font-medium"
                        : "border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        </SettingsGroup>

        <SettingsGroup label="Display">
          {/* Date format */}
          <div className="px-4 py-3 space-y-2">
            <p className="text-sm font-medium">Date Format</p>
            <div className="grid grid-cols-2 gap-2">
              {([
                { id: "eu",  label: "DD.MM.YYYY", example: "22.03.2026" },
                { id: "iso", label: "YYYY-MM-DD", example: "2026-03-22" },
              ] as const).map(({ id, label, example }) => {
                const isActive = localAppearance.dateFormat === id;
                return (
                  <button
                    key={id}
                    onClick={() => updateLocal({ dateFormat: id })}
                    className={`flex flex-col items-start rounded-lg border px-3 py-2 text-sm transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      isActive
                        ? "border-primary bg-primary/8 text-primary font-medium"
                        : "border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    <span>{label}</span>
                    <span className="text-xs opacity-70 font-mono">{example}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Reduce motion */}
          <SettingsRow
            label="Reduce Motion"
            description="Disable animations and transitions throughout the interface."
          >
            <Toggle
              checked={localAppearance.reduceMotion}
              onChange={(v) => updateLocal({ reduceMotion: v })}
            />
          </SettingsRow>

          {/* Monospace GenBank */}
          <SettingsRow
            label="Monospace GenBank viewer"
            description="Display GenBank sequence data in a fixed-width font."
          >
            <Toggle
              checked={localAppearance.monoGenbank}
              onChange={(v) => updateLocal({ monoGenbank: v })}
            />
          </SettingsRow>

          {/* Horizontal layout */}
          <SettingsRow
            label="Horizontal layout"
            description="Show plasmid details side-by-side instead of stacked."
          >
            <Toggle
              checked={!!data.horizontal_layout}
              onChange={() => toggleField("horizontal_layout", data.horizontal_layout)}
            />
          </SettingsRow>
        </SettingsGroup>

        <SettingsGroup label="Behaviour">
          <SettingsRow
            label="Duplicate GMOs"
            description="Create duplicate GMO entries when adding organisms to plasmids."
          >
            <Toggle
              checked={!!data.duplicate_gmos}
              onChange={() => toggleField("duplicate_gmos", data.duplicate_gmos)}
            />
          </SettingsRow>
          <SettingsRow
            label="Upload completed only"
            description="Only upload plasmids with 'Complete' status to servers."
          >
            <Toggle
              checked={!!data.upload_completed}
              onChange={() => toggleField("upload_completed", data.upload_completed)}
            />
          </SettingsRow>
        </SettingsGroup>
      </div>
    ),

    profile: (
      <div className="space-y-6">
        <SectionTitle title="Profile" description="Your identity used in exports and Formblatt Z." />

        <SettingsGroup>
          <SettingsInput
            id="s-name"
            label="Name"
            value={data.name || ""}
            onChange={(v) => setData({ ...data, name: v })}
            onBlur={(v) => updateField("name", v)}
          />
          <SettingsInput
            id="s-initials"
            label="Initials"
            value={data.initials || ""}
            onChange={(v) => setData({ ...data, initials: v })}
            onBlur={(v) => updateField("initials", v)}
          />
          <SettingsInput
            id="s-email"
            label="Email"
            type="email"
            value={data.email || ""}
            onChange={(v) => setData({ ...data, email: v })}
            onBlur={(v) => updateField("email", v)}
          />
          <SettingsInput
            id="s-institution"
            label="GMO Institute"
            value={data.institution || ""}
            onChange={(v) => setData({ ...data, institution: v })}
            onBlur={(v) => updateField("institution", v)}
          />
        </SettingsGroup>
      </div>
    ),

    organisms: (
      <div className="space-y-6">
        <SectionTitle
          title="Organisms"
          description="Configure which organisms appear in GMO entry dropdowns."
        />

        <SettingsGroup label="Target Organisms">
          <div className="px-4 py-3 space-y-3">
            <p className="text-xs text-muted-foreground">
              Organisms available as GMO targets when adding organisms to plasmids.
            </p>
            <div className="flex gap-2">
              <Select value={targetCombo} onValueChange={(v) => { if (v) setTargetCombo(v); }}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Select organism…" />
                </SelectTrigger>
                <SelectContent>
                  {allOrganisms.map((o) => (
                    <SelectItem key={o.id} value={o.short_name || `org-${o.id}`}>
                      {o.short_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button size="sm" className="gap-1.5" onClick={addTargetOrganism} disabled={!targetCombo}>
                <Plus className="h-4 w-4" />
                Add
              </Button>
            </div>
            <div className="space-y-1">
              {targetOrganisms.length > 0 ? (
                targetOrganisms.map((t) => (
                  <div
                    key={t.id}
                    className="flex items-center justify-between px-3 py-2 bg-muted rounded-md text-sm"
                  >
                    <span>{t.organism_name}</span>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => removeTargetOrganism(t.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                    </Button>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground py-1">No target organisms configured.</p>
              )}
            </div>
          </div>
        </SettingsGroup>

        <SettingsGroup label="Favourite Organisms">
          <div className="px-4 py-3 space-y-3">
            <p className="text-xs text-muted-foreground">
              Quick-access subset shown first in organism dropdowns. Must also exist in Target Organisms.
            </p>
            <div className="flex gap-2">
              <Select value={favCombo} onValueChange={(v) => { if (v) setFavCombo(v); }}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Select from targets…" />
                </SelectTrigger>
                <SelectContent>
                  {targetOrganisms.map((t) => (
                    <SelectItem key={t.id} value={t.organism_name || `t-${t.id}`}>
                      {t.organism_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button size="sm" className="gap-1.5" onClick={addFavOrganism} disabled={!favCombo}>
                <Copy className="h-4 w-4" />
                Add
              </Button>
            </div>
            <div className="space-y-1">
              {favOrganisms.length > 0 ? (
                favOrganisms.map((f) => (
                  <div
                    key={f.id}
                    className="flex items-center justify-between px-3 py-2 bg-muted rounded-md text-sm"
                  >
                    <span>{f.organism_name}</span>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => removeFavOrganism(f.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                    </Button>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground py-1">No favourite organisms configured.</p>
              )}
            </div>
          </div>
        </SettingsGroup>
      </div>
    ),

    integrations: (
      <div className="space-y-6">
        <SectionTitle title="Integrations" description="Connect to external services." />

        <SettingsGroup label="Servers">
          <SettingsRow
            label="JBEI/ice"
            description="Upload plasmid data to JBEI/ice registry."
          >
            <Toggle
              checked={!!data.use_ice}
              onChange={() => toggleField("use_ice", data.use_ice)}
            />
          </SettingsRow>
          <SettingsRow
            label="Filebrowser"
            description="Upload files to a Filebrowser server."
          >
            <Toggle
              checked={!!data.use_file_browser}
              onChange={() => toggleField("use_file_browser", data.use_file_browser)}
            />
          </SettingsRow>
          {(!!data.use_ice || !!data.use_file_browser) && (
            <ComingSoon label="Server credentials management" />
          )}
          <SettingsRow
            label="Zip files"
            description="Compress files before uploading (faster)."
          >
            <Toggle
              checked={!!data.zip_files}
              onChange={() => toggleField("zip_files", data.zip_files)}
            />
          </SettingsRow>
        </SettingsGroup>

        <SettingsGroup label="Google">
          <SettingsRow
            label="Google Drive Folder"
            description="Upload plasmid files to Google Drive."
          >
            <Toggle
              checked={!!data.use_gdrive}
              onChange={() => toggleField("use_gdrive", data.use_gdrive)}
            />
          </SettingsRow>
          {!!data.use_gdrive && (
            <SettingsInput
              id="s-gdrive-id"
              label="GDrive Folder ID"
              placeholder="ID from the folder link"
              value={data.drive_folder_id || ""}
              onChange={(v) => setData({ ...data, drive_folder_id: v })}
              onBlur={(v) => updateField("drive_folder_id", v)}
            />
          )}
          <SettingsRow
            label="Autosync Google Sheets"
            description="Automatically sync glossary with Google Sheets."
          >
            <Toggle
              checked={!!data.autosync}
              onChange={() => toggleField("autosync", data.autosync)}
            />
          </SettingsRow>
          {!!data.autosync && (
            <SettingsInput
              id="s-gsheet-id"
              label="Google Sheets ID"
              placeholder="Spreadsheet ID from the URL"
              value={data.glossary_sheet_id || ""}
              onChange={(v) => setData({ ...data, glossary_sheet_id: v })}
              onBlur={(v) => updateField("glossary_sheet_id", v)}
            />
          )}
        </SettingsGroup>

        <SettingsGroup label="Coming Soon">
          <ComingSoon label="Upload to JBEI/ice, Filebrowser, and GDrive" />
          <ComingSoon label="Google Sheets glossary sync" />
        </SettingsGroup>
      </div>
    ),

    about: (
      <div className="space-y-6">
        <div className="flex items-start justify-between">
          <SectionTitle title="About GMOCU" description="GMO documentation and plasmid management." />
          <a
            href="https://github.com/wfrs/GMOCUv2"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mt-1 shrink-0"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            GitHub
          </a>
        </div>

        <SettingsGroup>
          <div className="px-4 py-4 flex items-center gap-3">
            <span className="text-xl font-bold tracking-tight">GMOCU</span>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
              v{releaseNotes[0]?.version.replace(/^v/, "") ?? "2.1.0"}
            </span>
          </div>
        </SettingsGroup>

        <div className="space-y-1.5">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground px-1">
            What's New
          </p>

          {releasesLoading && (
            <p className="text-sm text-muted-foreground px-1">Loading release notes…</p>
          )}

          {!releasesLoading && releaseNotes.length === 0 && (
            <p className="text-sm text-muted-foreground px-1">
              No releases published yet.{" "}
              <a
                href="https://github.com/wfrs/GMOCUv2/releases"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-foreground"
              >
                View on GitHub
              </a>
            </p>
          )}

          {releaseNotes.length > 0 && (
            <div className="border rounded-xl overflow-hidden divide-y divide-border bg-card">
              {releaseNotes.map((r) => (
                <div key={r.version} className="px-4 py-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Tag className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-semibold hover:text-primary transition-colors"
                    >
                      {r.version}
                    </a>
                    {r.prerelease && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded border border-amber-300 text-amber-600 dark:text-amber-400">
                        pre-release
                      </span>
                    )}
                    {r.date && (
                      <span className="text-xs text-muted-foreground ml-auto">{r.date}</span>
                    )}
                  </div>
                  {r.notes && (
                    <div className="ml-5">
                      <ReleaseNoteBody notes={r.notes} />
                    </div>
                  )}
                </div>
              ))}
              <div className="px-4 py-3">
                <a
                  href="https://github.com/wfrs/GMOCUv2/releases"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  View all releases on GitHub
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    ),
  };

  // ── Layout ────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your profile, integrations, and preferences.
        </p>
      </div>

      <div className="flex gap-8 items-start">
        {/* Left nav rail */}
        <nav className="w-44 shrink-0 sticky top-4 space-y-0.5">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
            const isActive = activeSection === id;
            return (
              <button
                key={id}
                onClick={() => setActiveSection(id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring text-left ${
                  isActive
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </button>
            );
          })}
        </nav>

        {/* Right content */}
        <div className="flex-1 min-w-0 pb-10">
          {sections[activeSection]}
        </div>
      </div>
    </div>
  );
}
