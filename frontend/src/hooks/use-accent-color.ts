import { useState, useEffect } from "react";
import {
  COLOR_PRESETS,
  DEFAULT_PRESET_ID,
  applyAccent,
  type ColorPreset,
} from "@/lib/theme-colors";

const STORAGE_KEY = "gmocu-accent-color";

export function useAccentColor() {
  const [presetId, setPresetId] = useState<string>(() => {
    return localStorage.getItem(STORAGE_KEY) ?? DEFAULT_PRESET_ID;
  });

  // Apply on mount and whenever presetId changes
  useEffect(() => {
    const preset = COLOR_PRESETS.find((p) => p.id === presetId) ?? COLOR_PRESETS[0];
    applyAccent(preset.hue, preset.chroma);
    localStorage.setItem(STORAGE_KEY, presetId);
  }, [presetId]);

  const activePreset: ColorPreset =
    COLOR_PRESETS.find((p) => p.id === presetId) ?? COLOR_PRESETS[0];

  return { presetId, setPresetId, activePreset };
}
