import { useState } from "react";
import { CalendarDays } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { formatDate, parseDate, getCurrentDateFormat } from "@/lib/appearance";

interface DateInputProps {
  id?: string;
  value: string;
  onChange?: (e: { target: { value: string } }) => void;
  onBlur?: (e: { target: { value: string } }) => void;
  className?: string;
  disabled?: boolean;
}

export function DateInput({ id, value, onChange, onBlur, className, disabled }: DateInputProps) {
  const [display, setDisplay] = useState(() => (value ? formatDate(value) : ""));
  const [editing, setEditing] = useState(false);
  const shownValue = editing ? display : (value ? formatDate(value) : "");

  const emit = (iso: string) => onChange?.({ target: { value: iso } });

  const handleTextBlur = () => {
    setEditing(false);
    const iso = parseDate(display) ?? "";
    setDisplay(iso ? formatDate(iso) : "");
    emit(iso);
    onBlur?.({ target: { value: iso } });
  };

  const handleNativeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const iso = e.target.value;
    setDisplay(iso ? formatDate(iso) : "");
    emit(iso);
    onBlur?.({ target: { value: iso } });
  };

  const placeholder = getCurrentDateFormat() === "eu" ? "DD.MM.YYYY" : "YYYY-MM-DD";

  return (
    <div className={cn("relative w-36", className)}>
      <Input
        id={id}
        type="text"
        value={shownValue}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(e) => { setEditing(true); setDisplay(e.target.value); }}
        onFocus={() => setEditing(true)}
        onBlur={handleTextBlur}
        className="pr-7"
      />
      {/* The native date input sits directly behind the icon so the browser
          anchors its picker to this exact position. Opacity-0 hides it visually
          while keeping it fully interactive (no pointer-events-none). */}
      <div className="absolute right-0 top-0 h-full w-8 flex items-center justify-center pointer-events-none">
        <CalendarDays className="h-3.5 w-3.5 text-muted-foreground" />
      </div>
      <input
        type="date"
        value={value || ""}
        onChange={handleNativeChange}
        disabled={disabled}
        tabIndex={-1}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        style={{ colorScheme: "normal" }}
      />
    </div>
  );
}
