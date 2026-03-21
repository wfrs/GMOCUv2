import { useEffect, useMemo, useRef, useState } from "react";
import { Plus, Trash2, Search, X, Download } from "lucide-react";
import { toast } from "sonner";
import { features, type Feature } from "@/api/client";
import { useSort } from "@/hooks/use-sort";
import { SortableHead } from "@/components/sortable-head";
import { Pagination } from "@/components/pagination";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { CreateDialog } from "@/components/create-dialog";
import { exportCsv } from "@/lib/export-csv";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

interface FeaturesPageProps {
  openId?: number;
  onOpenIdConsumed?: () => void;
}

export default function FeaturesPage({ openId, onOpenIdConsumed }: FeaturesPageProps) {
  const [data, setData] = useState<Feature[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Feature | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);
  const undoRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { sorted, sortKey, sortDir, toggle: toggleSort } = useSort(data, "id");
  const toggle = toggleSort as (key: string) => void;
  const perPage = 50;
  const pageCount = Math.max(1, Math.ceil(sorted.length / perPage));
  const paged = useMemo(() => sorted.slice((page - 1) * perPage, page * perPage), [sorted, page]);

  const load = (q?: string) => {
    features.list(q).then(setData).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);
  useEffect(() => {
    const t = setTimeout(() => { load(search || undefined); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [search]);

  // Auto-open from command palette
  useEffect(() => {
    if (!openId || loading) return;
    const item = data.find((f) => f.id === openId);
    if (!item) return;
    const frame = window.requestAnimationFrame(() => {
      setSelected(item);
      setSheetOpen(true);
      onOpenIdConsumed?.();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [openId, data, loading]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Create ──
  const handleCreate = async (values: Record<string, string>) => {
    const created = await features.create({ annotation: values.annotation });
    setData((prev) => [...prev, created]);
    setSelected(created);
    setSheetOpen(true);
    toast.success(`Feature "${values.annotation}" created`);
  };

  // ── Update ──
  const handleUpdate = async (field: string, value: string) => {
    if (!selected) return;
    try {
      const updated = await features.update(selected.id, { [field]: value });
      setSelected(updated);
      setData((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update");
    }
  };

  // ── Delete single (with undo) ──
  const handleDelete = () => {
    if (!selected) return;
    const gone = selected;
    setData((prev) => prev.filter((f) => f.id !== gone.id));
    setSelected(null);
    setSheetOpen(false);

    const tid = toast(`Deleted "${gone.annotation}"`, {
      action: {
        label: "Undo",
        onClick: () => {
          clearTimeout(undoRef.current!);
          setData((prev) => [...prev, gone]);
          toast.success("Deletion undone");
        },
      },
      duration: 4000,
    });
    undoRef.current = setTimeout(async () => {
      toast.dismiss(tid);
      try { await features.delete(gone.id); } catch { load(); }
    }, 4000);
  };

  // ── Bulk delete ──
  const handleBulkDelete = () => {
    const toDelete = data.filter((f) => selectedIds.has(f.id));
    setData((prev) => prev.filter((f) => !selectedIds.has(f.id)));
    if (selected && selectedIds.has(selected.id)) { setSelected(null); setSheetOpen(false); }
    setSelectedIds(new Set());

    const tid = toast(`Deleted ${toDelete.length} features`, {
      action: {
        label: "Undo",
        onClick: () => {
          clearTimeout(undoRef.current!);
          setData((prev) => [...prev, ...toDelete]);
          toast.success("Deletion undone");
        },
      },
      duration: 4000,
    });
    undoRef.current = setTimeout(async () => {
      toast.dismiss(tid);
      try { await Promise.all(toDelete.map((f) => features.delete(f.id))); } catch { load(); }
    }, 4000);
  };

  // ── Export ──
  const handleExport = () => {
    exportCsv("features.csv", sorted.map((f) => ({
      id: f.id, annotation: f.annotation, alias: f.alias, risk: f.risk, organism: f.organism, uid: f.uid,
    })));
  };

  const toggleId = (id: number) => setSelectedIds((prev) => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });
  const toggleAll = () => setSelectedIds(selectedIds.size === paged.length ? new Set() : new Set(paged.map((f) => f.id)));

  if (loading) return <div className="flex items-center justify-center h-full text-muted-foreground">Loading…</div>;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Nucleic Acid Features</h1>
          <p className="text-sm text-muted-foreground mt-1">{data.length} feature{data.length !== 1 ? "s" : ""} in glossary</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" onClick={handleExport}>
            <Download className="h-3.5 w-3.5" /> Export CSV
          </Button>
          <Button size="sm" className="gap-1.5" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" /> New Feature
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search annotations…" value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9 pr-9" />
        {search && <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>}
      </div>

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 mb-3 px-3 py-2 bg-accent rounded-lg border border-border text-sm">
          <span className="font-medium">{selectedIds.size} selected</span>
          <Button variant="destructive" size="sm" className="gap-1.5 ml-auto" onClick={() => setBulkConfirmOpen(true)}>
            <Trash2 className="h-3.5 w-3.5" /> Delete selected
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setSelectedIds(new Set())}>Clear</Button>
        </div>
      )}

      {/* Table */}
      <div className="border rounded-lg overflow-auto flex-1">
        <Table>
          <TableHeader>
            <TableRow>
              <th className="w-10 px-3">
                <input type="checkbox" checked={selectedIds.size === paged.length && paged.length > 0} onChange={toggleAll} className="accent-primary" />
              </th>
              <SortableHead label="ID" sortKey="id" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} className="w-16" />
              <SortableHead label="Annotation" sortKey="annotation" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} />
              <SortableHead label="Alias" sortKey="alias" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} className="hidden md:table-cell" />
              <SortableHead label="Risk" sortKey="risk" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} className="w-24" />
              <SortableHead label="Organism" sortKey="organism" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} className="hidden lg:table-cell" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {paged.map((f) => (
              <TableRow
                key={f.id}
                className={`cursor-pointer ${selected?.id === f.id ? "bg-accent" : ""}`}
                onClick={() => { setSelected(f); setSheetOpen(true); }}
              >
                <TableCell className="w-10 px-3" onClick={(e) => e.stopPropagation()}>
                  <input type="checkbox" checked={selectedIds.has(f.id)} onChange={() => toggleId(f.id)} className="accent-primary" />
                </TableCell>
                <TableCell className="font-mono text-xs">{f.id}</TableCell>
                <TableCell className="font-medium">{f.annotation}</TableCell>
                <TableCell className="hidden md:table-cell text-muted-foreground truncate max-w-64">{f.alias || "—"}</TableCell>
                <TableCell>
                  <Badge variant={f.risk === "Risk" ? "destructive" : "secondary"}>{f.risk || "No Risk"}</Badge>
                </TableCell>
                <TableCell className="hidden lg:table-cell text-muted-foreground">{f.organism || "—"}</TableCell>
              </TableRow>
            ))}
            {data.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                  {search ? `No features matching "${search}".` : 'No features yet. Click "New Feature" to add one.'}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <Pagination page={page} pageCount={pageCount} onPageChange={setPage} />

      {/* Detail Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="sm:max-w-md overflow-y-auto">
          {selected && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  {selected.annotation}
                  <Badge variant={selected.risk === "Risk" ? "destructive" : "secondary"}>{selected.risk || "No Risk"}</Badge>
                </SheetTitle>
              </SheetHeader>
              <div className="space-y-5 px-4 pb-4">
                <div className="space-y-1.5">
                  <Label htmlFor="annotation">Annotation</Label>
                  <Input id="annotation" value={selected.annotation || ""} onChange={(e) => setSelected({ ...selected, annotation: e.target.value })} onBlur={(e) => handleUpdate("annotation", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="f-alias">Alias</Label>
                  <Input id="f-alias" value={selected.alias || ""} onChange={(e) => setSelected({ ...selected, alias: e.target.value })} onBlur={(e) => handleUpdate("alias", e.target.value)} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label>Risk</Label>
                    <Select value={selected.risk || "No Risk"} onValueChange={(v) => { const val = v ?? "No Risk"; setSelected({ ...selected, risk: val }); handleUpdate("risk", val); }}>
                      <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="No Risk">No Risk</SelectItem>
                        <SelectItem value="Risk">Risk</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="organism">Organism</Label>
                    <Input id="organism" value={selected.organism || ""} onChange={(e) => setSelected({ ...selected, organism: e.target.value })} onBlur={(e) => handleUpdate("organism", e.target.value)} />
                  </div>
                </div>
                <div className="text-xs text-muted-foreground font-mono">UID: {selected.uid}</div>
                <Separator />
                <Button variant="destructive" size="sm" className="gap-1.5" onClick={() => setConfirmOpen(true)}>
                  <Trash2 className="h-3.5 w-3.5" /> Delete
                </Button>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      <CreateDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="New Feature"
        fields={[{ key: "annotation", label: "Annotation name", placeholder: "e.g. lacZ", required: true }]}
        existingNames={data.map((f) => f.annotation ?? "")}
        duplicateField="annotation"
        onSubmit={handleCreate}
      />

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Delete feature?"
        description={`Permanently delete "${selected?.annotation}"? This cannot be undone.`}
        onConfirm={handleDelete}
      />

      <ConfirmDialog
        open={bulkConfirmOpen}
        onOpenChange={setBulkConfirmOpen}
        title={`Delete ${selectedIds.size} features?`}
        description="This will permanently delete all selected features."
        onConfirm={handleBulkDelete}
      />
    </div>
  );
}
