import { useMemo, useState } from "react";

export type SortDir = "asc" | "desc";

export function useSort<T>(data: T[], defaultKey?: keyof T & string) {
  const [sortKey, setSortKey] = useState<(keyof T & string) | null>(defaultKey ?? null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const toggle = (key: keyof T & string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      const as = String(av).toLowerCase();
      const bs = String(bv).toLowerCase();
      const cmp = as.localeCompare(bs);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  return { sorted, sortKey, sortDir, toggle };
}
