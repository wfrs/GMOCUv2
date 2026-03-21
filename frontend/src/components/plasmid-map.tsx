import { useState } from "react";
import type { GbRecord, GbFeature } from "@/lib/parse-genbank";

const RADIUS = 110;
const CX = 160;
const CY = 160;
const FEATURE_WIDTH = 14;
const INNER_R = RADIUS - FEATURE_WIDTH / 2;

function polarToXY(angle: number, r: number) {
  // angle in radians, 0 = top (12 o'clock)
  return {
    x: CX + r * Math.sin(angle),
    y: CY - r * Math.cos(angle),
  };
}

function arcPath(start: number, end: number, length: number, r: number, width: number): string {
  const a1 = (start / length) * 2 * Math.PI;
  const a2 = (end / length) * 2 * Math.PI;
  const largeArc = a2 - a1 > Math.PI ? 1 : 0;
  const outerR = r + width / 2;
  const innerR = r - width / 2;
  const p1 = polarToXY(a1, outerR);
  const p2 = polarToXY(a2, outerR);
  const p3 = polarToXY(a2, innerR);
  const p4 = polarToXY(a1, innerR);
  return [
    `M ${p1.x} ${p1.y}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${p2.x} ${p2.y}`,
    `L ${p3.x} ${p3.y}`,
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${p4.x} ${p4.y}`,
    "Z",
  ].join(" ");
}

function labelPos(start: number, end: number, length: number, r: number) {
  const mid = ((start + end) / 2 / length) * 2 * Math.PI;
  return polarToXY(mid, r + FEATURE_WIDTH + 10);
}

function tickMarks(length: number) {
  const ticks: { pos: number; major: boolean }[] = [];
  const step = Math.pow(10, Math.floor(Math.log10(length)) - 1);
  for (let i = 0; i < length; i += step) {
    ticks.push({ pos: i, major: i % (step * 5) === 0 });
  }
  return ticks;
}

interface PlasmidMapProps {
  record: GbRecord;
}

export function PlasmidMap({ record }: PlasmidMapProps) {
  const [hovered, setHovered] = useState<GbFeature | null>(null);

  const ticks = tickMarks(record.length);

  return (
    <div className="flex flex-col items-center gap-3">
      <svg viewBox="0 0 320 320" className="w-full">
        {/* Backbone circle */}
        <circle cx={CX} cy={CY} r={RADIUS} fill="none" stroke="currentColor" strokeWidth={2} className="text-border" />

        {/* Tick marks */}
        {ticks.map(({ pos, major }) => {
          const angle = (pos / record.length) * 2 * Math.PI;
          const rInner = RADIUS - (major ? 8 : 4);
          const rOuter = RADIUS + (major ? 8 : 4);
          const p1 = polarToXY(angle, rInner);
          const p2 = polarToXY(angle, rOuter);
          return (
            <line
              key={pos}
              x1={p1.x} y1={p1.y}
              x2={p2.x} y2={p2.y}
              stroke="currentColor"
              strokeWidth={major ? 1.5 : 0.75}
              className="text-muted-foreground/40"
            />
          );
        })}

        {/* Features */}
        {record.features.map((f, i) => {
          const isHovered = hovered === f;
          return (
            <path
              key={i}
              d={arcPath(f.start, f.end, record.length, INNER_R, FEATURE_WIDTH)}
              fill={f.color ?? "#94a3b8"}
              opacity={isHovered ? 1 : 0.85}
              stroke={isHovered ? "white" : "none"}
              strokeWidth={isHovered ? 1 : 0}
              className="cursor-pointer transition-opacity"
              onMouseEnter={() => setHovered(f)}
              onMouseLeave={() => setHovered(null)}
            />
          );
        })}

        {/* Labels for large features only */}
        {record.features
          .filter((f) => ((f.end - f.start) / record.length) > 0.04)
          .map((f, i) => {
            const pos = labelPos(f.start, f.end, record.length, INNER_R);
            const angle = ((f.start + f.end) / 2 / record.length) * 360;
            const anchor = (angle > 90 && angle < 270) ? "end" : "start";
            return (
              <text
                key={i}
                x={pos.x}
                y={pos.y}
                textAnchor={anchor}
                dominantBaseline="middle"
                fontSize={8}
                fill="currentColor"
                className="text-foreground pointer-events-none"
              >
                {f.label.length > 16 ? f.label.slice(0, 14) + "…" : f.label}
              </text>
            );
          })}

        {/* Centre label */}
        <text x={CX} y={CY - 8} textAnchor="middle" fontSize={11} fontWeight="600" fill="currentColor" className="text-foreground">
          {record.name}
        </text>
        <text x={CX} y={CY + 8} textAnchor="middle" fontSize={9} fill="currentColor" className="text-muted-foreground">
          {record.length.toLocaleString()} bp
        </text>
      </svg>

      {/* Info box — fixed size so both states take identical space */}
      <div className="w-full text-xs border rounded-md px-3 py-2 flex flex-col justify-center gap-0.5 h-[52px]">
        {hovered ? (
          <>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-sm shrink-0" style={{ background: hovered.color }} />
              <span className="font-medium truncate">{hovered.label}</span>
              <span className="text-muted-foreground shrink-0">{hovered.type}</span>
            </div>
            <div className="text-muted-foreground">
              {hovered.start}–{hovered.end} bp · {hovered.strand === 1 ? "+" : "−"} strand
            </div>
          </>
        ) : (
          <p className="text-muted-foreground/40 text-center">Hover over a feature to see details</p>
        )}
      </div>

      {/* Feature legend */}
      {record.features.length > 0 && (
        <div className="w-full max-h-[55vh] overflow-y-auto space-y-0.5">
          {record.features.map((f, i) => (
            <div
              key={i}
              className={`flex items-center gap-2 px-2 py-1 rounded text-xs cursor-default transition-colors ${
                hovered === f ? "bg-accent" : "hover:bg-muted"
              }`}
              onMouseEnter={() => setHovered(f)}
              onMouseLeave={() => setHovered(null)}
            >
              <span className="inline-block h-2.5 w-2.5 rounded-sm shrink-0" style={{ background: f.color }} />
              <span className="font-medium truncate flex-1">{f.label}</span>
              <span className="text-muted-foreground shrink-0">{f.type}</span>
              <span className="text-muted-foreground shrink-0 font-mono">{f.start}–{f.end}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
