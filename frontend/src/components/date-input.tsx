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
  const [display, setDisplay] = useState(() => value ? formatDate(value) : "");
  const [editing, setEditing] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pending, setPending] = useState<DateValue | null>(() => toCalendarDate(value));
  const containerRef = useRef<HTMLDivElement>(null);

  // Sync display when external value changes
  useEffect(() => {
    if (!editing) setDisplay(value ? formatDate(value) : "");
  }, [value, editing]);

  // Sync pending calendar date when picker opens
  useEffect(() => {
    if (pickerOpen) setPending(toCalendarDate(value));
  }, [pickerOpen, value]);

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
    // Don't commit if focus moves into the calendar popup
    if (containerRef.current?.contains(e.relatedTarget as Node)) return;
    setEditing(false);
    const iso = parseDate(display) ?? "";
    setDisplay(iso ? formatDate(iso) : "");
    emit(iso);
  };

  const handleApply = () => {
    const iso = toISO(pending);
    setDisplay(iso ? formatDate(iso) : "");
    emit(iso);
    setPickerOpen(false);
  };

  const placeholder = getCurrentDateFormat() === "eu" ? "DD.MM.YYYY" : "YYYY-MM-DD";

  return (
    <div ref={containerRef} className={cn("relative flex items-center w-44", className)}>
      <Input
        id={id}
        type="text"
        value={editing ? display : (value ? formatDate(value) : "")}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(e) => { setEditing(true); setDisplay(e.target.value); }}
        onFocus={() => setEditing(true)}
        onBlur={handleTextBlur}
        className="pr-8"
      />
      {/* Calendar icon trigger */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setPickerOpen((v) => !v)}
        className="absolute right-2 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors disabled:pointer-events-none"
        tabIndex={-1}
      >
        <CalendarDays className="h-3.5 w-3.5" />
      </button>

      {/* Calendar popup */}
      {pickerOpen && (
        <div className="uitl-calendar absolute top-full left-0 z-50 mt-1 rounded-2xl bg-white shadow-xl ring-1 ring-black/10 overflow-hidden min-w-max">
          <div className="px-6 py-5">
            <Calendar
              value={pending}
              onChange={setPending}
            />
          </div>
          <div className="grid grid-cols-2 gap-3 border-t border-border p-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPickerOpen(false)}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleApply}
            >
              Apply
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
