import { useEffect, useRef, useState } from "react";
import { Dna, FlaskConical, Bug, Settings as SettingsIcon, Search, Sun, Moon, Monitor, History, ScrollText, PanelLeft, PanelLeftClose, WifiOff, UserCog } from "lucide-react";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider, Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
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
] as const;

type PageId = (typeof navItems)[number]["id"] | "settings";
type ImportDialogMode = "review" | "importing" | "complete" | "error";

const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad|iPod/.test(navigator.platform);
const kbdHint = isMac ? "⌘K" : "Ctrl+K";

export default function App() {
  return (
    <ThemeProvider defaultTheme="system">
      <TooltipProvider>
        <AppInner />
        <Toaster richColors position="bottom-right" />
      </TooltipProvider>
    </ThemeProvider>
  );
}

function AppInner() {
  const [activePage, setActivePage] = useState<PageId>("plasmids");
  const [refreshKey, setRefreshKey] = useState(0);
  const [appVersion, setAppVersion] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [userName, setUserName] = useState<string | null>(null);
  const [backendDown, setBackendDown] = useState(false);
  const [profileIncomplete, setProfileIncomplete] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { presetId, setPresetId } = useAccentColor();
  const { theme, setTheme } = useTheme();
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
      .then((health) => { setAppVersion(health.version); setBackendDown(false); })
      .catch(() => { setAppVersion(null); setBackendDown(true); });
  }, []);

  useEffect(() => {
    document.title = appVersion ? `GMOCU v${appVersion}` : "GMOCU";
  }, [appVersion]);

  // Apply all appearance settings from DB on startup
  useEffect(() => {
    settingsApi.get().then((s) => {
      applyAllAppearance(s);
      if (s.name) setUserName(s.name);
      setProfileIncomplete(!s.name || !s.initials);
    }).catch(() => {});
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
    <>
      <div className="flex h-screen">
          {/* Sidebar */}
          <aside className={`${sidebarCollapsed ? "w-14" : "w-56"} transition-all duration-200 border-r border-border bg-sidebar flex flex-col overflow-hidden shrink-0`}>
            {/* Logo */}
            <div className={`py-4 flex items-center gap-2.5 justify-center ${sidebarCollapsed ? "px-3" : "px-4"}`}>
              <div className="flex items-center justify-center h-8 w-8 shrink-0 rounded-lg bg-sidebar-primary/16 ring-1 ring-sidebar-primary/20">
                <img src="/logo-mark.svg" alt="GMOCU logo" className="h-5 w-5" />
              </div>
              {!sidebarCollapsed && (
                <>
                  <span className="text-base font-semibold tracking-tight text-sidebar-foreground">GMOCU</span>
                  {appVersion && (
                    <span className="text-[10px] font-medium text-sidebar-foreground/40 bg-sidebar-foreground/10 px-1.5 py-0.5 rounded-full">
                      v{appVersion}
                    </span>
                  )}
                </>
              )}
            </div>
            <Separator className="bg-sidebar-border" />

            {/* Navigation */}
            <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-hidden">
              {/* Search */}
              {sidebarCollapsed ? (
                <div className="w-full flex justify-center">
                  <Tooltip>
                    <TooltipTrigger
                      className="h-9 w-9 flex items-center justify-center rounded-full text-sidebar-foreground/50 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground transition-colors"
                      onClick={() => setPaletteOpen(true)}
                    >
                      <Search className="h-5 w-5" />
                    </TooltipTrigger>
                    <TooltipContent side="right">Search</TooltipContent>
                  </Tooltip>
                </div>
              ) : (
                <button
                  className="w-full flex items-center gap-2 px-3 h-9 text-sm text-sidebar-foreground/50 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground rounded-md transition-colors"
                  onClick={() => setPaletteOpen(true)}
                >
                  <Search className="h-5 w-5 shrink-0" />
                  <span className="flex-1 text-left">Search…</span>
                  <kbd className="text-[10px] bg-sidebar-foreground/10 px-1.5 py-0.5 rounded-full border border-sidebar-foreground/15 shrink-0">{kbdHint}</kbd>
                </button>
              )}

              <Separator className="my-2 bg-sidebar-border" />

              {/* Nav items */}
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activePage === item.id;
                const activeClass = "bg-sidebar-accent text-sidebar-accent-foreground font-medium hover:bg-sidebar-accent hover:text-sidebar-accent-foreground";
                const inactiveClass = "text-sidebar-foreground/60 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground";
                if (sidebarCollapsed) {
                  return (
                    <div key={item.id} className="w-full flex justify-center">
                      <Tooltip>
                        <TooltipTrigger
                          className={`h-9 w-9 flex items-center justify-center rounded-full transition-colors ${isActive ? activeClass : inactiveClass}`}
                          onClick={() => setActivePage(item.id)}
                        >
                          <Icon className={`h-5 w-5 ${isActive ? "text-sidebar-primary" : ""}`} />
                        </TooltipTrigger>
                        <TooltipContent side="right">{item.label}</TooltipContent>
                      </Tooltip>
                    </div>
                  );
                }
                return (
                  <Button
                    key={item.id}
                    variant="ghost"
                    className={`w-full justify-start gap-2.5 h-9 px-3 text-sm ${isActive ? activeClass : inactiveClass}`}
                    onClick={() => setActivePage(item.id)}
                  >
                    <Icon className={`h-5 w-5 ${isActive ? "text-sidebar-primary" : ""}`} />
                    {item.label}
                  </Button>
                );
              })}
            </nav>

            <Separator className="bg-sidebar-border" />

            {/* Settings (pinned) */}
            <div className="px-2 py-1.5">
              {sidebarCollapsed ? (
                <div className="w-full flex justify-center">
                  <Tooltip>
                    <TooltipTrigger
                      className={`h-9 w-9 flex items-center justify-center rounded-full transition-colors ${activePage === "settings" ? "bg-sidebar-accent text-sidebar-accent-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" : "text-sidebar-foreground/60 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground"}`}
                      onClick={() => setActivePage("settings")}
                    >
                      <SettingsIcon className={`h-5 w-5 ${activePage === "settings" ? "text-sidebar-primary" : ""}`} />
                    </TooltipTrigger>
                    <TooltipContent side="right">Settings</TooltipContent>
                  </Tooltip>
                </div>
              ) : (
                <Button
                  variant="ghost"
                  className={`w-full justify-start gap-2.5 h-9 px-3 text-sm ${activePage === "settings" ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium hover:bg-sidebar-accent hover:text-sidebar-accent-foreground" : "text-sidebar-foreground/60 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground"}`}
                  onClick={() => setActivePage("settings")}
                >
                  <SettingsIcon className={`h-5 w-5 ${activePage === "settings" ? "text-sidebar-primary" : ""}`} />
                  Settings
                </Button>
              )}
            </div>

            {/* User + theme footer */}
            {sidebarCollapsed ? (
              <div className="px-2 py-3 border-t border-sidebar-border flex flex-col items-center gap-1.5">
                <Tooltip>
                  <TooltipTrigger className="h-7 w-7 rounded-full bg-sidebar-primary/20 flex items-center justify-center text-xs font-semibold text-sidebar-primary cursor-default select-none">
                    {userName ? userName[0].toUpperCase() : "?"}
                  </TooltipTrigger>
                  <TooltipContent side="right">{userName || "Set name in Settings"}</TooltipContent>
                </Tooltip>
                <DropdownMenu>
                  <DropdownMenuTrigger className="h-6 w-6 flex items-center justify-center rounded-full text-sidebar-foreground/50 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground transition-colors">
                    {theme === "light" ? <Sun className="h-3.5 w-3.5" /> : theme === "dark" ? <Moon className="h-3.5 w-3.5" /> : <Monitor className="h-3.5 w-3.5" />}
                  </DropdownMenuTrigger>
                  <DropdownMenuContent side="right" align="end">
                    <DropdownMenuItem onClick={() => setTheme("light")}><Sun className="h-4 w-4 mr-2" />Light</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTheme("system")}><Monitor className="h-4 w-4 mr-2" />System</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTheme("dark")}><Moon className="h-4 w-4 mr-2" />Dark</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <button
                  onClick={() => setSidebarCollapsed(false)}
                  className="h-6 w-6 flex items-center justify-center rounded-full text-sidebar-foreground/50 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground transition-colors"
                  title="Expand sidebar"
                >
                  <PanelLeft className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              <div className="px-3 py-3 border-t border-sidebar-border flex flex-col gap-2">
                {/* Row 1: avatar + name */}
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 shrink-0 rounded-full bg-sidebar-primary/20 flex items-center justify-center text-xs font-semibold text-sidebar-primary select-none">
                    {userName ? userName[0].toUpperCase() : "?"}
                  </div>
                  <span className="flex-1 text-sm text-sidebar-foreground truncate min-w-0">{userName || ""}</span>
                </div>
                {/* Row 2: theme toggle + collapse */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-0.5 p-0.5 bg-sidebar-foreground/8 rounded-full">
                    {(["light", "system", "dark"] as const).map((mode) => {
                      const Icon = mode === "light" ? Sun : mode === "system" ? Monitor : Moon;
                      return (
                        <button
                          key={mode}
                          onClick={() => setTheme(mode)}
                          title={mode.charAt(0).toUpperCase() + mode.slice(1)}
                          className={`h-6 w-6 flex items-center justify-center rounded-full transition-colors ${theme === mode ? "bg-sidebar-accent text-sidebar-accent-foreground" : "text-sidebar-foreground/50 hover:text-sidebar-foreground"}`}
                        >
                          <Icon className="h-3 w-3" />
                        </button>
                      );
                    })}
                  </div>
                  <button
                    onClick={() => setSidebarCollapsed(true)}
                    className="h-6 w-6 flex items-center justify-center rounded-full text-sidebar-foreground/50 hover:bg-sidebar-foreground/8 hover:text-sidebar-foreground transition-colors"
                    title="Collapse sidebar"
                  >
                    <PanelLeftClose className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept=".db"
              className="hidden"
              onChange={onFileChange}
            />
          </aside>

          {/* Main content */}
          <main className="flex-1 overflow-auto bg-background">
            {backendDown ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-6">
                <div className="flex items-center justify-center h-14 w-14 rounded-2xl bg-destructive/10 text-destructive">
                  <WifiOff className="h-7 w-7" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Cannot reach the server</h2>
                  <p className="text-sm text-muted-foreground mt-1 max-w-xs">
                    Make sure the GMOCU backend is running, then reload the page.
                  </p>
                </div>
                <button
                  onClick={() => window.location.reload()}
                  className="text-sm text-primary hover:underline"
                >
                  Reload
                </button>
              </div>
            ) : (
              <div className="h-full flex flex-col">
                {/* Profile nudge */}
                {profileIncomplete && activePage !== "settings" && (
                  <div className="flex items-center gap-3 px-6 py-2.5 bg-amber-500/8 border-b border-amber-500/20 text-sm">
                    <UserCog className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
                    <span className="text-amber-700 dark:text-amber-300 flex-1">
                      Your profile is incomplete — name and initials are required for Formblatt Z exports.
                    </span>
                    <button
                      className="text-amber-700 dark:text-amber-300 font-medium hover:underline shrink-0"
                      onClick={() => setActivePage("settings")}
                    >
                      Complete profile
                    </button>
                    <button
                      className="text-amber-600/60 hover:text-amber-700 dark:hover:text-amber-300 shrink-0"
                      onClick={() => setProfileIncomplete(false)}
                    >
                      ✕
                    </button>
                  </div>
                )}
                <div className="flex-1 overflow-auto p-6">
                  {activePage === "plasmids" && <PlasmidsPage key={`p-${refreshKey}`} openId={pendingOpenId?.page === "plasmids" ? pendingOpenId.id : undefined} onOpenIdConsumed={() => setPendingOpenId(null)} />}
                  {activePage === "features" && <FeaturesPage key={`f-${refreshKey}`} openId={pendingOpenId?.page === "features" ? pendingOpenId.id : undefined} onOpenIdConsumed={() => setPendingOpenId(null)} />}
                  {activePage === "organisms" && <OrganismsPage key={`o-${refreshKey}`} openId={pendingOpenId?.page === "organisms" ? pendingOpenId.id : undefined} onOpenIdConsumed={() => setPendingOpenId(null)} />}
                  {activePage === "activity" && <ActivityPage key={`act-${refreshKey}`} onNavigate={handlePaletteSelect} />}
                  {activePage === "formblatt" && <FormblattPage key={`fb-${refreshKey}`} />}
                  {activePage === "settings" && <SettingsPage key={`s-${refreshKey}`} accentPresetId={presetId} onAccentChange={setPresetId} onImportDatabase={() => fileInputRef.current?.click()} onUserNameChange={setUserName} onProfileChange={() => setProfileIncomplete(false)} />}
                </div>
              </div>
            )}
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
    </>
  );
}
