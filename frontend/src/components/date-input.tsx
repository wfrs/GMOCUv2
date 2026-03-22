import { useEffect, useState } from "react";
import { parseDate as parseCalendarDate } from "@internationalized/date";
import type { DateValue } from "react-aria-components";
import { DatePicker } from "@/components/application/date-picker/date-picker";

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
  try {
    return parseCalendarDate(iso);
  } catch {
    return null;
  }
}

export function DateInput({ value, onChange, onBlur, disabled }: DateInputProps) {
  const [pending, setPending] = useState<DateValue | null>(() => toCalendarDate(value));

  useEffect(() => {
    setPending(toCalendarDate(value));
  }, [value]);

  return (
    <DatePicker
      value={pending}
      onChange={setPending}
      onApply={() => {
        const iso = toISO(pending);
        onChange?.({ target: { value: iso } });
        onBlur?.({ target: { value: iso } });
      }}
      onCancel={() => {
        setPending(toCalendarDate(value));
      }}
      isDisabled={disabled}
    />
  );
}
