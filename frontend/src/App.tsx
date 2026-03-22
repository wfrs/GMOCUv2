import { useEffect, useRef, useState } from "react";
import { Dna, FlaskConical, Bug, Settings as SettingsIcon, Upload, Search, Sun, Moon, Monitor, History, ScrollText } from "lucide-react";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import { useTheme } from "@/components/theme-context";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { database, plasmids, features, organisms, settings as settingsApi } from "@/api/client";
import { applyAllAppearance } from "@/lib/appearance";
import type {
  DatabaseImportJob,
  PlasmidListItem,
  Feature,
  Organism,
  DatabaseImportReport,
  DatabaseImportResult,
} from "@/api/client";
import { useAccentColor } from "@/hooks/use-accent-color";
import { CommandPalette } from "@/components/command-palette";
import { DatabaseImportDialog } from "@/components/database-import-dialog";
import PlasmidsPage from "./pages/PlasmidsPage";
import FeaturesPage from "./pages/FeaturesPage";
import OrganismsPage from "./pages/OrganismsPage";
import SettingsPage from "./pages/SettingsPage";
import ActivityPage from "./pages/ActivityPage";
import FormblattPage from "./pages/FormblattPage";

const navItems = [
  { id: "plasmids", label: "Plasmids", icon: Dna },
  { id: "features", label: "Features", icon: FlaskConical },
  { id: "organisms", label: "Organisms", icon: Bug },
  { id: "activity", label: "Activity", icon: History },
  { id: "formblatt", label: "Reports", icon: ScrollText },
  { id: "settings", label: "Settings", icon: SettingsIcon },
] as const;

type PageId = (typeof navItems)[number]["id"];
type ImportDialogMode = "review" | "importing" | "complete" | "error";

function SidebarThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="px-3 py-3 border-t border-sidebar-border">
      <div className="flex items-center gap-1 p-1 bg-sidebar-foreground/8 rounded-lg">
        {([["light", Sun], ["system", Monitor], ["dark", Moon]] as const).map(([mode, Icon]) => (
          <button
            key={mode}
            onClick={() => setTheme(mode)}
            className={`flex-1 flex items-center justify-center h-7 rounded-md transition-colors ${
              theme === mode
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/50 hover:text-sidebar-foreground"
            }`}
            title={mode.charAt(0).toUpperCase() + mode.slice(1)}
          >
            <Icon className="h-3.5 w-3.5" />
          </button>
        ))}
      </div>
    </div>
  );
}

const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad|iPod/.test(navigator.platform);
const kbdHint = isMac ? "⌘K" : "Ctrl+K";

