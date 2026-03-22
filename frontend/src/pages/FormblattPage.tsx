import { useState } from "react";
import {
  Download, RefreshCw, ShieldCheck, ChevronDown, ChevronRight,
  Loader2, CheckCircle2, AlertTriangle, XCircle, Info, List,
} from "lucide-react";
import {
  reports,
  type FormblattRow,
  type FormblattLang,
  type HealthReport,
  FORMBLATT_COLUMNS_DE,
  FORMBLATT_COLUMNS_EN,
} from "@/api/client";
import { Button } from "@/components/ui/button";
import { useEffect } from "react";

const LANG_LABELS: Record<FormblattLang, string> = { de: "DE", en: "EN" };
const COL_WIDTHS = [40, 160, 72, 130, 60, 100, 200, 180, 120, 44, 72, 110, 100, 80];

// ── Health helpers ────────────────────────────────────────────────────────────

type Severity = "ok" | "warning" | "error";

function featuresSeverity(f: HealthReport["features"]): Severity {
  if (f.missing.length > 0 || f.duplicates.length > 0 || f.has_empty_fields) return "error";
  if (f.redundant.length > 0) return "warning";
  return "ok";
}

function organismsSeverity(o: HealthReport["organisms"]): Severity {
  if (o.missing_pairs.length > 0 || o.duplicates.length > 0) return "error";
  if (o.redundant.length > 0) return "warning";
  return "ok";
}

function plasmidsSeverity(p: HealthReport["plasmids"]): Severity {
  if (p.duplicates.length > 0) return "error";
  if (p.no_backbone.length > 0 || p.no_cassettes.length > 0) return "warning";
  return "ok";
}

const SEVERITY_ICON: Record<Severity, React.ReactNode> = {
  ok:      <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />,
  warning: <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />,
  error:   <XCircle className="h-4 w-4 text-destructive shrink-0" />,
};

const SEVERITY_BADGE: Record<Severity, string> = {
  ok:      "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-700/40",
  warning: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200/60 dark:border-amber-700/40",
  error:   "bg-destructive/10 text-destructive border-destructive/20",
};

const SEVERITY_LABEL: Record<Severity, string> = {
  ok: "All clear", warning: "Warnings", error: "Issues",
};

