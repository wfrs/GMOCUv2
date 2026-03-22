import { useEffect, useState } from "react";
import { Dna, FlaskConical, Bug, ArrowUpRight } from "lucide-react";
import { activityLog, type ActivityLog } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/appearance";

const FILTERS = [
  { label: "All", value: undefined },
  { label: "Plasmids", value: "plasmid" },
  { label: "Features", value: "feature" },
  { label: "Organisms", value: "organism" },
] as const;

type FilterValue = (typeof FILTERS)[number]["value"];

const ACTION_BADGE: Record<string, string> = {
  create:    "bg-emerald-500/12 text-emerald-700 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-700/40",
  duplicate: "bg-violet-500/12 text-violet-700 dark:text-violet-400 border-violet-200/60 dark:border-violet-700/40",
  update:    "bg-blue-500/12 text-blue-700 dark:text-blue-400 border-blue-200/60 dark:border-blue-700/40",
  delete:    "bg-red-500/12 text-red-700 dark:text-red-400 border-red-200/60 dark:border-red-700/40",
};

const ACTION_LABEL: Record<string, string> = {
  create:    "Created",
  duplicate: "Duplicated",
  update:    "Updated",
  delete:    "Deleted",
};

function EntityIcon({ type }: { type: string }) {
  const cls = "h-4 w-4 shrink-0 text-muted-foreground";
  if (type === "plasmid") return <Dna className={cls} />;
  if (type === "feature") return <FlaskConical className={cls} />;
  return <Bug className={cls} />;
}

function formatTime(ts: string | null): string {
  if (!ts) return "";
  const d = new Date(ts.includes("T") ? ts : ts.replace(" ", "T") + "Z");
  const now = new Date();
  const todayStr = now.toDateString();
  const dStr = d.toDateString();
  if (dStr === todayStr) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (dStr === yesterday.toDateString()) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function groupLabel(ts: string | null): string {
  if (!ts) return "Unknown";
  const d = new Date(ts.includes("T") ? ts : ts.replace(" ", "T") + "Z");
  const now = new Date();
  const todayStr = now.toDateString();
  const dStr = d.toDateString();
  if (dStr === todayStr) return "Today";
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (dStr === yesterday.toDateString()) return "Yesterday";
  return formatDate(d.toISOString().slice(0, 10));
}

type EntityType = "plasmid" | "feature" | "organism";

interface ActivityPageProps {
  onNavigate?: (type: EntityType, id: number) => void;
}

export default function ActivityPage({ onNavigate }: ActivityPageProps) {
  const [data, setData] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterValue>(undefined);

  useEffect(() => {
    activityLog.list(filter)
      .then((rows) => { setData(rows); setLoading(false); })
      .catch(() => setLoading(false));
  }, [filter]);

  // Group entries by date label
  const groups: { label: string; items: ActivityLog[] }[] = [];
  for (const item of data) {
    const label = groupLabel(item.timestamp);
    const last = groups[groups.length - 1];
    if (last && last.label === label) {
      last.items.push(item);
    } else {
      groups.push({ label, items: [item] });
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Activity</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {loading ? "Loading…" : `${data.length} event${data.length !== 1 ? "s" : ""}`}
          </p>
        </div>
      </div>

      {/* Filter pills */}
      <div className="flex items-center gap-2 mb-5">
        {FILTERS.map((f) => (
          <button
            key={String(f.value)}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors border ${
              filter === f.value
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-transparent text-muted-foreground border-border hover:bg-muted hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32 text-muted-foreground">Loading…</div>
        ) : data.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
            No activity yet. Create, edit, or delete a plasmid, feature, or organism to see events here.
          </div>
        ) : (
          <div className="space-y-6">
            {groups.map((group) => (
              <div key={group.label}>
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {group.label}
                  </span>
                  <div className="flex-1 h-px bg-border" />
                </div>
                <div className="space-y-1">
                  {group.items.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <EntityIcon type={item.entity_type} />
                      <Badge
                        variant="outline"
                        className={`text-[10px] px-1.5 py-0 shrink-0 ${ACTION_BADGE[item.action] ?? ""}`}
                      >
                        {ACTION_LABEL[item.action] ?? item.action}
                      </Badge>
                      {item.action !== "delete" && onNavigate ? (
                        <button
                          className="group inline-flex items-center gap-1 font-medium text-sm text-primary hover:underline text-left cursor-pointer truncate"
                          onClick={() => onNavigate(item.entity_type as EntityType, item.entity_id)}
                        >
                          <span className="truncate">{item.entity_name ?? "—"}</span>
                          <ArrowUpRight className="h-3.5 w-3.5 shrink-0 opacity-50 group-hover:opacity-100 transition-opacity" />
                        </button>
                      ) : (
                        <span className="font-medium text-sm truncate">{item.entity_name ?? "—"}</span>
                      )}
                      {item.action === "update" && item.field && (
                        <span className="text-xs text-muted-foreground font-mono truncate">
                          {item.field}: {item.old_value ?? "—"} → {item.new_value ?? "—"}
                        </span>
                      )}
                      {item.action === "duplicate" && item.old_value && (
                        <span className="text-xs text-muted-foreground truncate">
                          from {item.old_value}
                        </span>
                      )}
                      <span className="ml-auto text-xs text-muted-foreground shrink-0 tabular-nums">
                        {formatTime(item.timestamp)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
