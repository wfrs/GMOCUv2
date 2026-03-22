import { useEffect, useRef, useState } from "react";
import { parseDate as parseCalendarDate } from "@internationalized/date";
import { CalendarDays } from "lucide-react";
import type { DateValue } from "react-aria-components";
import { Calendar } from "@/components/application/date-picker/calendar";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatDate, parseDate, getCurrentDateFormat } from "@/lib/appearance";

interface DateInputProps {
  id?: string;
  value: string; // ISO YYYY-MM-DD or empty string
  onChange?: (e: { target: { value: string } }) => void;
  onBlur?: (e: { target: { value: string } }) => void;
  className?: string;
  disabled?: boolean;
}

function toISO(dv: DateValue | null): string {
  if (!dv) return "";
  return `${dv.year}-${String(dv.month).padStart(2, "0")}-${String(dv.day).padStart(2, "0")}`;
}

function toCalendarDate(iso: string): DateValue | null {
  if (!iso) return null;
  try { return parseCalendarDate(iso); } catch { return null; }
}

export function DateInput({ id, value, onChange, onBlur, className, disabled }: DateInputProps) {
  // typedText tracks what the user is typing; null means "not editing"
  const [typedText, setTypedText] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pending, setPending] = useState<DateValue | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const isEditing = typedText !== null;
  const displayValue = isEditing ? typedText : (value ? formatDate(value) : "");

  // Close picker on outside click
  useEffect(() => {
    if (!pickerOpen) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [pickerOpen]);

  const emit = (iso: string) => {
    onChange?.({ target: { value: iso } });
    onBlur?.({ target: { value: iso } });
  };

  const handleTextBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    if (containerRef.current?.contains(e.relatedTarget as Node)) return;
    const iso = parseDate(typedText ?? "") ?? "";
    setTypedText(null);
    emit(iso);
  };

  const openPicker = () => {
    setPending(toCalendarDate(value));
    setPickerOpen(true);
  };

  const handleApply = () => {
    const iso = toISO(pending);
    setTypedText(null);
    emit(iso);
    setPickerOpen(false);
  };

  const placeholder = getCurrentDateFormat() === "eu" ? "DD.MM.YYYY" : "YYYY-MM-DD";

  return (
    <div ref={containerRef} className={cn("relative flex items-center w-44", className)}>
      <Input
        id={id}
        type="text"
        value={displayValue}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(e) => setTypedText(e.target.value)}
        onFocus={() => { if (!isEditing) setTypedText(value ? formatDate(value) : ""); }}
        onBlur={handleTextBlur}
        className="pr-8"
      />
      {/* Calendar icon trigger */}
      <button
        type="button"
        disabled={disabled}
        onClick={openPicker}
        className="absolute right-2 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors disabled:pointer-events-none"
        tabIndex={-1}
      >
        <CalendarDays className="h-3.5 w-3.5" />
      </button>

      {/* Calendar popup */}
      {pickerOpen && (
        <div className="absolute top-full left-0 z-50 mt-1 rounded-2xl bg-popover shadow-xl ring-1 ring-border overflow-hidden min-w-max">
          {/* .uitl-calendar scoped to the calendar body only so the
              app's green primary is preserved in the footer buttons */}
          <div className="uitl-calendar px-6 py-5">
            <Calendar value={pending} onChange={setPending} />
          </div>
          <div className="grid grid-cols-2 gap-3 border-t border-border p-4">
            <Button variant="outline" size="sm" onClick={() => setPickerOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleApply}>
              Apply
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