function IssueGroup({ label, items, severity = "error" }: {
  label: string;
  items: string[];
  severity?: "error" | "warning" | "info";
}) {
  const [open, setOpen] = useState(false);
  if (items.length === 0) return null;
  const iconClass = severity === "error"
    ? "text-destructive" : severity === "warning"
    ? "text-amber-500" : "text-blue-500";
  return (
    <div className="text-xs">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors w-full text-left py-0.5"
      >
        {open ? <ChevronDown className={`h-3 w-3 shrink-0 ${iconClass}`} />
               : <ChevronRight className={`h-3 w-3 shrink-0 ${iconClass}`} />}
        <span className="font-medium">{label}</span>
        <span className="ml-auto font-mono text-[10px] px-1.5 py-0.5 rounded bg-muted border border-border">
          {items.length}
        </span>
      </button>
      {open && (
        <ul className="mt-1 ml-4 space-y-0.5">
          {items.map((item, i) => (
            <li key={i} className="text-muted-foreground font-mono truncate">{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function HealthCard({
  title, severity, children,
}: { title: string; severity: Severity; children: React.ReactNode }) {
  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center gap-2">
        {SEVERITY_ICON[severity]}
        <span className="text-sm font-medium">{title}</span>
        <span className={`ml-auto text-[10px] font-medium px-2 py-0.5 rounded-full border ${SEVERITY_BADGE[severity]}`}>
          {SEVERITY_LABEL[severity]}
        </span>
      </div>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function FormblattPage() {
  // Formblatt Z state
  const [lang, setLang] = useState<FormblattLang>("de");
  const [rows, setRows] = useState<FormblattRow[]>([]);
  const [fbLoading, setFbLoading] = useState(true);

  // Health state
  const [healthOpen, setHealthOpen] = useState(false);
  const [checking, setChecking] = useState(false);
  const [health, setHealth] = useState<HealthReport | null>(null);

  const columns = lang === "de"
    ? (FORMBLATT_COLUMNS_DE as readonly string[])
    : (FORMBLATT_COLUMNS_EN as readonly string[]);

  const loadRows = (l: FormblattLang) => {
    setFbLoading(true);
    reports.rows(l).then(setRows).finally(() => setFbLoading(false));
  };

  useEffect(() => { loadRows(lang); }, [lang]);

  const runChecks = async () => {
    setChecking(true);
    setHealthOpen(true);
    try {
      const result = await reports.health();
      setHealth(result);
    } finally {
      setChecking(false);
    }
  };

  // Derived health severities
  const fSev = health ? featuresSeverity(health.features) : null;
  const oSev = health ? organismsSeverity(health.organisms) : null;
  const pSev = health ? plasmidsSeverity(health.plasmids) : null;
  const overallSev: Severity | null = fSev && oSev && pSev
    ? ([fSev, oSev, pSev].includes("error") ? "error"
      : [fSev, oSev, pSev].includes("warning") ? "warning" : "ok")
    : null;

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground mt-1">GMO documentation exports and data quality</p>
      </div>

      {/* ── Data Health ── */}
      <div className="border rounded-lg overflow-hidden">
        {/* Header bar */}
        <div className="flex items-center gap-3 px-4 py-3 bg-muted/30">
          <ShieldCheck className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="text-sm font-medium">Data Health</span>
          {overallSev && (
            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${SEVERITY_BADGE[overallSev]}`}>
              {SEVERITY_LABEL[overallSev]}
            </span>
          )}
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="outline" size="sm" className="gap-1.5 h-7 text-xs"
              onClick={runChecks} disabled={checking}
            >
              {checking
                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                : <ShieldCheck className="h-3.5 w-3.5" />}
              Run checks
            </Button>
            <button
              onClick={() => setHealthOpen((v) => !v)}
              className="flex items-center justify-center h-7 w-7 rounded-md hover:bg-muted transition-colors text-muted-foreground"
            >
              <ChevronDown className={`h-4 w-4 transition-transform ${healthOpen ? "" : "-rotate-90"}`} />
            </button>
          </div>
        </div>

        {/* Body */}
        {healthOpen && (
          <div className="border-t border-border">
            {!health && !checking && (
              <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
                <Info className="h-4 w-4" />
                Click "Run checks" to validate your data before exporting.
              </div>
            )}
            {checking && (
              <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Running checks…
              </div>
            )}
            {health && !checking && (
              <div className="grid grid-cols-3 divide-x divide-border">
                {/* Features */}
                <HealthCard title="Features" severity={fSev!}>
                  <IssueGroup label="Missing from glossary" items={health.features.missing} severity="error" />
                  <IssueGroup label="Duplicate entries" items={health.features.duplicates} severity="error" />
                  {health.features.has_empty_fields && (
                    <p className="text-xs text-destructive flex items-center gap-1.5">
                      <XCircle className="h-3 w-3 shrink-0" /> Glossary has empty fields
                    </p>
                  )}
                  <IssueGroup label="Redundant / unused" items={health.features.redundant} severity="warning" />
                  {fSev === "ok" && (
                    <p className="text-xs text-muted-foreground">All {health.features.redundant.length === 0 ? "features" : "required features"} are resolved.</p>
                  )}
                </HealthCard>

                {/* Organisms */}
                <HealthCard title="Organisms" severity={oSev!}>
                  <IssueGroup label="Missing from glossary" items={health.organisms.missing_pairs} severity="error" />
                  <IssueGroup label="Duplicate entries" items={health.organisms.duplicates} severity="error" />
                  <IssueGroup label="Redundant / unused" items={health.organisms.redundant} severity="warning" />
                  {oSev === "ok" && (
                    <p className="text-xs text-muted-foreground">All organisms are resolved.</p>
                  )}
                </HealthCard>

                {/* Plasmids */}
                <HealthCard title="Plasmids" severity={pSev!}>
                  <IssueGroup label="Duplicate names" items={health.plasmids.duplicates} severity="error" />
                  <IssueGroup label="No backbone vector" items={health.plasmids.no_backbone} severity="warning" />
                  <IssueGroup label="No cassettes defined" items={health.plasmids.no_cassettes} severity="warning" />
                  <IssueGroup label="No GMOs registered" items={health.plasmids.no_gmos} severity="info" />
                  {pSev === "ok" && health.plasmids.no_gmos.length === 0 && (
                    <p className="text-xs text-muted-foreground">All plasmids are complete.</p>
                  )}
                </HealthCard>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Plasmid List ── */}
      <div className="border rounded-lg px-4 py-3 flex items-center gap-4">
        <List className="h-4 w-4 text-muted-foreground shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium">Plasmid List</p>
          <p className="text-xs text-muted-foreground mt-0.5">Formatted Excel export of all plasmids</p>
        </div>
        <Button
          variant="outline" size="sm" className="gap-1.5 shrink-0"
          onClick={() => window.open(reports.plasmidListUrl(), "_blank")}
        >
          <Download className="h-3.5 w-3.5" />
          Export Excel
        </Button>
      </div>

      {/* ── Formblatt Z ── */}
      <div className="flex flex-col flex-1 min-h-0">
        {/* Section header */}
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-sm font-medium">Formblatt Z</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {fbLoading ? "Loading…" : `${rows.length} GMO row${rows.length !== 1 ? "s" : ""}`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Language toggle */}
            <div className="flex items-center gap-1 p-1 bg-muted rounded-lg border border-border">
              {(["de", "en"] as FormblattLang[]).map((l) => (
                <button
                  key={l}
                  onClick={() => { if (l !== lang) setLang(l); }}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    lang === l
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {LANG_LABELS[l]}
                </button>
              ))}
            </div>
            <Button variant="outline" size="sm" className="gap-1.5" onClick={() => loadRows(lang)}>
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </Button>
            <Button size="sm" className="gap-1.5" onClick={() => window.open(reports.downloadUrl(lang), "_blank")}>
              <Download className="h-3.5 w-3.5" />
              Export Excel
            </Button>
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto border rounded-lg">
          {fbLoading ? (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">Loading…</div>
          ) : rows.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
              No GMO entries found. Add GMOs to plasmids to generate this report.
            </div>
          ) : (
            <table
              className="w-full text-sm border-collapse"
              style={{ tableLayout: "fixed", minWidth: COL_WIDTHS.reduce((a, b) => a + b, 0) }}
            >
              <colgroup>
                {COL_WIDTHS.map((w, i) => <col key={i} style={{ width: w }} />)}
              </colgroup>
              <thead className="sticky top-0 z-10">
                <tr className="bg-muted/80 backdrop-blur border-b border-border">
                  {columns.map((col, i) => (
                    <th
                      key={col}
                      className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground"
                      style={{ width: COL_WIDTHS[i] }}
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                    {columns.map((col, j) => (
                      <td
                        key={col}
                        className="px-3 py-2 align-top"
                        style={{ width: COL_WIDTHS[j] }}
                      >
                        <div className="break-words text-sm">
                          {row[col] != null ? String(row[col]) : "—"}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
