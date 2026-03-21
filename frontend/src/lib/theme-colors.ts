export interface ColorPreset {
  id: string;
  name: string;
  hue: number;
  chroma: number;
}

export const COLOR_PRESETS: readonly ColorPreset[] = [
  { id: "fern", name: "Fern", hue: 134, chroma: 0.21 },
  { id: "cobalt", name: "Cobalt", hue: 255, chroma: 0.19 },
  { id: "amber", name: "Amber", hue: 75, chroma: 0.18 },
  { id: "coral", name: "Coral", hue: 30, chroma: 0.2 },
  { id: "berry", name: "Berry", hue: 350, chroma: 0.19 },
  { id: "teal", name: "Teal", hue: 190, chroma: 0.18 },
] as const;

export const DEFAULT_PRESET_ID = COLOR_PRESETS[0].id;

export function applyAccent(hue: number, chroma: number) {
  const root = document.documentElement;
  root.style.setProperty("--accent-hue", String(hue));
  root.style.setProperty("--accent-chroma", String(chroma));
}

export function swatchColor(preset: ColorPreset) {
  return `oklch(0.62 ${preset.chroma} ${preset.hue})`;
}
