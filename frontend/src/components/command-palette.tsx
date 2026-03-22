import { useEffect, useMemo, useState } from "react";
import { Dna, FlaskConical, Bug, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogContent,
} from "@/components/ui/alert-dialog";
import type { PlasmidListItem, Feature, Organism } from "@/api/client";

type ResultType = "plasmid" | "feature" | "organism";

interface Result {
  type: ResultType;
  id: number;
  primary: string;
  secondary: string;
}

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  plasmids: PlasmidListItem[];
  features: Feature[];
  organisms: Organism[];
  onSelect: (type: ResultType, id: number) => void;
}

const TYPE_ICON: Record<ResultType, React.ElementType> = {
  plasmid: Dna,
  feature: FlaskConical,
  organism: Bug,
};

const TYPE_LABEL: Record<ResultType, string> = {
  plasmid: "Plasmid",
  feature: "Feature",
  organism: "Organism",
};

export function CommandPalette({
  open,
  onOpenChange,
  plasmids,
  features,
  organisms,
  onSelect,
}: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);

  useEffect(() => {
    if (!open) return;
    const frame = window.requestAnimationFrame(() => {
      setQuery("");
      setCursor(0);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [open]);

  const results = useMemo<Result[]>(() => {
    const q = query.toLowerCase().trim();
    if (!q) return [];
    const out: Result[] = [];
    for (const p of plasmids) {
      if (
        p.name?.toLowerCase().includes(q) ||
        p.alias?.toLowerCase().includes(q) ||
        p.backbone_vector?.toLowerCase().includes(q)
      ) {
        out.push({ type: "plasmid", id: p.id, primary: p.name ?? `#${p.id}`, secondary: p.alias ?? p.backbone_vector ?? "" });
      }
    }
    for (const f of features) {
      if (f.annotation?.toLowerCase().includes(q) || f.alias?.toLowerCase().includes(q)) {
        out.push({ type: "feature", id: f.id, primary: f.annotation ?? `#${f.id}`, secondary: f.alias ?? f.organism ?? "" });
      }
    }
    for (const o of organisms) {
      if (o.full_name?.toLowerCase().includes(q) || o.short_name?.toLowerCase().includes(q)) {
        out.push({ type: "organism", id: o.id, primary: o.full_name ?? `#${o.id}`, secondary: o.short_name ?? "" });
      }
    }
    return out.slice(0, 12);
  }, [query, plasmids, features, organisms]);

  const activeCursor = Math.min(cursor, Math.max(results.length - 1, 0));

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, results.length - 1)); }
    if (e.key === "ArrowUp")   { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
    if (e.key === "Enter" && results[activeCursor]) {
      const r = results[activeCursor];
      onSelect(r.type, r.id);
      onOpenChange(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="p-0 gap-0 overflow-hidden max-w-lg">
        <div className="flex items-center gap-3 px-4 py-3 border-b">
          <Search className="h-4 w-4 text-muted-foreground shrink-0" />
          <Input
            className="border-0 shadow-none focus-visible:ring-0 pl-1 pr-0 h-7 text-base"
            placeholder="Search plasmids, features, organisms…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setCursor(0);
            }}
            onKeyDown={handleKey}
            autoFocus
          />
          <kbd className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full border shrink-0">Esc</kbd>
        </div>

        {results.length > 0 ? (
          <ul className="py-1 max-h-80 overflow-y-auto">
            {results.map((r, i) => {
              const Icon = TYPE_ICON[r.type];
              return (
                <li
                  key={`${r.type}-${r.id}`}
                  className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer text-sm transition-colors ${
                    i === activeCursor ? "bg-accent text-accent-foreground" : "hover:bg-muted"
                  }`}
                  onMouseEnter={() => setCursor(i)}
                  onClick={() => { onSelect(r.type, r.id); onOpenChange(false); }}
                >
                  <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="flex-1 font-medium truncate">{r.primary}</span>
                  {r.secondary && <span className="text-muted-foreground truncate max-w-40">{r.secondary}</span>}
                  <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full shrink-0">
                    {TYPE_LABEL[r.type]}
                  </span>
                </li>
              );
            })}
          </ul>
        ) : query ? (
          <p className="px-4 py-6 text-center text-sm text-muted-foreground">No results for "{query}"</p>
        ) : (
          <p className="px-4 py-6 text-center text-sm text-muted-foreground">Start typing to search…</p>
        )}
      </AlertDialogContent>
    </AlertDialog>
  );
}
