import { useEffect, useMemo, useRef, useState } from "react";
import { formatDate } from "@/lib/appearance";

const ISO_DATE_RE = /\d{4}-\d{2}-\d{2}/g;
function fmtSummary(s: string | null | undefined): string {
  if (!s) return "No GMO summary";
  return s.replace(ISO_DATE_RE, (m) => formatDate(m));
}
import {
  Plus, Trash2, Search, Download, Upload, X, FileText,
  Paperclip, ChevronDown, Loader2, Copy, Download as DownloadIcon,
  Maximize2, Minimize2, ArrowLeft, CheckCircle2, ClipboardList,
} from "lucide-react";
import { toast } from "sonner";
import {
  plasmids, organismSelections,
  type Plasmid, type PlasmidListItem, type OrganismSelectionItem,
} from "@/api/client";
import { useSort } from "@/hooks/use-sort";
import { SortableHead } from "@/components/sortable-head";
import { Pagination } from "@/components/pagination";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { FormblattDialog } from "@/components/formblatt-dialog";
import { PlasmidMap } from "@/components/plasmid-map";
import { parseGenbank } from "@/lib/parse-genbank";
import { exportCsv } from "@/lib/export-csv";
import {
  Tooltip, TooltipTrigger, TooltipContent, TooltipProvider,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";

const STATUS_MAP: Record<number, { label: string; className: string }> = {
  1: { label: "Complete",    className: "bg-emerald-500/12 text-emerald-700 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-700/40" },
  2: { label: "In Progress", className: "bg-blue-500/12 text-blue-700 dark:text-blue-400 border-blue-200/60 dark:border-blue-700/40" },
  3: { label: "Abandoned",   className: "bg-orange-500/12 text-orange-700 dark:text-orange-400 border-orange-200/60 dark:border-orange-700/40" },
  4: { label: "Planned",     className: "bg-muted text-muted-foreground border-border" },
};

const PER_PAGE = 50;
const todayString = () => new Date().toISOString().slice(0, 10);

interface PlasmidsPageProps {
  openId?: number;
  onOpenIdConsumed?: () => void;
}

export default function PlasmidsPage({ openId, onOpenIdConsumed }: PlasmidsPageProps) {
  const [data, setData] = useState<PlasmidListItem[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Plasmid | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [targetOrganisms, setTargetOrganisms] = useState<OrganismSelectionItem[]>([]);
  const [editingCassette, setEditingCassette] = useState<number | null>(null);
  const [cassetteValue, setCassetteValue] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ title: string; description: string; onConfirm: () => void }>({ title: "", description: "", onConfirm: () => {} });
  const [expanded, setExpanded] = useState(false);
  const [formblattOpen, setFormblattOpen] = useState(false);
  const [newGmoOrganism, setNewGmoOrganism] = useState("");
  const [newGmoTargetRiskGroup, setNewGmoTargetRiskGroup] = useState(1);
  const [newGmoApproval, setNewGmoApproval] = useState("-");
  const [newGmoCreatedOn, setNewGmoCreatedOn] = useState(todayString());
  const undoRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const gbFileRef = useRef<HTMLInputElement>(null);
  const attachFileRef = useRef<HTMLInputElement>(null);

  const { sorted, sortKey, sortDir, toggle: toggleSort } = useSort(data, "id");
  const toggle = toggleSort as (key: string) => void;
  const pageCount = Math.max(1, Math.ceil(sorted.length / PER_PAGE));
  const paged = useMemo(() => sorted.slice((page - 1) * PER_PAGE, page * PER_PAGE), [sorted, page]);

  const parsedGb = useMemo(
    () => selected?.genbank_filename ? parseGenbank(selected.genbank_content ?? "") : null,
    [selected?.genbank_content, selected?.genbank_filename],
  );

  const load = (q?: string) => plasmids.list(q).then(setData).finally(() => setLoading(false));

  useEffect(() => { load(); organismSelections.list().then(setTargetOrganisms); }, []);
  useEffect(() => {
    const t = setTimeout(() => { load(search || undefined); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [search]);
  useEffect(() => { setPage(1); }, [sortKey, sortDir]);
  useEffect(() => {
    setNewGmoOrganism("");
    setNewGmoTargetRiskGroup(selected?.target_risk_group ?? 1);
    setNewGmoApproval("-");
    setNewGmoCreatedOn(todayString());
  }, [selected?.id, selected?.target_risk_group]);

  // Auto-open from command palette
  useEffect(() => {
    if (!openId || loading) return;
    const item = data.find((p) => p.id === openId);
    if (item) { openPlasmid(item); onOpenIdConsumed?.(); }
  }, [openId, data, loading]); // eslint-disable-line react-hooks/exhaustive-deps

  const confirm = (title: string, description: string, onConfirm: () => void) => {
    setConfirmAction({ title, description, onConfirm });
    setConfirmOpen(true);
  };

  const openPlasmid = async (p: PlasmidListItem) => {
    setSheetOpen(true);
    setSelected(null);
    setDetailLoading(true);
    try {
      setSelected(await plasmids.get(p.id));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load plasmid");
    } finally {
      setDetailLoading(false);
    }
  };

  const refreshSelected = async (id: number) => {
    const updated = await plasmids.get(id);
    setSelected(updated);
    setData((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    return updated;
  };

  // ── Create ──
  const handleCreate = async () => {
    try {
      const created = await plasmids.create({ name: "pXX000" });
      setData((prev) => [...prev, created]);
      setSelected(created);
      setSheetOpen(true);
      toast.success("Plasmid created");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create plasmid");
    }
  };

  // ── Duplicate ──
  const handleDuplicate = async () => {
    if (!selected) return;
    try {
      const copy = await plasmids.duplicate(selected.id);
      setData((prev) => [...prev, copy]);
      setSelected(copy);
      toast.success(`Duplicated as "${copy.name}"`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to duplicate");
    }
  };

  // ── Update ──
  const handleUpdate = async (field: string, value: string | number | null) => {
    if (!selected) return;
    try {
      const updated = await plasmids.update(selected.id, { [field]: value });
      setSelected(updated);
      setData((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update");
    }
  };

  // ── Delete single (with undo) ──
  const handleDelete = () => {
    if (!selected) return;
    const gone = selected;
    setData((prev) => prev.filter((p) => p.id !== gone.id));
    setSelected(null);
    setSheetOpen(false);
    setExpanded(false);

    const tid = toast(`Deleted "${gone.name}"`, {
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
      try { await plasmids.delete(gone.id); } catch { load(); }
    }, 4000);
  };

  // ── Bulk delete ──
  const handleBulkDelete = () => {
    const toDelete = data.filter((p) => selectedIds.has(p.id));
    setData((prev) => prev.filter((p) => !selectedIds.has(p.id)));
    if (selected && selectedIds.has(selected.id)) { setSelected(null); setSheetOpen(false); }
    setSelectedIds(new Set());

    const tid = toast(`Deleted ${toDelete.length} plasmids`, {
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
      try { await Promise.all(toDelete.map((p) => plasmids.delete(p.id))); } catch { load(); }
    }, 4000);
  };

  // ── Export ──
  const handleExport = () => {
    const rows = (selectedIds.size > 0 ? sorted.filter((p) => selectedIds.has(p.id)) : sorted).map((p) => ({
      id: p.id, name: p.name, alias: p.alias,
      status: STATUS_MAP[p.status_id ?? 4]?.label,
      clone: p.clone, backbone_vector: p.backbone_vector,
      marker: p.marker, target_risk_group: p.target_risk_group,
      created_on: p.created_on, destroyed_on: p.destroyed_on,
    }));
    exportCsv("plasmids.csv", rows);
  };

  // ── Cassettes ──
  const handleAddCassette = async () => {
    if (!selected) return;
    try { await plasmids.addCassette(selected.id); await refreshSelected(selected.id); }
    catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Failed to add cassette"); }
  };
  const handleSaveCassette = async (id: number) => {
    try { await plasmids.updateCassette(id, cassetteValue); setEditingCassette(null); if (selected) await refreshSelected(selected.id); }
    catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Failed to update cassette"); }
  };
  const handleDeleteCassette = async (id: number) => {
    if (!selected) return;
    try { await plasmids.deleteCassette(id); await refreshSelected(selected.id); }
    catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Failed to delete cassette"); }
  };

  // ── GMOs ──
  const handleAddGmo = async () => {
    if (!selected) return;
    if (!newGmoOrganism) return;
    try {
      await plasmids.addGmo(selected.id, {
        organism_name: newGmoOrganism,
        approval: newGmoApproval,
        target_risk_group: newGmoTargetRiskGroup,
        created_on: newGmoCreatedOn || null,
      });
      await refreshSelected(selected.id);
      setNewGmoOrganism("");
      setNewGmoCreatedOn(todayString());
      toast.success(`Added ${newGmoOrganism}`);
    }
    catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Failed to add GMO"); }
  };
  const handleUpdateGmo = async (
    id: number,
    patch: {
      organism_name?: string | null;
      approval?: string | null;
      target_risk_group?: number | null;
      created_on?: string | null;
      destroyed_on?: string | null;
    },
  ) => {
    if (!selected) return;
    try {
      await plasmids.updateGmo(id, patch);
      await refreshSelected(selected.id);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update GMO");
    }
  };
  const handleDeleteGmo = async (id: number) => {
    if (!selected) return;
    try { await plasmids.deleteGmo(id); await refreshSelected(selected.id); }
    catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Failed to delete GMO"); }
  };
  const handleDestroyGmo = async (id: number) => {
    if (!selected) return;
    try { await plasmids.destroyGmo(id); await refreshSelected(selected.id); }
    catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Failed to mark destroyed"); }
  };

  // ── GenBank ──
  const handleGbUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selected) return;
    e.target.value = "";
    try {
      const text = await file.text();
      await plasmids.uploadGenbank(selected.id, file.name, text);
      await refreshSelected(selected.id);
      toast.success("GenBank file uploaded");
    } catch (err: unknown) { toast.error(err instanceof Error ? err.message : "Failed to upload"); }
  };
  const handleGbDownload = () => { if (selected) window.open(`/api/plasmids/${selected.id}/genbank`, "_blank"); };
  const handleGbDelete = async () => {
    if (!selected) return;
    try { await plasmids.deleteGenbank(selected.id); await refreshSelected(selected.id); toast.success("GenBank file removed"); }
    catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Failed to remove"); }
  };

  // ── Attachments ──
  const handleAttachUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selected) return;
    e.target.value = "";
    try { await plasmids.uploadAttachment(selected.id, file); await refreshSelected(selected.id); toast.success(`Uploaded "${file.name}"`); }
    catch (err: unknown) { toast.error(err instanceof Error ? err.message : "Failed to upload"); }
  };
  const handleAttachDownload = (id: number) => window.open(`/api/plasmids/attachments/${id}/download`, "_blank");
  const handleAttachDelete = async (id: number) => {
    if (!selected) return;
    try { await plasmids.deleteAttachment(id); await refreshSelected(selected.id); }
    catch (e: unknown) { toast.error(e instanceof Error ? e.message : "Failed to delete"); }
  };

  const toggleId = (id: number) => setSelectedIds((prev) => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });
  const toggleAll = () => setSelectedIds(selectedIds.size === paged.length ? new Set() : new Set(paged.map((p) => p.id)));

  if (loading) return <div className="flex items-center justify-center h-full text-muted-foreground">Loading…</div>;

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full">

        {/* ── Expanded full-page view ── */}
        {expanded && selected && (
          <div className="flex flex-col h-full">
            {/* Top bar */}
            <div className="flex items-center gap-3 mb-6 pb-4 border-b shrink-0">
              <Button variant="ghost" size="sm" className="gap-1.5"
                onClick={() => { setExpanded(false); setSheetOpen(true); }}>
                <ArrowLeft className="h-4 w-4" /> Back
              </Button>
              <h2 className="text-xl font-semibold">{selected.name}</h2>
              <Badge variant="outline" className={STATUS_MAP[selected.status_id ?? 4].className}>
                {STATUS_MAP[selected.status_id ?? 4].label}
              </Badge>
              <Button variant="ghost" size="sm" className="gap-1.5 ml-auto"
                onClick={() => { setExpanded(false); setSheetOpen(true); }}>
                <Minimize2 className="h-4 w-4" /> Collapse
              </Button>
            </div>

            {/* Workflow progress banner (expanded) */}
            {(() => {
              const cassetteDone = selected.cassettes.some(c => c.content && c.content !== "Empty");
              const gmosDone = selected.gmos.length > 0;
              return (
                <div className="mb-6 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 shrink-0">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2.5">GMO Registration Workflow</p>
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cassetteDone ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-400" : "bg-muted text-muted-foreground"}`}>
                      {cassetteDone
                        ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                        : <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border border-current text-[9px] font-bold">1</span>}
                      Cassette
                    </div>
                    <span className="text-muted-foreground/40 text-xs">›</span>
                    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${gmosDone ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-400" : "bg-muted text-muted-foreground"}`}>
                      {gmosDone
                        ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                        : <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border border-current text-[9px] font-bold">2</span>}
                      GMOs{gmosDone ? ` (${selected.gmos.length})` : ""}
                    </div>
                    <span className="text-muted-foreground/40 text-xs">›</span>
                    <Tooltip>
                      <TooltipTrigger render={
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-dashed border-primary/30 text-xs font-medium text-primary/50 cursor-not-allowed select-none">
                          <ClipboardList className="h-3.5 w-3.5 shrink-0" />
                          Formblatt Z
                        </div>
                      } />
                      <TooltipContent>Coming soon</TooltipContent>
                    </Tooltip>
                  </div>
                </div>
              );
            })()}

            {/* 3-column grid */}
            <div className="flex-1 overflow-auto">
              <div className="grid grid-cols-3 gap-8 pb-2">

                {/* Col 1 — Basic fields */}
                <div className="space-y-5">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="ep-name">Name</Label>
                      <Input id="ep-name" value={selected.name || ""} onChange={(e) => setSelected({ ...selected, name: e.target.value })} onBlur={(e) => handleUpdate("name", e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="ep-alias">Alias</Label>
                      <Input id="ep-alias" value={selected.alias || ""} onChange={(e) => setSelected({ ...selected, alias: e.target.value })} onBlur={(e) => handleUpdate("alias", e.target.value)} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="ep-backbone">Backbone Vector</Label>
                      <Input id="ep-backbone" value={selected.backbone_vector || ""} onChange={(e) => setSelected({ ...selected, backbone_vector: e.target.value })} onBlur={(e) => handleUpdate("backbone_vector", e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="ep-marker">Marker</Label>
                      <Input id="ep-marker" value={selected.marker || ""} onChange={(e) => setSelected({ ...selected, marker: e.target.value })} onBlur={(e) => handleUpdate("marker", e.target.value)} />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-1.5">
                      <Label>Status</Label>
                      <Select value={String(selected.status_id ?? 4)} onValueChange={(v) => { const val = Number(v ?? 4); setSelected({ ...selected, status_id: val }); handleUpdate("status_id", val); }}>
                        <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1">Complete</SelectItem>
                          <SelectItem value="2">In Progress</SelectItem>
                          <SelectItem value="3">Abandoned</SelectItem>
                          <SelectItem value="4">Planned</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="ep-rg">Target RG</Label>
                      <Input id="ep-rg" type="number" min={1} max={4} value={selected.target_risk_group ?? 1} onChange={(e) => setSelected({ ...selected, target_risk_group: Number(e.target.value) })} onBlur={(e) => handleUpdate("target_risk_group", Number(e.target.value))} />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="ep-clone">Clone</Label>
                      <Input id="ep-clone" value={selected.clone || ""} onChange={(e) => setSelected({ ...selected, clone: e.target.value })} onBlur={(e) => handleUpdate("clone", e.target.value)} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <Label>Organism Selector</Label>
                      <Select
                        value={selected.target_organism_selection_id ? String(selected.target_organism_selection_id) : "none"}
                        onValueChange={(v) => {
                          const nextValue = v === "none" ? null : Number(v);
                          setSelected({ ...selected, target_organism_selection_id: nextValue });
                          handleUpdate("target_organism_selection_id", nextValue);
                        }}
                      >
                        <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">None</SelectItem>
                          {targetOrganisms
                            .filter((t) => t.organism_name)
                            .map((t) => (
                              <SelectItem key={t.id} value={String(t.id)}>{t.organism_name}</SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="ep-recorded-on">Entry Date</Label>
                      <Input
                        id="ep-recorded-on"
                        type="date"
                        value={selected.recorded_on || ""}
                        onChange={(e) => setSelected({ ...selected, recorded_on: e.target.value || null })}
                        onBlur={(e) => handleUpdate("recorded_on", e.target.value || null)}
                      />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="ep-purpose">Purpose</Label>
                    <Textarea id="ep-purpose" rows={3} value={selected.purpose || ""} onChange={(e) => setSelected({ ...selected, purpose: e.target.value })} onBlur={(e) => handleUpdate("purpose", e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="ep-summary">Cloning Summary</Label>
                    <Textarea id="ep-summary" rows={5} value={selected.summary || ""} onChange={(e) => setSelected({ ...selected, summary: e.target.value })} onBlur={(e) => handleUpdate("summary", e.target.value)} />
                  </div>
                  <Separator />
                  <div className="flex gap-2 flex-wrap">
                    <Tooltip>
                      <TooltipTrigger render={<Button variant="outline" size="sm" className="gap-1.5" onClick={handleDuplicate} />}>
                        <Copy className="h-3.5 w-3.5" /> Duplicate
                      </TooltipTrigger>
                      <TooltipContent>Create a copy of this plasmid</TooltipContent>
                    </Tooltip>
                    <Button variant="destructive" size="sm" className="gap-1.5"
                      onClick={() => confirm("Delete plasmid?", `Permanently delete "${selected.name}"? This will also remove all GMOs and attachments.`, handleDelete)}>
                      <Trash2 className="h-3.5 w-3.5" /> Delete Plasmid
                    </Button>
                  </div>
                </div>

                {/* Col 2 — Cassettes + GMOs + Attachments */}
                <div className="space-y-6">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <Label className="text-xs uppercase tracking-wider text-muted-foreground">Cassettes</Label>
                      <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={handleAddCassette}>
                        <Plus className="h-3 w-3" /> Add
                      </Button>
                    </div>
                    <div className="space-y-1.5">
                      {selected.cassettes.map((c) => (
                        <div key={c.id} className="flex items-center gap-1.5">
                          {editingCassette === c.id ? (
                            <>
                              <Input className="h-8 font-mono text-sm flex-1" value={cassetteValue} onChange={(e) => setCassetteValue(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") handleSaveCassette(c.id); if (e.key === "Escape") setEditingCassette(null); }} autoFocus />
                              <Tooltip>
                                <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => handleSaveCassette(c.id)} />}>
                                  <ChevronDown className="h-3.5 w-3.5" />
                                </TooltipTrigger>
                                <TooltipContent>Save</TooltipContent>
                              </Tooltip>
                            </>
                          ) : (
                            <>
                              <div className="flex-1 px-3 py-1.5 bg-muted rounded-md text-sm font-mono cursor-pointer hover:bg-muted/80" onClick={() => { setEditingCassette(c.id); setCassetteValue(c.content || ""); }}>
                                {c.content || "Empty"}
                              </div>
                              <Tooltip>
                                <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => confirm("Delete cassette?", `Remove "${c.content || "Empty"}"?`, () => handleDeleteCassette(c.id))} />}>
                                  <X className="h-3.5 w-3.5 text-muted-foreground" />
                                </TooltipTrigger>
                                <TooltipContent>Remove cassette</TooltipContent>
                              </Tooltip>
                            </>
                          )}
                        </div>
                      ))}
                      {selected.cassettes.length === 0 && <p className="text-sm text-muted-foreground">No cassettes</p>}
                    </div>
                  </div>
                  <Separator />
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <Label className="text-xs uppercase tracking-wider text-muted-foreground">GMOs</Label>
                    </div>
                    <div className="grid grid-cols-[minmax(0,1.4fr)_96px_minmax(0,1fr)_minmax(0,1fr)_auto] gap-2 mb-3">
                      <Select value={newGmoOrganism || undefined} onValueChange={(value) => setNewGmoOrganism(value ?? "")}>
                        <SelectTrigger className="w-full"><SelectValue placeholder="Organism…" /></SelectTrigger>
                        <SelectContent>
                          {targetOrganisms
                            .filter((t) => t.organism_name)
                            .map((t) => (
                              <SelectItem key={t.id} value={t.organism_name || ""}>{t.organism_name}</SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                      <Input type="number" min={1} max={4} value={newGmoTargetRiskGroup} onChange={(e) => setNewGmoTargetRiskGroup(Number(e.target.value) || 1)} placeholder="RG" />
                      <Input value={newGmoApproval} onChange={(e) => setNewGmoApproval(e.target.value)} placeholder="Approval" />
                      <Input type="date" value={newGmoCreatedOn} onChange={(e) => setNewGmoCreatedOn(e.target.value)} />
                      <Button variant="outline" size="sm" className="h-9" onClick={handleAddGmo}>Add</Button>
                    </div>
                    <div className="space-y-1.5">
                      {selected.gmos.map((g) => (
                        <div key={g.id} className="px-3 py-3 bg-muted rounded-md text-sm">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="font-medium">{g.organism_name}</span>
                            {g.destroyed_on && <Badge variant="destructive" className="text-[10px]">Destroyed</Badge>}
                          </div>
                          <div className="grid grid-cols-[minmax(0,1.2fr)_92px_minmax(0,1fr)_minmax(0,1fr)] gap-2 mb-2">
                            <Input value={g.organism_name || ""} onChange={(e) => setSelected({ ...selected, gmos: selected.gmos.map((item) => item.id === g.id ? { ...item, organism_name: e.target.value } : item) })} onBlur={(e) => handleUpdateGmo(g.id, { organism_name: e.target.value || null })} />
                            <Input type="number" min={1} max={4} value={g.target_risk_group ?? 1} onChange={(e) => setSelected({ ...selected, gmos: selected.gmos.map((item) => item.id === g.id ? { ...item, target_risk_group: Number(e.target.value) || 1 } : item) })} onBlur={(e) => handleUpdateGmo(g.id, { target_risk_group: Number(e.target.value) || 1 })} />
                            <Input value={g.approval || ""} onChange={(e) => setSelected({ ...selected, gmos: selected.gmos.map((item) => item.id === g.id ? { ...item, approval: e.target.value } : item) })} onBlur={(e) => handleUpdateGmo(g.id, { approval: e.target.value || null })} />
                            <Input type="date" value={g.created_on || ""} onChange={(e) => setSelected({ ...selected, gmos: selected.gmos.map((item) => item.id === g.id ? { ...item, created_on: e.target.value || null } : item) })} onBlur={(e) => handleUpdateGmo(g.id, { created_on: e.target.value || null })} />
                          </div>
                          <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2 items-center">
                            <Input type="date" value={g.destroyed_on || ""} onChange={(e) => setSelected({ ...selected, gmos: selected.gmos.map((item) => item.id === g.id ? { ...item, destroyed_on: e.target.value || null } : item) })} onBlur={(e) => handleUpdateGmo(g.id, { destroyed_on: e.target.value || null })} />
                            <div className="flex items-center gap-0.5 ml-2">
                            {!g.destroyed_on && (
                              <Tooltip>
                                <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => confirm("Mark GMO as destroyed?", `Set today as destruction date for ${g.organism_name}.`, () => handleDestroyGmo(g.id))} />}>
                                  <Trash2 className="h-3.5 w-3.5 text-orange-500" />
                                </TooltipTrigger>
                                <TooltipContent>Mark destroyed</TooltipContent>
                              </Tooltip>
                            )}
                            <Tooltip>
                              <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => confirm("Delete GMO?", `Remove ${g.organism_name} from this plasmid?`, () => handleDeleteGmo(g.id))} />}>
                                <X className="h-3.5 w-3.5 text-muted-foreground" />
                              </TooltipTrigger>
                                <TooltipContent>Delete GMO</TooltipContent>
                              </Tooltip>
                            </div>
                          </div>
                          <div className="text-xs text-muted-foreground mt-2 font-mono">
                            {fmtSummary(g.summary)}
                          </div>
                        </div>
                      ))}
                      {selected.gmos.length === 0 && <p className="text-sm text-muted-foreground">No GMOs</p>}
                    </div>
                  </div>
                  <Separator />
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <Label className="text-xs uppercase tracking-wider text-muted-foreground">Attachments</Label>
                      <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={() => attachFileRef.current?.click()}>
                        <Upload className="h-3 w-3" /> Upload
                      </Button>
                    </div>
                    <div className="space-y-1.5">
                      {selected.attachments.map((a) => (
                        <div key={a.id} className="flex items-center gap-2 px-3 py-2 bg-muted rounded-md text-sm">
                          <Paperclip className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="flex-1 font-mono truncate">{a.filename || "file"}</span>
                          <Tooltip>
                            <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => handleAttachDownload(a.id)} />}>
                              <Download className="h-3.5 w-3.5" />
                            </TooltipTrigger>
                            <TooltipContent>Download</TooltipContent>
                          </Tooltip>
                          <Tooltip>
                            <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => confirm("Delete attachment?", `Remove "${a.filename || "file"}"?`, () => handleAttachDelete(a.id))} />}>
                              <X className="h-3.5 w-3.5 text-muted-foreground" />
                            </TooltipTrigger>
                            <TooltipContent>Delete attachment</TooltipContent>
                          </Tooltip>
                        </div>
                      ))}
                      {selected.attachments.length === 0 && <p className="text-sm text-muted-foreground">No attachments</p>}
                    </div>
                  </div>
                </div>

                {/* Col 3 — GenBank (full column) */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <Label className="text-xs uppercase tracking-wider text-muted-foreground">GenBank File</Label>
                    <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={() => gbFileRef.current?.click()}>
                      <Upload className="h-3 w-3" /> Upload
                    </Button>
                  </div>
                  {selected.genbank_filename ? (
                    <>
                      <div className="flex items-center gap-2 px-3 py-2 bg-muted rounded-md text-sm mb-3">
                        <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span className="flex-1 font-mono truncate">{selected.genbank_filename}</span>
                        <Tooltip>
                          <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={handleGbDownload} />}>
                            <Download className="h-3.5 w-3.5" />
                          </TooltipTrigger>
                          <TooltipContent>Download</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => confirm("Remove GenBank file?", `Delete "${selected.genbank_filename}" from this plasmid?`, handleGbDelete)} />}>
                            <X className="h-3.5 w-3.5 text-muted-foreground" />
                          </TooltipTrigger>
                          <TooltipContent>Remove file</TooltipContent>
                        </Tooltip>
                      </div>
                      {parsedGb ? (
                        <PlasmidMap record={parsedGb} />
                      ) : (
                        <p className="text-xs text-muted-foreground">Could not parse GenBank file for visualisation.</p>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">No GenBank file attached. Upload a .gb file to visualise the plasmid map.</p>
                  )}
                </div>

              </div>
            </div>
          </div>
        )}

        {/* ── Normal table + sheet view ── */}
        {!expanded && <>

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Plasmids</h1>
            <p className="text-sm text-muted-foreground mt-1">{data.length} plasmid{data.length !== 1 ? "s" : ""} in database</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="gap-1.5" onClick={handleExport}>
              <DownloadIcon className="h-3.5 w-3.5" />
              {selectedIds.size > 0 ? `Export ${selectedIds.size}` : "Export CSV"}
            </Button>
            <Button size="sm" className="gap-1.5" onClick={handleCreate}>
              <Plus className="h-4 w-4" /> New Plasmid
            </Button>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search plasmids…" value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9 pr-9" />
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
                <SortableHead label="Name" sortKey="name" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} />
                <SortableHead label="Alias" sortKey="alias" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} className="hidden md:table-cell" />
                <SortableHead label="Status" sortKey="status_id" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} className="w-28" />
                <SortableHead label="RG" sortKey="target_risk_group" activeSortKey={sortKey} sortDir={sortDir} onSort={toggle} className="hidden lg:table-cell w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {paged.map((p) => {
                const status = STATUS_MAP[p.status_id ?? 4];
                return (
                  <TableRow key={p.id} className={`cursor-pointer ${selected?.id === p.id ? "bg-accent" : ""}`} onClick={() => openPlasmid(p)}>
                    <TableCell className="w-10 px-3" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" checked={selectedIds.has(p.id)} onChange={() => toggleId(p.id)} className="accent-primary" />
                    </TableCell>
                    <TableCell className="font-mono text-xs">{p.id}</TableCell>
                    <TableCell className="font-medium">{p.name}</TableCell>
                    <TableCell className="hidden md:table-cell text-muted-foreground truncate max-w-64">{p.alias || "—"}</TableCell>
                    <TableCell><Badge variant="outline" className={status.className}>{status.label}</Badge></TableCell>
                    <TableCell className="hidden lg:table-cell">{p.target_risk_group ?? 1}</TableCell>
                  </TableRow>
                );
              })}
              {data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                    {search ? "No matching plasmids." : 'No plasmids yet. Click "New Plasmid" to create one.'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        <Pagination page={page} pageCount={pageCount} onPageChange={setPage} />

        {/* Detail Sheet */}
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetContent className="w-[92vw] sm:max-w-2xl lg:max-w-4xl overflow-y-auto">
            {detailLoading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : selected ? (
              <>
                <SheetHeader>
                  <SheetTitle className="flex items-center gap-2">
                    {selected.name}
                    <Badge variant="outline" className={`ml-1 ${STATUS_MAP[selected.status_id ?? 4].className}`}>
                      {STATUS_MAP[selected.status_id ?? 4].label}
                    </Badge>
                    <Tooltip>
                      <TooltipTrigger render={
                        <Button variant="ghost" size="icon-sm" className="ml-auto mr-7"
                          onClick={() => { setExpanded(true); setSheetOpen(false); }} />
                      }>
                        <Maximize2 className="h-4 w-4" />
                      </TooltipTrigger>
                      <TooltipContent>Expand to full page</TooltipContent>
                    </Tooltip>
                  </SheetTitle>
                </SheetHeader>

                {/* Workflow progress banner */}
                {(() => {
                  const cassetteDone = selected.cassettes.some(c => c.content && c.content !== "Empty");
                  const gmosDone = selected.gmos.length > 0;
                  return (
                    <div className="mx-4 mt-3 mb-0 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2.5">GMO Registration Workflow</p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cassetteDone ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-400" : "bg-muted text-muted-foreground"}`}>
                          {cassetteDone
                            ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                            : <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border border-current text-[9px] font-bold">1</span>}
                          Cassette
                        </div>
                        <span className="text-muted-foreground/40 text-xs">›</span>
                        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${gmosDone ? "bg-emerald-500/12 text-emerald-700 dark:text-emerald-400" : "bg-muted text-muted-foreground"}`}>
                          {gmosDone
                            ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                            : <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border border-current text-[9px] font-bold">2</span>}
                          GMOs{gmosDone ? ` (${selected.gmos.length})` : ""}
                        </div>
                        <span className="text-muted-foreground/40 text-xs">›</span>
                        <button
                          onClick={() => setFormblattOpen(true)}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-primary/40 bg-primary/8 text-xs font-medium text-primary hover:bg-primary/15 transition-colors"
                        >
                          <ClipboardList className="h-3.5 w-3.5 shrink-0" />
                          Formblatt Z
                        </button>
                      </div>
                    </div>
                  );
                })()}

                <div className="space-y-5 px-4 pb-4">
                  {/* Name / Alias */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="p-name">Name</Label>
                      <Input id="p-name" value={selected.name || ""} onChange={(e) => setSelected({ ...selected, name: e.target.value })} onBlur={(e) => handleUpdate("name", e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="p-alias">Alias</Label>
                      <Input id="p-alias" value={selected.alias || ""} onChange={(e) => setSelected({ ...selected, alias: e.target.value })} onBlur={(e) => handleUpdate("alias", e.target.value)} />
                    </div>
                  </div>

                  {/* Backbone / Marker */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="p-backbone">Backbone Vector</Label>
                      <Input id="p-backbone" value={selected.backbone_vector || ""} onChange={(e) => setSelected({ ...selected, backbone_vector: e.target.value })} onBlur={(e) => handleUpdate("backbone_vector", e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="p-marker">Marker</Label>
                      <Input id="p-marker" value={selected.marker || ""} onChange={(e) => setSelected({ ...selected, marker: e.target.value })} onBlur={(e) => handleUpdate("marker", e.target.value)} />
                    </div>
                  </div>

                  {/* Status / RG / Clone */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-1.5">
                      <Label>Status</Label>
                      <Select value={String(selected.status_id ?? 4)} onValueChange={(v) => { const val = Number(v ?? 4); setSelected({ ...selected, status_id: val }); handleUpdate("status_id", val); }}>
                        <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1">Complete</SelectItem>
                          <SelectItem value="2">In Progress</SelectItem>
                          <SelectItem value="3">Abandoned</SelectItem>
                          <SelectItem value="4">Planned</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="p-rg">Target RG</Label>
                      <Input id="p-rg" type="number" min={1} max={4} value={selected.target_risk_group ?? 1} onChange={(e) => setSelected({ ...selected, target_risk_group: Number(e.target.value) })} onBlur={(e) => handleUpdate("target_risk_group", Number(e.target.value))} />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="p-clone">Clone</Label>
                      <Input id="p-clone" value={selected.clone || ""} onChange={(e) => setSelected({ ...selected, clone: e.target.value })} onBlur={(e) => handleUpdate("clone", e.target.value)} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <Label>Organism Selector</Label>
                      <Select
                        value={selected.target_organism_selection_id ? String(selected.target_organism_selection_id) : "none"}
                        onValueChange={(v) => {
                          const nextValue = v === "none" ? null : Number(v);
                          setSelected({ ...selected, target_organism_selection_id: nextValue });
                          handleUpdate("target_organism_selection_id", nextValue);
                        }}
                      >
                        <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">None</SelectItem>
                          {targetOrganisms
                            .filter((t) => t.organism_name)
                            .map((t) => (
                              <SelectItem key={t.id} value={String(t.id)}>{t.organism_name}</SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="p-recorded-on">Entry Date</Label>
                      <Input
                        id="p-recorded-on"
                        type="date"
                        value={selected.recorded_on || ""}
                        onChange={(e) => setSelected({ ...selected, recorded_on: e.target.value || null })}
                        onBlur={(e) => handleUpdate("recorded_on", e.target.value || null)}
                      />
                    </div>
                  </div>

                  {/* Purpose */}
                  <div className="space-y-1.5">
                    <Label htmlFor="p-purpose">Purpose</Label>
                    <Textarea id="p-purpose" rows={2} value={selected.purpose || ""} onChange={(e) => setSelected({ ...selected, purpose: e.target.value })} onBlur={(e) => handleUpdate("purpose", e.target.value)} />
                  </div>

                  {/* Summary */}
                  <div className="space-y-1.5">
                    <Label htmlFor="p-summary">Cloning Summary</Label>
                    <Textarea id="p-summary" rows={3} value={selected.summary || ""} onChange={(e) => setSelected({ ...selected, summary: e.target.value })} onBlur={(e) => handleUpdate("summary", e.target.value)} />
                  </div>

                  {/* Cassettes */}
                  <div>
                    <Separator className="mb-4" />
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-xs uppercase tracking-wider text-muted-foreground">Cassettes</Label>
                      <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={handleAddCassette}>
                        <Plus className="h-3 w-3" /> Add
                      </Button>
                    </div>
                    <div className="space-y-1.5">
                      {selected.cassettes.map((c) => (
                        <div key={c.id} className="flex items-center gap-1.5">
                          {editingCassette === c.id ? (
                            <>
                              <Input className="h-8 font-mono text-sm flex-1" value={cassetteValue} onChange={(e) => setCassetteValue(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") handleSaveCassette(c.id); if (e.key === "Escape") setEditingCassette(null); }} autoFocus />
                              <Tooltip>
                                <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => handleSaveCassette(c.id)} />}>
                                  <ChevronDown className="h-3.5 w-3.5" />
                                </TooltipTrigger>
                                <TooltipContent>Save</TooltipContent>
                              </Tooltip>
                            </>
                          ) : (
                            <>
                              <div className="flex-1 px-3 py-1.5 bg-muted rounded-md text-sm font-mono cursor-pointer hover:bg-muted/80" onClick={(e) => { e.stopPropagation(); setEditingCassette(c.id); setCassetteValue(c.content || ""); }}>
                                {c.content || "Empty"}
                              </div>
                              <Tooltip>
                                <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => confirm("Delete cassette?", `Remove "${c.content || "Empty"}"?`, () => handleDeleteCassette(c.id))} />}>
                                  <X className="h-3.5 w-3.5 text-muted-foreground" />
                                </TooltipTrigger>
                                <TooltipContent>Remove cassette</TooltipContent>
                              </Tooltip>
                            </>
                          )}
                        </div>
                      ))}
                      {selected.cassettes.length === 0 && <p className="text-sm text-muted-foreground">No cassettes</p>}
                    </div>
                  </div>

                  {/* GMOs */}
                  <div>
                    <Separator className="mb-4" />
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-xs uppercase tracking-wider text-muted-foreground">GMOs</Label>
                    </div>
                    <div className="grid grid-cols-1 gap-2 mb-2 md:grid-cols-[minmax(0,1.4fr)_92px_minmax(0,1fr)]">
                      <Select value={newGmoOrganism || undefined} onValueChange={(value) => setNewGmoOrganism(value ?? "")}>
                        <SelectTrigger className="w-full"><SelectValue placeholder="Organism…" /></SelectTrigger>
                        <SelectContent>
                          {targetOrganisms
                            .filter((t) => t.organism_name)
                            .map((t) => (
                              <SelectItem key={t.id} value={t.organism_name || ""}>{t.organism_name}</SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                      <Input type="number" min={1} max={4} value={newGmoTargetRiskGroup} onChange={(e) => setNewGmoTargetRiskGroup(Number(e.target.value) || 1)} placeholder="RG" />
                      <Input value={newGmoApproval} onChange={(e) => setNewGmoApproval(e.target.value)} placeholder="Approval" />
                    </div>
                    <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2 mb-2">
                      <Input type="date" value={newGmoCreatedOn} onChange={(e) => setNewGmoCreatedOn(e.target.value)} />
                      <Button variant="outline" size="sm" className="h-9" onClick={handleAddGmo}>Add</Button>
                    </div>
                    <div className="space-y-1.5">
                      {selected.gmos.map((g) => (
                        <div key={g.id} className="px-3 py-3 bg-muted rounded-md text-sm">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="font-medium">{g.organism_name}</span>
                            {g.destroyed_on && <Badge variant="destructive" className="text-[10px]">Destroyed</Badge>}
                          </div>
                          <div className="grid grid-cols-1 gap-2 mb-2 md:grid-cols-[minmax(0,1.2fr)_92px_minmax(0,1fr)]">
                            <Input value={g.organism_name || ""} onChange={(e) => setSelected({ ...selected, gmos: selected.gmos.map((item) => item.id === g.id ? { ...item, organism_name: e.target.value } : item) })} onBlur={(e) => handleUpdateGmo(g.id, { organism_name: e.target.value || null })} />
                            <Input type="number" min={1} max={4} value={g.target_risk_group ?? 1} onChange={(e) => setSelected({ ...selected, gmos: selected.gmos.map((item) => item.id === g.id ? { ...item, target_risk_group: Number(e.target.value) || 1 } : item) })} onBlur={(e) => handleUpdateGmo(g.id, { target_risk_group: Number(e.target.value) || 1 })} />
                            <Input value={g.approval || ""} onChange={(e) => setSelected({ ...selected, gmos: selected.gmos.map((item) => item.id === g.id ? { ...item, approval: e.target.value } : item) })} onBlur={(e) => handleUpdateGmo(g.id, { approval: e.target.value || null })} />
                          </div>
                          <div className="grid grid-cols-1 gap-2 mb-2 md:grid-cols-2">
                            <Input type="date" value={g.created_on || ""} onChange={(e) => setSelected({ ...selected, gmos: selected.gmos.map((item) => item.id === g.id ? { ...item, created_on: e.target.value || null } : item) })} onBlur={(e) => handleUpdateGmo(g.id, { created_on: e.target.value || null })} />
                            <Input type="date" value={g.destroyed_on || ""} onChange={(e) => setSelected({ ...selected, gmos: selected.gmos.map((item) => item.id === g.id ? { ...item, destroyed_on: e.target.value || null } : item) })} onBlur={(e) => handleUpdateGmo(g.id, { destroyed_on: e.target.value || null })} />
                          </div>
                          <div className="flex items-center gap-0.5 ml-2">
                            {!g.destroyed_on && (
                              <Tooltip>
                                <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => confirm("Mark GMO as destroyed?", `Set today as destruction date for ${g.organism_name}.`, () => handleDestroyGmo(g.id))} />}>
                                  <Trash2 className="h-3.5 w-3.5 text-orange-500" />
                                </TooltipTrigger>
                                <TooltipContent>Mark destroyed</TooltipContent>
                              </Tooltip>
                            )}
                            <Tooltip>
                              <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => confirm("Delete GMO?", `Remove ${g.organism_name} from this plasmid?`, () => handleDeleteGmo(g.id))} />}>
                                <X className="h-3.5 w-3.5 text-muted-foreground" />
                              </TooltipTrigger>
                                <TooltipContent>Delete GMO</TooltipContent>
                              </Tooltip>
                          </div>
                          <div className="text-xs text-muted-foreground mt-2 font-mono break-words">
                            {fmtSummary(g.summary)}
                          </div>
                        </div>
                      ))}
                      {selected.gmos.length === 0 && <p className="text-sm text-muted-foreground">No GMOs</p>}
                    </div>
                  </div>

                  {/* GenBank */}
                  <div>
                    <Separator className="mb-4" />
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-xs uppercase tracking-wider text-muted-foreground">GenBank File</Label>
                      <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={() => gbFileRef.current?.click()}>
                        <Upload className="h-3 w-3" /> Upload
                      </Button>
                      <input ref={gbFileRef} type="file" accept=".gb,.gbk,.genbank" className="hidden" onChange={handleGbUpload} />
                    </div>
                    {selected.genbank_filename ? (
                      <>
                        <div className="flex items-center gap-2 px-3 py-2 bg-muted rounded-md text-sm mb-3">
                          <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="flex-1 font-mono truncate">{selected.genbank_filename}</span>
                          <Tooltip>
                            <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={handleGbDownload} />}>
                              <Download className="h-3.5 w-3.5" />
                            </TooltipTrigger>
                            <TooltipContent>Download</TooltipContent>
                          </Tooltip>
                          <Tooltip>
                            <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => confirm("Remove GenBank file?", `Delete "${selected.genbank_filename}" from this plasmid?`, handleGbDelete)} />}>
                              <X className="h-3.5 w-3.5 text-muted-foreground" />
                            </TooltipTrigger>
                            <TooltipContent>Remove file</TooltipContent>
                          </Tooltip>
                        </div>
                        {parsedGb ? (
                          <PlasmidMap record={parsedGb} />
                        ) : (
                          <p className="text-xs text-muted-foreground">Could not parse GenBank file for visualisation.</p>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">No GenBank file</p>
                    )}
                  </div>

                  {/* Attachments */}
                  <div>
                    <Separator className="mb-4" />
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-xs uppercase tracking-wider text-muted-foreground">Attachments</Label>
                      <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={() => attachFileRef.current?.click()}>
                        <Upload className="h-3 w-3" /> Upload
                      </Button>
                      <input ref={attachFileRef} type="file" className="hidden" onChange={handleAttachUpload} />
                    </div>
                    <div className="space-y-1.5">
                      {selected.attachments.map((a) => (
                        <div key={a.id} className="flex items-center gap-2 px-3 py-2 bg-muted rounded-md text-sm">
                          <Paperclip className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="flex-1 font-mono truncate">{a.filename || "file"}</span>
                          <Tooltip>
                            <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => handleAttachDownload(a.id)} />}>
                              <Download className="h-3.5 w-3.5" />
                            </TooltipTrigger>
                            <TooltipContent>Download</TooltipContent>
                          </Tooltip>
                          <Tooltip>
                            <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => confirm("Delete attachment?", `Remove "${a.filename || "file"}"?`, () => handleAttachDelete(a.id))} />}>
                              <X className="h-3.5 w-3.5 text-muted-foreground" />
                            </TooltipTrigger>
                            <TooltipContent>Delete attachment</TooltipContent>
                          </Tooltip>
                        </div>
                      ))}
                      {selected.attachments.length === 0 && <p className="text-sm text-muted-foreground">No attachments</p>}
                    </div>
                  </div>

                  {/* Actions */}
                  <Separator />
                  <div className="flex gap-2 flex-wrap">
                    <Tooltip>
                      <TooltipTrigger render={
                        <Button variant="outline" size="sm" className="gap-1.5" onClick={handleDuplicate} />
                      }>
                        <Copy className="h-3.5 w-3.5" /> Duplicate
                      </TooltipTrigger>
                      <TooltipContent>Create a copy of this plasmid</TooltipContent>
                    </Tooltip>
                    <Button variant="destructive" size="sm" className="gap-1.5"
                      onClick={() => confirm("Delete plasmid?", `Permanently delete "${selected.name}"? This will also remove all GMOs and attachments.`, handleDelete)}>
                      <Trash2 className="h-3.5 w-3.5" /> Delete Plasmid
                    </Button>
                  </div>
                </div>
              </>
            ) : null}
          </SheetContent>
        </Sheet>

        </> /* end !expanded */}

        <ConfirmDialog open={confirmOpen} onOpenChange={setConfirmOpen} title={confirmAction.title} description={confirmAction.description} onConfirm={confirmAction.onConfirm} />
        <ConfirmDialog open={bulkConfirmOpen} onOpenChange={setBulkConfirmOpen} title={`Delete ${selectedIds.size} plasmids?`} description="This will permanently delete all selected plasmids and their associated data." onConfirm={handleBulkDelete} />
        <FormblattDialog open={formblattOpen} onOpenChange={setFormblattOpen} />
      </div>
    </TooltipProvider>
  );
}
