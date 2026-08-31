"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";

const STORAGE_KEY = "wheredox.theme";

/** The theme is applied to <html> before paint by a script in the layout; this only flips it. */
export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark");
  }, []);

  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Remembering the preference is a nicety, not a requirement.
    }
  };

  return (
    <button
      onClick={toggle}
      title={theme === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
      aria-label={theme === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
      className="shrink-0 rounded-lg border border-edge px-2.5 py-1.5 text-xs text-ink-soft hover:bg-panel-soft"
    >
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}