export default function App() {
  const [activePage, setActivePage] = useState<PageId>("plasmids");
  const [refreshKey, setRefreshKey] = useState(0);
  const [appVersion, setAppVersion] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { presetId, setPresetId } = useAccentColor();
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importDialogMode, setImportDialogMode] = useState<ImportDialogMode>("review");
  const [pendingImportFile, setPendingImportFile] = useState<File | null>(null);
  const [importReport, setImportReport] = useState<DatabaseImportReport | null>(null);
  const [importJob, setImportJob] = useState<DatabaseImportJob | null>(null);
  const [importResult, setImportResult] = useState<DatabaseImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // Command palette data
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteData, setPaletteData] = useState<{
    plasmids: PlasmidListItem[];
    features: Feature[];
    organisms: Organism[];
  }>({ plasmids: [], features: [], organisms: [] });
  const [pendingOpenId, setPendingOpenId] = useState<{ page: PageId; id: number } | null>(null);

  const loadPaletteData = () => {
    Promise.all([plasmids.list(), features.list(), organisms.list()]).then(
      ([p, f, o]) => setPaletteData({ plasmids: p, features: f, organisms: o })
    );
  };

  useEffect(() => { loadPaletteData(); }, [refreshKey]);

  useEffect(() => {
    database
      .health()
      .then((health) => setAppVersion(health.version))
      .catch(() => setAppVersion(null));
  }, []);

  useEffect(() => {
    document.title = appVersion ? `GMOCU v${appVersion}` : "GMOCU";
  }, [appVersion]);

  // Apply all appearance settings from DB on startup
  useEffect(() => {
    settingsApi.get().then(applyAllAppearance).catch(() => {});
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handlePaletteSelect = (type: "plasmid" | "feature" | "organism", id: number) => {
    const pageMap = { plasmid: "plasmids", feature: "features", organism: "organisms" } as const;
    const page = pageMap[type];
    setActivePage(page);
    setPendingOpenId({ page, id });
  };

  const handleDatabaseUpload = async (file: File) => {
    setImportError(null);
    setImportResult(null);
    setImportReport(null);
    setImportJob(null);
    setImportDialogMode("review");
    try {
      const report = await database.inspect(file);
      setPendingImportFile(file);
      setImportReport(report);
      setImportDialogOpen(true);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to inspect database");
    }
  };

  const confirmDatabaseImport = async () => {
    if (!pendingImportFile || !importReport) return;

    setImportDialogMode("importing");
    setImportError(null);

    try {
      let job = await database.startImportJob(pendingImportFile);
      setImportJob(job);

      while (job.status === "queued" || job.status === "running") {
        await new Promise((resolve) => window.setTimeout(resolve, 500));
        job = await database.getImportJob(job.job_id);
        setImportJob(job);
      }

      if (job.status === "failed") {
        throw new Error(job.error || "Failed to import database");
      }

      setImportResult(job.result);
      setImportDialogMode("complete");
      toast.success("Database imported successfully");
      setRefreshKey((k) => k + 1); // force re-render all pages
    } catch (e: unknown) {
      setImportDialogMode("error");
      setImportError(e instanceof Error ? e.message : "Failed to import database");
      toast.error(e instanceof Error ? e.message : "Failed to import database");
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleDatabaseUpload(file);
    e.target.value = ""; // reset so same file can be re-selected
  };

  const onImportDialogOpenChange = (open: boolean) => {
    setImportDialogOpen(open);
    if (!open && importDialogMode !== "importing") {
      setPendingImportFile(null);
      setImportReport(null);
      setImportJob(null);
      setImportResult(null);
      setImportError(null);
      setImportDialogMode("review");
    }
  };

  return (
    <ThemeProvider defaultTheme="system">
      <TooltipProvider>
        <div className="flex h-screen">
          {/* Sidebar */}
          <aside className="w-56 border-r border-border bg-sidebar flex flex-col">
            {/* Logo */}
            <div className="px-4 py-4 flex items-center gap-2.5">
              <div className="flex items-center justify-center h-7 w-7 rounded-lg bg-sidebar-primary/20">
                <Dna className="h-4 w-4 text-sidebar-primary" />
              </div>
              <span className="text-base font-semibold tracking-tight text-sidebar-foreground">
                GMOCU
              </span>
              {appVersion && (
                <span className="text-[10px] font-medium text-sidebar-foreground/40 bg-sidebar-foreground/10 px-1.5 py-0.5 rounded-md">
                  v{appVersion}
                </span>
              )}
            </div>
            <Separator className="bg-sidebar-border" />

            {/* Navigation */}
            <nav className="flex-1 px-2 py-3 space-y-0.5">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activePage === item.id;
                return (
                  <Button
                    key={item.id}
                    variant="ghost"
                    className={`w-full justify-start gap-2.5 h-9 px-3 text-sm ${
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/60 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground"
                    }`}
                    onClick={() => setActivePage(item.id)}
                  >
                    <Icon className={`h-4 w-4 ${isActive ? "text-sidebar-primary" : ""}`} />
                    {item.label}
                  </Button>
                );
              })}

              <Separator className="my-2 bg-sidebar-border" />

              {/* Command palette trigger */}
              <button
                className="w-full flex items-center gap-2 px-3 h-9 text-sm text-sidebar-foreground/50 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground rounded-md transition-colors"
                onClick={() => setPaletteOpen(true)}
              >
                <Search className="h-4 w-4 shrink-0" />
                <span className="flex-1 text-left">Search…</span>
                <kbd className="text-[10px] bg-sidebar-foreground/10 px-1.5 py-0.5 rounded border border-sidebar-foreground/15 shrink-0">{kbdHint}</kbd>
              </button>

              <Separator className="my-2 bg-sidebar-border" />

              {/* Import database */}
              <Button
                variant="ghost"
                className="w-full justify-start gap-2.5 h-9 px-3 text-sm text-sidebar-foreground/50 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-4 w-4" />
                Import Database
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".db"
                className="hidden"
                onChange={onFileChange}
              />
            </nav>

            <SidebarThemeToggle />

          </aside>

          {/* Main content */}
          <main className="flex-1 overflow-auto bg-background">
            <div className="h-full p-6">
              {activePage === "plasmids" && <PlasmidsPage key={`p-${refreshKey}`} openId={pendingOpenId?.page === "plasmids" ? pendingOpenId.id : undefined} onOpenIdConsumed={() => setPendingOpenId(null)} />}
              {activePage === "features" && <FeaturesPage key={`f-${refreshKey}`} openId={pendingOpenId?.page === "features" ? pendingOpenId.id : undefined} onOpenIdConsumed={() => setPendingOpenId(null)} />}
              {activePage === "organisms" && <OrganismsPage key={`o-${refreshKey}`} openId={pendingOpenId?.page === "organisms" ? pendingOpenId.id : undefined} onOpenIdConsumed={() => setPendingOpenId(null)} />}
              {activePage === "activity" && <ActivityPage key={`act-${refreshKey}`} onNavigate={handlePaletteSelect} />}
              {activePage === "formblatt" && <FormblattPage key={`fb-${refreshKey}`} />}
              {activePage === "settings" && <SettingsPage key={`s-${refreshKey}`} accentPresetId={presetId} onAccentChange={setPresetId} />}
            </div>
          </main>
        </div>

        <CommandPalette
          open={paletteOpen}
          onOpenChange={setPaletteOpen}
          plasmids={paletteData.plasmids}
          features={paletteData.features}
          organisms={paletteData.organisms}
          onSelect={handlePaletteSelect}
        />

        <DatabaseImportDialog
          open={importDialogOpen}
          mode={importDialogMode}
          report={importReport}
          job={importJob}
          result={importResult}
          error={importError}
          onOpenChange={onImportDialogOpenChange}
          onConfirm={confirmDatabaseImport}
        />

        <Toaster richColors position="bottom-right" />
      </TooltipProvider>
    </ThemeProvider>
  );
}
