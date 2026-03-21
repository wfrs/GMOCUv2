import { useEffect, useMemo, useRef, useState } from "react";
import { Plus, Trash2, Search, X, Download } from "lucide-react";
import { toast } from "sonner";
import { organisms, type Organism } from "@/api/client";
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

const RG_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  "1": "secondary", "2": "outline", "3": "default", "4": "destructive",
};

interface OrganismsPageProps {
  openId?: number;
  onOpenIdConsumed?: () => void;
}

export default function OrganismsPage({ openId, onOpenIdConsumed }: OrganismsPageProps) {
  const [data, setData] = useState<Organism[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Organism | null>(null);
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
    organisms.list(q).then(setData).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);
  useEffect(() => {
    const t = setTimeout(() => { load(search || undefined); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [search]);

  // Auto-open from command palette
  useEffect(() => {
    if (!openId || loading) return;
    const item = data.find((o) => o.id === openId);
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
    const created = await organisms.create({ full_name: values.full_name, short_name: values.short_name });
    setData((prev) => [...prev, created]);
    setSelected(created);
    setSheetOpen(true);
    toast.success(`Organism "${values.short_name}" created`);
  };

  // ── Update ──
  const handleUpdate = async (field: string, value: string) => {
    if (!selected) return;
    try {
      const updated = await organisms.update(selected.id, { [field]: value });
      setSelected(updated);
      setData((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update");
    }
  };

  // ── Delete single (with undo) ──
  const handleDelete = () => {
    if (!selected) return;
    const gone = selected;
    setData((prev) => prev.filter((o) => o.id !== gone.id));
    setSelected(null);
    setSheetOpen(false);

    const tid = toast(`Deleted "${gone.short_name}"`, {
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
      try { await organisms.delete(gone.id); } catch { load(); }
    }, 4000);
  };

  // ── Bulk delete ──
  const handleBulkDelete = () => {
    const toDelete = data.filter((o) => selectedIds.has(o.id));
    setData((prev) => prev.filter((o) => !selectedIds.has(o.id)));
    if (selected && selectedIds.has(selected.id)) { setSelected(null); setSheetOpen(false); }
    setSelectedIds(new Set());

    const tid = toast(`Deleted ${toDelete.length} organisms`, {
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
      try { await Promise.all(toDelete.map((o) => organisms.delete(o.id))); } catch { load(); }
    }, 4000);
  };

  // ── Export ──
  const handleExport = () => {
    exportCsv("organisms.csv", sorted.map((o) => ({
      id: o.id, full_name: o.full_name, short_name: o.short_name, risk_group: o.risk_group, uid: o.uid,
    })));
  };

  const toggleId = (id: number) => setSelectedIds((prev) => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });
  const toggleAll = () => setSelectedIds(selectedIds.size === paged.length ? new Set() : new Set(paged.map((o) => o.id)));

  if (loading) return <div className="flex items-center justify-center h-full text-muted-foreground">Loading…</div>;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Organisms</h1>
          <p className="text-sm text-muted-foreground mt-1">{data.length} organism{data.length !== 1 ? "s" : ""} in glossary</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" onClick={handleExport}>
            <Download className="h-3.5 w-3.5" /> Export CSV
          </Button>
          <Button size="sm" className="gap-1.5" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" /> New Organism
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search organisms…" value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9 pr-9" />
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
              <SortableHead label="Full Name" sortKey="full_name" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} />
              <SortableHead label="Short Name" sortKey="short_name" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} />
              <SortableHead label="RG" sortKey="risk_group" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} className="w-20" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {paged.map((o) => (
              <TableRow key={o.id} className={`cursor-pointer ${selected?.id === o.id ? "bg-accent" : ""}`} onClick={() => { setSelected(o); setSheetOpen(true); }}>
                <TableCell className="w-10 px-3" onClick={(e) => e.stopPropagation()}>
                  <input type="checkbox" checked={selectedIds.has(o.id)} onChange={() => toggleId(o.id)} className="accent-primary" />
                </TableCell>
                <TableCell className="font-mono text-xs">{o.id}</TableCell>
                <TableCell className="font-medium">{o.full_name}</TableCell>
                <TableCell className="text-muted-foreground">{o.short_name}</TableCell>
                <TableCell>
                  <Badge variant={RG_COLORS[o.risk_group || "1"] || "secondary"}>RG {o.risk_group || "1"}</Badge>
                </TableCell>
              </TableRow>
            ))}
            {data.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                  {search ? `No organisms matching "${search}".` : 'No organisms yet. Click "New Organism" to add one.'}
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
                  {selected.short_name}
                  <Badge variant={RG_COLORS[selected.risk_group || "1"] || "secondary"}>RG {selected.risk_group || "1"}</Badge>
                </SheetTitle>
              </SheetHeader>
              <div className="space-y-5 px-4 pb-4">
                <div className="space-y-1.5">
                  <Label htmlFor="full_name">Full Name</Label>
                  <Input id="full_name" value={selected.full_name || ""} onChange={(e) => setSelected({ ...selected, full_name: e.target.value })} onBlur={(e) => handleUpdate("full_name", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="short_name">Short Name</Label>
                  <Input id="short_name" value={selected.short_name || ""} onChange={(e) => setSelected({ ...selected, short_name: e.target.value })} onBlur={(e) => handleUpdate("short_name", e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label>Risk Group</Label>
                  <Select value={selected.risk_group || "1"} onValueChange={(v) => { const val = v ?? "1"; setSelected({ ...selected, risk_group: val }); handleUpdate("risk_group", val); }}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1</SelectItem>
                      <SelectItem value="2">2</SelectItem>
                      <SelectItem value="3">3</SelectItem>
                      <SelectItem value="4">4</SelectItem>
                    </SelectContent>
                  </Select>
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
        title="New Organism"
        fields={[
          { key: "full_name", label: "Full name", placeholder: "e.g. Escherichia coli", required: true },
          { key: "short_name", label: "Short name", placeholder: "e.g. E. coli", required: true },
        ]}
        existingNames={data.map((o) => o.full_name ?? "")}
        duplicateField="full_name"
        onSubmit={handleCreate}
      />

      <ConfirmDialog open={confirmOpen} onOpenChange={setConfirmOpen} title="Delete organism?" description={`Permanently delete "${selected?.short_name}"?`} onConfirm={handleDelete} />
      <ConfirmDialog open={bulkConfirmOpen} onOpenChange={setBulkConfirmOpen} title={`Delete ${selectedIds.size} organisms?`} description="This will permanently delete all selected organisms." onConfirm={handleBulkDelete} />
    </div>
  );
}
