import { AlertCircle, CheckCircle2, Database, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogClose,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { DatabaseImportJob, DatabaseImportReport, DatabaseImportResult } from "@/api/client";

type DatabaseImportDialogMode = "review" | "importing" | "complete" | "error";

interface DatabaseImportDialogProps {
  open: boolean;
  mode: DatabaseImportDialogMode;
  report: DatabaseImportReport | null;
  job: DatabaseImportJob | null;
  result: DatabaseImportResult | null;
  error: string | null;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}

function formatBytes(bytes: number | null) {
  if (bytes == null) return "Unknown size";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function inspectionLabel(report: DatabaseImportReport) {
  const inspection = report.inspection;
  if (inspection.kind === "legacy") {
    return `Legacy DB ${inspection.legacy_version ?? "unknown"}`;
  }
  if (inspection.kind === "current") {
    return `Current v2 schema ${inspection.schema_version ?? "unknown"}`;
  }
  return inspection.kind;
}

function countItems(report: DatabaseImportReport) {
  return [
    ["Plasmids", report.counts.plasmids],
    ["Features", report.counts.features],
    ["Organisms", report.counts.organisms],
    ["GMOs", report.counts.gmos],
    ["Cassettes", report.counts.cassettes],
    ["Attachments", report.counts.attachments],
  ] as const;
}

export function DatabaseImportDialog({
  open,
  mode,
  report,
  job,
  result,
  error,
  onOpenChange,
  onConfirm,
}: DatabaseImportDialogProps) {
  const visibleReport = result?.import_report ?? job?.report ?? report;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-2xl">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Database Import
          </AlertDialogTitle>
          <AlertDialogDescription>
            {mode === "review" && "Review the uploaded database before replacing the active v2 database."}
            {mode === "importing" && "The import is running. The app will switch to the imported database when this finishes."}
            {mode === "complete" && "The imported database is active now."}
            {mode === "error" && "The import did not complete."}
          </AlertDialogDescription>
        </AlertDialogHeader>

        {visibleReport && (
          <div className="space-y-5">
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="rounded-lg border p-3">
                <div className="text-xs uppercase tracking-wider text-muted-foreground">File</div>
                <div className="mt-1 font-medium break-all">{visibleReport.filename}</div>
                <div className="text-xs text-muted-foreground mt-1">{formatBytes(visibleReport.file_size_bytes)}</div>
              </div>
              <div className="rounded-lg border p-3">
                <div className="text-xs uppercase tracking-wider text-muted-foreground">Detected</div>
                <div className="mt-1 font-medium">{inspectionLabel(visibleReport)}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Target schema v{visibleReport.inspection.target_schema_version}
                </div>
              </div>
              <div className="rounded-lg border p-3">
                <div className="text-xs uppercase tracking-wider text-muted-foreground">Destination</div>
                <div className="mt-1 font-medium break-all">{visibleReport.destination_path}</div>
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-3">Imported Content</div>
              <div className="grid grid-cols-3 gap-3 text-sm">
                {countItems(visibleReport).map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between rounded-md bg-muted px-3 py-2">
                    <span>{label}</span>
                    <Badge variant="outline">{value}</Badge>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border p-4">
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-3">Import Steps</div>
              <div className="space-y-2">
                {(job?.steps ?? visibleReport.planned_steps).map((step) => {
                  const stepStatus = "status" in step ? step.status : "pending";
                  return (
                    <div key={step.id} className="flex items-start gap-3 rounded-md px-3 py-2 bg-muted/60">
                      <div className="mt-0.5">
                        {stepStatus === "completed" || mode === "complete" ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        ) : stepStatus === "running" || (mode === "importing" && job == null && step.id === visibleReport.planned_steps[0]?.id) ? (
                          <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        ) : stepStatus === "failed" ? (
                          <AlertCircle className="h-4 w-4 text-destructive" />
                        ) : (
                          <div className="h-4 w-4 rounded-full border border-border" />
                        )}
                      </div>
                      <div>
                        <div className="text-sm font-medium">{step.label}</div>
                        <div className="text-xs text-muted-foreground">{step.detail}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {result?.backup_path && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                Backup created at <span className="font-mono">{result.backup_path}</span>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <AlertDialogFooter>
          <AlertDialogClose render={<Button variant="outline" size="sm" disabled={mode === "importing"} />}>
            {mode === "complete" ? "Close" : "Cancel"}
          </AlertDialogClose>
          {mode === "review" && (
            <Button size="sm" onClick={onConfirm}>
              Import Database
            </Button>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
