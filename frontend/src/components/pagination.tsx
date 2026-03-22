import { ChevronLeft, ChevronRight } from "lucide-react";

function PageBtn({
  p,
  active,
  onClick,
}: {
  p: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`h-8 min-w-8 px-2.5 rounded-md text-sm font-medium transition-colors border-0 outline-none cursor-pointer ${
        active
          ? "bg-primary text-primary-foreground"
          : "bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
      }`}
    >
      {p}
    </button>
  );
}

export function Pagination({
  page,
  pageCount,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}) {
  if (pageCount <= 1) return null;

  // Build a sorted set of page numbers to show:
  // always show first 4 and last 4, plus current ±1 window
  const pageSet = new Set<number>();
  for (let i = 1; i <= Math.min(4, pageCount); i++) pageSet.add(i);
  for (let i = Math.max(1, pageCount - 3); i <= pageCount; i++) pageSet.add(i);
  for (let i = Math.max(1, page - 1); i <= Math.min(pageCount, page + 1); i++) pageSet.add(i);

  const sorted = Array.from(pageSet).sort((a, b) => a - b);
  const pages: (number | "…")[] = [];
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) pages.push("…");
    pages.push(sorted[i]);
  }

  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center px-1 py-3">
      <span className="text-xs text-muted-foreground">
        Page {page} of {pageCount}
      </span>
      <div className="flex items-center gap-1">
        <button
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="h-8 w-8 flex items-center justify-center rounded-md text-muted-foreground transition-colors border-0 outline-none cursor-pointer hover:bg-muted hover:text-foreground disabled:opacity-30 disabled:pointer-events-none"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        {pages.map((p, i) =>
          p === "…" ? (
            <span key={`ellipsis-${i}`} className="h-8 w-6 flex items-center justify-center text-xs text-muted-foreground">
              …
            </span>
          ) : (
            <PageBtn key={p} p={p} active={p === page} onClick={() => onPageChange(p)} />
          )
        )}
        <button
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
          className="h-8 w-8 flex items-center justify-center rounded-md text-muted-foreground transition-colors border-0 outline-none cursor-pointer hover:bg-muted hover:text-foreground disabled:opacity-30 disabled:pointer-events-none"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
      <div />
    </div>
  );
}
