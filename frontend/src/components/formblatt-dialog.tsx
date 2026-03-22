import { useEffect, useState } from "react";
import { Download, AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { reports, type FormblattValidation } from "@/api/client";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogClose,
} from "@/components/ui/alert-dialog";

interface FormblattDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function FormblattDialog({ open, onOpenChange }: FormblattDialogProps) {
  const [validation, setValidation] = useState<FormblattValidation | null>(null);

  // Derive loading from validation being absent while dialog is open
  const loading = open && validation === null;

  useEffect(() => {
    if (!open) return;
    reports.validateFormblatt().then(setValidation);
    return () => setValidation(null);
  }, [open]);

  const handleDownload = (lang: "de" | "en") => {
    window.open(reports.downloadUrl(lang), "_blank");
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-lg">
        <AlertDialogHeader>
          <AlertDialogTitle>Generate Formblatt Z</AlertDialogTitle>
        </AlertDialogHeader>

        <div className="space-y-4 py-1">
          {loading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Checking data…
            </div>
          )}

          {validation && (
            <>
              {/* GMO count */}
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">GMO rows in report:</span>
                <span className="font-semibold tabular-nums">{validation.gmo_count}</span>
              </div>

              {/* Status */}
              {validation.ready ? (
                <div className="flex items-center gap-2 rounded-lg border border-emerald-200/60 bg-emerald-500/8 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-700/40 dark:text-emerald-400">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  All features and organisms are defined. Ready to export.
                </div>
              ) : (
                <div className="rounded-lg border border-orange-200/60 bg-orange-500/8 px-3 py-2 text-sm dark:border-orange-700/40">
                  <div className="flex items-center gap-2 text-orange-700 dark:text-orange-400 mb-2">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span className="font-medium">Issues found — export may be incomplete</span>
                  </div>
                  <ul className="space-y-1 ml-6 list-disc text-orange-700/80 dark:text-orange-400/80">
                    {validation.issues.map((issue, i) => (
                      <li key={i}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Download buttons */}
              {validation.gmo_count > 0 && (
                <div className="flex gap-2 pt-1">
                  <Button className="flex-1 gap-2" onClick={() => handleDownload("de")}>
                    <Download className="h-4 w-4" />
                    Download DE
                  </Button>
                  <Button variant="outline" className="flex-1 gap-2" onClick={() => handleDownload("en")}>
                    <Download className="h-4 w-4" />
                    Download EN
                  </Button>
                </div>
              )}

              {validation.gmo_count === 0 && (
                <p className="text-sm text-muted-foreground">
                  No GMO entries found. Add GMOs to plasmids before generating this report.
                </p>
              )}
            </>
          )}
        </div>

        <AlertDialogFooter>
          <AlertDialogClose render={<Button variant="outline" size="sm" />}>
            Close
          </AlertDialogClose>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
