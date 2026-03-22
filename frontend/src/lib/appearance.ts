/**
 * Appearance helpers — apply DB and localStorage appearance preferences to the DOM.
 *
 * DB fields (via Settings):
 *   font_size   0 = small (14 px) | 1 = medium (16 px) | 2 = large (18 px)
 *   scale       0 = compact        | 1 = comfortable    | 2 = spacious
 *   horizontal_layout  0 = stacked | 1 = side-by-side (reserved for future use)
 *
 * localStorage keys (purely frontend):
 *   gmocu-date-format   "eu" (DD.MM.YYYY) | "iso" (YYYY-MM-DD)
 *   gmocu-reduce-motion "1" | "0"
 *   gmocu-mono-genbank  "1" | "0"
 */

// ── Types ─────────────────────────────────────────────────────────────────────

export type DateFormat = "eu" | "iso";

export interface LocalAppearance {
  dateFormat: DateFormat;
  reduceMotion: boolean;
  monoGenbank: boolean;
}

// ── DB appearance (applied to <html>) ─────────────────────────────────────────

const FONT_SIZES = [14, 16, 18];
const DENSITIES = ["compact", "comfortable", "spacious"];

export function applyDbAppearance(fontSizeIdx: number | null, scaleIdx: number | null, horizontalLayout: number | null) {
  const el = document.documentElement;

  const px = FONT_SIZES[fontSizeIdx ?? 1] ?? 16;
  el.style.fontSize = `${px}px`;

  const density = DENSITIES[Math.round(scaleIdx ?? 1)] ?? "comfortable";
  el.setAttribute("data-density", density);

  el.setAttribute("data-layout", horizontalLayout ? "horizontal" : "vertical");
}

// ── localStorage appearance ───────────────────────────────────────────────────

const CHANGE_EVENT = "gmocu-appearance-change";

export function getLocalAppearance(): LocalAppearance {
  return {
    dateFormat: (localStorage.getItem("gmocu-date-format") as DateFormat) ?? "eu",
    reduceMotion: localStorage.getItem("gmocu-reduce-motion") === "1",
    monoGenbank: localStorage.getItem("gmocu-mono-genbank") === "1",
  };
}

export function setLocalAppearance(patch: Partial<LocalAppearance>) {
  if (patch.dateFormat !== undefined) localStorage.setItem("gmocu-date-format", patch.dateFormat);
  if (patch.reduceMotion !== undefined) localStorage.setItem("gmocu-reduce-motion", patch.reduceMotion ? "1" : "0");
  if (patch.monoGenbank !== undefined) localStorage.setItem("gmocu-mono-genbank", patch.monoGenbank ? "1" : "0");
  applyLocalAppearance();
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
}

export function applyLocalAppearance() {
  const el = document.documentElement;
  const { reduceMotion } = getLocalAppearance();
  if (reduceMotion) {
    el.setAttribute("data-reduce-motion", "");
  } else {
    el.removeAttribute("data-reduce-motion");
  }
}

export function onAppearanceChange(cb: () => void): () => void {
  window.addEventListener(CHANGE_EVENT, cb);
  return () => window.removeEventListener(CHANGE_EVENT, cb);
}

// ── Date formatting ───────────────────────────────────────────────────────────

export function formatDate(isoDate: string | null | undefined): string {
  if (!isoDate) return "";
  const fmt = getLocalAppearance().dateFormat;
  // Handle YYYY-MM-DD or ISO timestamp
  const parts = isoDate.slice(0, 10).split("-");
  if (parts.length !== 3) return isoDate;
  const [y, m, d] = parts;
  return fmt === "eu" ? `${d}.${m}.${y}` : `${y}-${m}-${d}`;
}
