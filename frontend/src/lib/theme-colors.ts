export interface ColorPreset {
  id: string;
  name: string;
  hue: number;
  chroma: number;
  lightness: number;
}

export const COLOR_PRESETS: readonly ColorPreset[] = [
  { id: "julia-green", name: "Julia Green", hue: 134.13, chroma: 0.212, lightness: 0.781 },
  { id: "mint", name: "Mint", hue: 155, chroma: 0.15, lightness: 0.82 },
  { id: "teal", name: "Teal", hue: 190, chroma: 0.18, lightness: 0.68 },
  { id: "lagoon", name: "Lagoon", hue: 205, chroma: 0.17, lightness: 0.67 },
  { id: "sapphire", name: "Sapphire", hue: 230, chroma: 0.18, lightness: 0.6 },
  { id: "cobalt", name: "Cobalt", hue: 255, chroma: 0.19, lightness: 0.59 },
  { id: "orchid", name: "Orchid", hue: 315, chroma: 0.19, lightness: 0.68 },
  { id: "berry", name: "Berry", hue: 350, chroma: 0.19, lightness: 0.62 },
  { id: "rose", name: "Rose", hue: 8, chroma: 0.17, lightness: 0.75 },
  { id: "coral", name: "Coral", hue: 30, chroma: 0.2, lightness: 0.71 },
  { id: "amber", name: "Amber", hue: 75, chroma: 0.18, lightness: 0.78 },
  { id: "graphite", name: "Graphite", hue: 255, chroma: 0.04, lightness: 0.55 },
] as const;

export const DEFAULT_PRESET_ID = COLOR_PRESETS[0].id;

export function applyAccent(hue: number, chroma: number) {
  const root = document.documentElement;
  root.style.setProperty("--accent-hue", String(hue));
  root.style.setProperty("--accent-chroma", String(chroma));
}

export function swatchColor(preset: ColorPreset) {
  return `oklch(${preset.lightness} ${preset.chroma} ${preset.hue})`;
}
