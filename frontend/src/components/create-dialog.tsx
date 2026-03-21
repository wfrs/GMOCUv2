import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogFooter,
  AlertDialogClose,
} from "@/components/ui/alert-dialog";

export interface FieldConfig {
  key: string;
  label: string;
  placeholder?: string;
  required?: boolean;
}

interface CreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  fields: FieldConfig[];
  onSubmit: (values: Record<string, string>) => Promise<void>;
  /** Existing names to warn on duplicate */
  existingNames?: string[];
  /** Which field key to check for duplicates */
  duplicateField?: string;
}

export function CreateDialog({
  open,
  onOpenChange,
  title,
  fields,
  onSubmit,
  existingNames = [],
  duplicateField,
}: CreateDialogProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const firstRef = useRef<HTMLInputElement>(null);

  // Reset on open
  useEffect(() => {
    if (open) {
      setValues({});
      setTimeout(() => firstRef.current?.focus(), 50);
    }
  }, [open]);

  const duplicateValue = duplicateField ? values[duplicateField] : undefined;
  const isDuplicate =
    !!duplicateValue &&
    existingNames.some((n) => n.toLowerCase() === duplicateValue.toLowerCase());

  const canSubmit =
    !submitting &&
    fields.filter((f) => f.required !== false).every((f) => (values[f.key] || "").trim());

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await onSubmit(values);
      onOpenChange(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
        </AlertDialogHeader>

        <form
          className="space-y-3 py-1"
          onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
        >
          {fields.map((field, i) => {
            const showDupWarning = field.key === duplicateField && isDuplicate;
            return (
              <div key={field.key} className="space-y-1.5">
                <Label htmlFor={`cd-${field.key}`}>{field.label}</Label>
                <Input
                  id={`cd-${field.key}`}
                  ref={i === 0 ? firstRef : undefined}
                  placeholder={field.placeholder}
                  value={values[field.key] || ""}
                  onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
                />
                {showDupWarning && (
                  <p className="text-xs text-amber-600 dark:text-amber-400">
                    A record with this name already exists.
                  </p>
                )}
              </div>
            );
          })}
        </form>

        <AlertDialogFooter>
          <AlertDialogClose render={<Button variant="outline" size="sm" />}>
            Cancel
          </AlertDialogClose>
          <Button size="sm" disabled={!canSubmit} onClick={handleSubmit}>
            {submitting ? "Creating…" : "Create"}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
