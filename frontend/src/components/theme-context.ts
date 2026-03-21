import { createContext, useContext } from "react";

export type Theme = "dark" | "light" | "system";

export type ThemeProviderState = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
};

export const ThemeProviderContext = createContext<ThemeProviderState>({
  theme: "system",
  setTheme: () => null,
});

export function useTheme() {
  return useContext(ThemeProviderContext);
}
