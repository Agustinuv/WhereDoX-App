"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import PersonSwitcher from "@/components/PersonSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { useViewer } from "@/components/ViewerProvider";
import { ApiError, api } from "@/lib/api";
import type { Group } from "@/lib/types";

export default function Home() {
  const { viewer, viewerId, ready, refreshPeople, setViewerId } = useViewer();
  const [mine, setMine] = useState<Group[]>([]);
  const [all, setAll] = useState<Group[]>([]);
  const [newGroup, setNewGroup] = useState("");
  const [newPerson, setNewPerson] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const groups = await api.listGroups();
      setAll(groups);
      setMine(viewerId === null ? [] : await api.listGroupsForPerson(viewerId));
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo contactar la API. ¿Está corriendo el backend?",
      );
    }
  }, [viewerId]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await action();
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  };

  const others = all.filter((group) => !mine.some((joined) => joined.id === group.id));

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col gap-6 px-6 py-10">
      <header className="flex items-start gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-semibold">WhereDoX</h1>
          <p className="mt-1 text-sm text-ink-soft">
            ¿Dónde hacemos la próxima junta? Elige quién eres y entra a uno de tus grupos.
          </p>
        </div>
        <ThemeToggle />
      </header>

      <section className="rounded-2xl border border-edge bg-panel p-4">
        <PersonSwitcher />
        <p className="mt-2 text-[11px] leading-snug text-ink-faint">
          No hay login: el backend recibe este <code>person_id</code> explícito. Con Telegram
          saldría del <code>telegram_user_id</code>.
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const name = newPerson.trim();
            if (!name) return;
            setNewPerson("");
            run(async () => {
              const person = await api.createPerson(name);
              await refreshPeople();
              setViewerId(person.id);
            });
          }}
          className="mt-3"
        >
          <input
            value={newPerson}
            onChange={(event) => setNewPerson(event.target.value)}
            placeholder="Crear una persona nueva y pasar a ser ella…"
            disabled={busy}
            className="w-full rounded-lg border border-edge bg-panel-soft px-3 py-2 text-xs placeholder:text-ink-faint"
          />
        </form>
      </section>

      {error && (
        <p className="rounded-xl border border-danger-ink/30 bg-danger-soft px-4 py-3 text-sm text-danger-ink">
          ⚠️ {error}
        </p>
      )}

      {viewerId === null ? (
        <p className="text-sm text-ink-faint">
          Elige una persona arriba para ver los grupos a los que pertenece.
        </p>
      ) : (
        <>
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-faint">
              Grupos de {viewer?.name ?? "esta persona"}
            </h2>
            {mine.length === 0 ? (
              <p className="mt-2 text-sm text-ink-faint">
                Todavía no pertenece a ningún grupo. Únete a uno de abajo o crea el tuyo.
              </p>
            ) : (
              <ul className="mt-2 grid gap-2 sm:grid-cols-2">
                {mine.map((group) => (
                  <li key={group.id}>
                    <Link
                      href={`/groups/${group.id}`}
                      className="flex items-center gap-3 rounded-xl border border-edge bg-panel px-4 py-3 hover:bg-panel-soft"
                    >
                      <span className="text-lg">🎲</span>
                      <span className="min-w-0 flex-1 truncate text-sm font-medium">
                        {group.name}
                      </span>
                      <span className="text-ink-faint">›</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {others.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-faint">
                Otros grupos
              </h2>
              <ul className="mt-2 space-y-2">
                {others.map((group) => (
                  <li
                    key={group.id}
                    className="flex items-center gap-3 rounded-xl border border-edge px-4 py-2.5"
                  >
                    <span className="min-w-0 flex-1 truncate text-sm text-ink-soft">
                      {group.name}
                    </span>
                    <button
                      disabled={busy}
                      onClick={() => run(() => api.addMember(group.id, viewerId))}
                      className="rounded-lg bg-edge px-3 py-1.5 text-xs text-ink hover:opacity-90 disabled:opacity-40"
                    >
                      Unirme
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-faint">
              Crear un grupo
            </h2>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                const name = newGroup.trim();
                if (!name) return;
                setNewGroup("");
                run(async () => {
                  const created = await api.createGroup(name);
                  await api.addMember(created.id, viewerId);
                });
              }}
              className="mt-2 flex gap-2"
            >
              <input
                value={newGroup}
                onChange={(event) => setNewGroup(event.target.value)}
                placeholder="Nombre del grupo…"
                disabled={busy}
                className="min-w-0 flex-1 rounded-lg border border-edge bg-panel-soft px-3 py-2 text-sm placeholder:text-ink-faint"
              />
              <button
                disabled={busy || !newGroup.trim()}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-40"
              >
                Crear y unirme
              </button>
            </form>
          </section>
        </>
      )}
    </div>
  );
}
