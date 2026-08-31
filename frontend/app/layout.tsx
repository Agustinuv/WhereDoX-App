import type { Metadata } from "next";

import { ViewerProvider } from "@/components/ViewerProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "WhereDoX",
  description: "Coordinador de juntas de juegos de mesa",
};

// Runs before first paint so a light-theme reload never flashes the dark palette.
const THEME_BOOTSTRAP = `
try {
  document.documentElement.dataset.theme =
    localStorage.getItem("wheredox.theme") === "light" ? "light" : "dark";
} catch (error) {
  document.documentElement.dataset.theme = "dark";
}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" data-theme="dark">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
      </head>
      <body className="h-full">
        <ViewerProvider>{children}</ViewerProvider>
      </body>
    </html>
  );
}
