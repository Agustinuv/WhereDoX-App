"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Person } from "@/lib/types";

const STORAGE_KEY = "wheredox.viewer";

interface ViewerContextValue {
  people: Person[];
  viewer: Person | null;
  viewerId: number | null;
  /** False until the stored identity has been read, so pages don't act on a null viewer. */
  ready: boolean;
  setViewerId: (personId: number | null) => void;
  refreshPeople: () => Promise<void>;
}

const ViewerContext = createContext<ViewerContextValue | null>(null);

/**
 * The mocked identity, shared across routes.
 *
 * There is no session: this is just "who am I pretending to be", kept in localStorage so a
 * page reload during a demo does not lose it. The backend never sees anything but the
 * explicit person_id that the API client sends.
 */
export function ViewerProvider({ children }: { children: React.ReactNode }) {
  const [people, setPeople] = useState<Person[]>([]);
  const [viewerId, setViewerIdState] = useState<number | null>(null);
  const [ready, setReady] = useState(false);

  const refreshPeople = useCallback(async () => {
    setPeople(await api.listPeople());
  }, []);

  useEffect(() => {
    let stored: number | null = null;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      stored = raw === null ? null : Number(raw);
    } catch {
      // Private mode or blocked storage: fall back to asking again.
    }
    if (stored !== null && !Number.isNaN(stored)) setViewerIdState(stored);
    refreshPeople().finally(() => setReady(true));
  }, [refreshPeople]);

  const setViewerId = useCallback((personId: number | null) => {
    setViewerIdState(personId);
    try {
      if (personId === null) localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, String(personId));
    } catch {
      // Not being able to remember the choice is not worth failing over.
    }
  }, []);

  const viewer = people.find((person) => person.id === viewerId) ?? null;

  return (
    <ViewerContext.Provider
      value={{ people, viewer, viewerId, ready, setViewerId, refreshPeople }}
    >
      {children}
    </ViewerContext.Provider>
  );
}

export function useViewer() {
  const value = useContext(ViewerContext);
  if (value === null) throw new Error("useViewer must be used inside ViewerProvider");
  return value;
}
