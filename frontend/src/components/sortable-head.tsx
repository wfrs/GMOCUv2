import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { TableHead } from "@/components/ui/table";
import type { SortDir } from "@/hooks/use-sort";

export function SortableHead({
  label,
  sortKey,
  activeSortKey,
  sortDir,
  onSort,
  className,
}: {
  label: string;
  sortKey: string;
  activeSortKey: string | null;
  sortDir: SortDir;
  onSort: (key: string) => void;
  className?: string;
}) {
  const isActive = activeSortKey === sortKey;

  return (
    <TableHead
      className={`cursor-pointer select-none ${className ?? ""}`}
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {isActive ? (
          sortDir === "asc" ? (
            <ArrowUp className="h-3.5 w-3.5 text-foreground" />
          ) : (
            <ArrowDown className="h-3.5 w-3.5 text-foreground" />
          )
        ) : (
          <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground/50" />
        )}
      </span>
    </TableHead>
  );
}
