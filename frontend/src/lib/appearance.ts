/**
 * Appearance helpers — apply DB-stored appearance settings to the DOM.
 *
 * All preferences live in the SQLite app_settings row so they are consistent
 * across browser windows and survive database export/import.
 *
 * DB fields used:
 *   font_size        0 = small (14 px) | 1 = medium (16 px) | 2 = large (18 px)
 *   scale            0 = compact | 1 = comfortable | 2 = spacious
 *   horizontal_layout  0 = stacked | 1 = side-by-side (future use)
 *   date_format      "eu" (DD.MM.YYYY) | "iso" (YYYY-MM-DD)
 *   reduce_motion    0 | 1
 *   mono_genbank     0 | 1
 */

import type { Settings } from "@/api/client";

// ── Module-level cache (set once on startup, updated on settings change) ──────

let _dateFormat: string = "eu";
let _monoGenbank: boolean = false;

// ── Apply all appearance from a Settings object ───────────────────────────────

const FONT_SIZES = [14, 16, 18];
const DENSITIES = ["compact", "comfortable", "spacious"];

export function applyAllAppearance(s: Partial<Settings>) {
  const el = document.documentElement;

  // Font size
  const px = FONT_SIZES[s.font_size ?? 1] ?? 16;
  el.style.fontSize = `${px}px`;

  // Density
  const density = DENSITIES[Math.round(s.scale ?? 1)] ?? "comfortable";
  el.setAttribute("data-density", density);

  // Layout
  el.setAttribute("data-layout", s.horizontal_layout ? "horizontal" : "vertical");

  // Reduce motion
  if (s.reduce_motion) {
    el.setAttribute("data-reduce-motion", "");
  } else {
    el.removeAttribute("data-reduce-motion");
  }

  // Cache for helpers
  _dateFormat = s.date_format ?? "eu";
  _monoGenbank = !!s.mono_genbank;
}

// ── Helpers for other pages ───────────────────────────────────────────────────

export function formatDate(isoDate: string | null | undefined): string {
  if (!isoDate) return "";
  const parts = isoDate.slice(0, 10).split("-");
  if (parts.length !== 3) return isoDate;
  const [y, m, d] = parts;
  return _dateFormat === "eu" ? `${d}.${m}.${y}` : `${y}-${m}-${d}`;
}

export function isMonoGenbank(): boolean {
  return _monoGenbank;
}
