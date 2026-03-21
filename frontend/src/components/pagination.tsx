import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

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

  return (
    <div className="flex items-center justify-between px-2 py-3">
      <p className="text-xs text-muted-foreground">
        Page {page} of {pageCount}
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon-sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        {pageCount <= 7 ? (
          Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
            <Button
              key={p}
              variant={p === page ? "default" : "outline"}
              size="icon-sm"
              onClick={() => onPageChange(p)}
              className="w-8"
            >
              {p}
            </Button>
          ))
        ) : (
          <>
            {[1, 2].map((p) => (
              <Button key={p} variant={p === page ? "default" : "outline"} size="icon-sm" onClick={() => onPageChange(p)} className="w-8">{p}</Button>
            ))}
            {page > 3 && <span className="px-1 text-muted-foreground text-xs">...</span>}
            {page > 2 && page < pageCount - 1 && (
              <Button variant="default" size="icon-sm" className="w-8">{page}</Button>
            )}
            {page < pageCount - 2 && <span className="px-1 text-muted-foreground text-xs">...</span>}
            {[pageCount - 1, pageCount].map((p) => (
              <Button key={p} variant={p === page ? "default" : "outline"} size="icon-sm" onClick={() => onPageChange(p)} className="w-8">{p}</Button>
            ))}
          </>
        )}
        <Button
          variant="outline"
          size="icon-sm"
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
