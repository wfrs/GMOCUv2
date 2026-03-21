import { useEffect, useState } from "react";
import { Plus, Trash2, Construction, Copy, Check, Sun, Moon, Monitor } from "lucide-react";
import { COLOR_PRESETS, swatchColor } from "@/lib/theme-colors";
import { useTheme } from "@/components/theme-context";
import { toast } from "sonner";
import {
  settings as settingsApi,
  organisms as organismsApi,
  organismSelections,
  organismFavourites,
  type Settings,
  type Organism,
  type OrganismSelectionItem,
  type OrganismFavouriteItem,
} from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

function SectionHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      {description && (
        <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
      )}
    </div>
  );
}

function ComingSoon({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground py-1">
      <Construction className="h-4 w-4" />
      <span>{label}</span>
      <Badge variant="outline" className="text-[10px] px-1.5 py-0">
        coming soon
      </Badge>
    </div>
  );
}

interface SettingsPageProps {
  accentPresetId: string;
  onAccentChange: (id: string) => void;
}

export default function SettingsPage({ accentPresetId, onAccentChange }: SettingsPageProps) {
  const { theme, setTheme } = useTheme();
  const [data, setData] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [allOrganisms, setAllOrganisms] = useState<Organism[]>([]);
  const [targetOrganisms, setTargetOrganisms] = useState<OrganismSelectionItem[]>([]);
  const [favOrganisms, setFavOrganisms] = useState<OrganismFavouriteItem[]>([]);
  const [targetCombo, setTargetCombo] = useState("");
  const [favCombo, setFavCombo] = useState("");

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
        Loading...
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your profile, integrations, and preferences.
        </p>
      </div>

      {/* ── Appearance ── */}
      <section className="border rounded-lg p-5 space-y-5">
        <SectionHeader title="Appearance" description="Personalise the look and feel of the interface." />

        {/* Mode */}
        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-wider text-muted-foreground">Mode</Label>
          <div className="grid grid-cols-3 gap-2">
            {([
              { id: "light",  label: "Light",  Icon: Sun },
              { id: "system", label: "System", Icon: Monitor },
              { id: "dark",   label: "Dark",   Icon: Moon },
            ] as const).map(({ id, label, Icon }) => {
              const isActive = theme === id;
              return (
                <button
                  key={id}
                  onClick={() => setTheme(id)}
                  className={`flex items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring ${
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
        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-wider text-muted-foreground">Accent Colour</Label>
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
                    className="flex h-8 w-8 items-center justify-center rounded-full shadow-sm ring-1 ring-black/10 dark:ring-white/10"
                    style={{ backgroundColor: swatchColor(preset) }}
                  >
                    {isActive && <Check className="h-4 w-4 text-white drop-shadow" />}
                  </span>
                  <span className={`text-[11px] leading-none ${isActive ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                    {preset.name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Profile ── */}
      <section className="border rounded-lg p-5 space-y-4">
        <SectionHeader title="Profile" description="Your identity used in exports and Formblatt Z." />

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="s-name">Name</Label>
            <Input
              id="s-name"
              value={data.name || ""}
              onChange={(e) => setData({ ...data, name: e.target.value })}
              onBlur={(e) => updateField("name", e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="s-initials">Initials</Label>
            <Input
              id="s-initials"
              value={data.initials || ""}
              onChange={(e) => setData({ ...data, initials: e.target.value })}
              onBlur={(e) => updateField("initials", e.target.value)}
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="s-email">Email</Label>
          <Input
            id="s-email"
            type="email"
            value={data.email || ""}
            onChange={(e) => setData({ ...data, email: e.target.value })}
            onBlur={(e) => updateField("email", e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="s-institution">GMO Institute</Label>
          <Input
            id="s-institution"
            value={data.institution || ""}
            onChange={(e) => setData({ ...data, institution: e.target.value })}
            onBlur={(e) => updateField("institution", e.target.value)}
          />
        </div>
      </section>

      {/* ── Behaviour ── */}
      <section className="border rounded-lg p-5 space-y-4">
        <SectionHeader title="Behaviour" description="Control how GMOCU handles data." />

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Duplicate GMOs</p>
            <p className="text-xs text-muted-foreground">Create duplicate GMO entries when adding organisms to plasmids.</p>
          </div>
          <Toggle
            checked={!!data.duplicate_gmos}
            onChange={() => toggleField("duplicate_gmos", data.duplicate_gmos)}
          />
        </div>

        <Separator />

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Upload completed only</p>
            <p className="text-xs text-muted-foreground">Only upload plasmids with "Complete" status to servers.</p>
          </div>
          <Toggle
            checked={!!data.upload_completed}
            onChange={() => toggleField("upload_completed", data.upload_completed)}
          />
        </div>
      </section>

      {/* ── Integrations ── */}
      <section className="border rounded-lg p-5 space-y-4">
        <SectionHeader title="Integrations" description="Connect to external services." />

        {/* JBEI/ice */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">JBEI/ice</p>
            <p className="text-xs text-muted-foreground">Upload plasmid data to JBEI/ice registry.</p>
          </div>
          <Toggle
            checked={!!data.use_ice}
            onChange={() => toggleField("use_ice", data.use_ice)}
          />
        </div>

        <Separator />

        {/* Filebrowser */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Filebrowser</p>
            <p className="text-xs text-muted-foreground">Upload files to Filebrowser server.</p>
          </div>
          <Toggle
            checked={!!data.use_file_browser}
            onChange={() => toggleField("use_file_browser", data.use_file_browser)}
          />
        </div>

        {(!!data.use_ice || !!data.use_file_browser) && (
          <div className="pl-4 border-l-2 border-muted space-y-2">
            <ComingSoon label="Server credentials management" />
          </div>
        )}

        <Separator />

        {/* Google Drive */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Google Drive Folder</p>
            <p className="text-xs text-muted-foreground">Upload plasmid files to Google Drive.</p>
          </div>
          <Toggle
            checked={!!data.use_gdrive}
            onChange={() => toggleField("use_gdrive", data.use_gdrive)}
          />
        </div>

        {!!data.use_gdrive && (
          <div className="pl-4 border-l-2 border-muted space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="s-gdrive-id">GDrive Folder ID</Label>
              <Input
                id="s-gdrive-id"
                placeholder="ID from link"
                value={data.drive_folder_id || ""}
                onChange={(e) => setData({ ...data, drive_folder_id: e.target.value })}
                onBlur={(e) => updateField("drive_folder_id", e.target.value)}
              />
            </div>
          </div>
        )}

        <Separator />

        {/* Zip files */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Zip files</p>
            <p className="text-xs text-muted-foreground">Compress files before uploading (faster).</p>
          </div>
          <Toggle
            checked={!!data.zip_files}
            onChange={() => toggleField("zip_files", data.zip_files)}
          />
        </div>

        <Separator />

        {/* Google Sheets sync */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Autosync Google Sheets</p>
            <p className="text-xs text-muted-foreground">Automatically sync glossary with Google Sheets.</p>
          </div>
          <Toggle
            checked={!!data.autosync}
            onChange={() => toggleField("autosync", data.autosync)}
          />
        </div>

        {!!data.autosync && (
          <div className="pl-4 border-l-2 border-muted space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="s-gsheet-id">GDrive Sheet ID</Label>
              <Input
                id="s-gsheet-id"
                placeholder="Google Sheets ID"
                value={data.glossary_sheet_id || ""}
                onChange={(e) => setData({ ...data, glossary_sheet_id: e.target.value })}
                onBlur={(e) => updateField("glossary_sheet_id", e.target.value)}
              />
            </div>
          </div>
        )}
      </section>

      {/* ── Coming soon ── */}
      <section className="border rounded-lg p-5 space-y-3 border-dashed">
        <SectionHeader title="Coming Soon" description="Features being ported from the legacy app." />
        <ComingSoon label="Upload to JBEI/ice, Filebrowser, and GDrive" />
        <ComingSoon label="Generate Formblatt Z" />
        <ComingSoon label="Generate plasmid list" />
        <ComingSoon label="Google Sheets glossary sync" />
        <ComingSoon label="Excel import/export for features and organisms" />
        <ComingSoon label="Import data from another GMOCU database" />
      </section>

      {/* ── Target Organisms ── */}
      <section className="border rounded-lg p-5 space-y-4">
        <SectionHeader
          title="Target Organisms"
          description="Organisms available as GMO targets when adding organisms to plasmids."
        />

        <div className="flex gap-2">
          <Select value={targetCombo} onValueChange={(v) => { if (v) setTargetCombo(v); }}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Select organism..." />
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
            <p className="text-sm text-muted-foreground py-2">No target organisms configured.</p>
          )}
        </div>
      </section>

      {/* ── Favourite Organisms ── */}
      <section className="border rounded-lg p-5 space-y-4">
        <SectionHeader
          title="Favourite Organisms"
          description="Quick-access subset of target organisms. All listed organisms must also exist in Target Organisms."
        />

        <div className="flex gap-2">
          <Select value={favCombo} onValueChange={(v) => { if (v) setFavCombo(v); }}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Select from targets..." />
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
            <p className="text-sm text-muted-foreground py-2">No favourite organisms configured.</p>
          )}
        </div>
      </section>

      {/* Bottom spacer */}
      <div className="h-8" />
    </div>
  );
}
