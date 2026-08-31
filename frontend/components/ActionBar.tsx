"use client";

import { useState } from "react";

import RatingForm from "@/components/RatingForm";
import { useViewer } from "@/components/ViewerProvider";
import type { Workspace } from "@/hooks/useWorkspace";
import { api } from "@/lib/api";
import { MAX_PROPOSED_DATES } from "@/lib/constants";
import { toUtcIso } from "@/lib/format";
import type { AttendanceStatus } from "@/lib/types";

/** datetime-local wants "YYYY-MM-DDTHH:mm" in local time. */
function defaultSlot(daysAhead: number) {
  const slot = new Date();
  slot.setDate(slot.getDate() + daysAhead);
  slot.setHours(20, 0, 0, 0);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${slot.getFullYear()}-${pad(slot.getMonth() + 1)}-${pad(slot.getDate())}T${pad(
    slot.getHours(),
  )}:${pad(slot.getMinutes())}`;
}

export default function ActionBar({
  workspace,
  isHost,
  isMember,
}: {
  workspace: Workspace;
  isHost: boolean;
  isMember: boolean;
}) {
  const { bundle, games, busy, act } = workspace;
  const { viewerId } = useViewer();
  const [slots, setSlots] = useState([defaultSlot(7), defaultSlot(8)]);
  const [gameToLog, setGameToLog] = useState("");

  if (!bundle || viewerId === null) return null;
  const { event, tally, gamesPlayed, attendance, dates } = bundle;
  const myAttendance = attendance.find((row) => row.person_id === viewerId);

  // The cap belongs to the event, so what is already proposed eats into what can be added.
  const remaining = MAX_PROPOSED_DATES - dates.length;
  const visibleSlots = slots.slice(0, Math.max(remaining, 0));

  const canPropose =
    isHost && (event.status === "draft" || event.status === "voting") && remaining > 0;
  const canCloseVoting = isHost && event.status === "voting" && tally.dates.length > 0;
  const canSetAttendance = isMember && event.status === "confirmed";
  const canLogGames = isHost && (event.status === "confirmed" || event.status === "completed");
  const canRate = isMember && gamesPlayed.length > 0;
  const hasNothingToDo =
    isMember && !canPropose && !canCloseVoting && !canSetAttendance && !canLogGames && !canRate;

  return (
    <div className="border-t border-edge bg-panel px-6 py-4">
      {canPropose && (
        <Block
          label={`Proponer fechas (solo anfitrión/a) · ${dates.length}/${MAX_PROPOSED_DATES} usadas`}
        >
          <div className="flex flex-wrap items-center gap-2">
            {visibleSlots.map((slot, index) => (
              <div key={index} className="flex items-center gap-1">
                <input
                  type="datetime-local"
                  value={slot}
                  onChange={(changed) =>
                    setSlots(slots.map((s, i) => (i === index ? changed.target.value : s)))
                  }
                  className="rounded-lg border border-edge bg-panel-soft px-2 py-1.5 text-xs"
                />
                {visibleSlots.length > 1 && (
                  <button
                    onClick={() => setSlots(visibleSlots.filter((_, i) => i !== index))}
                    title="Quitar esta fecha"
                    aria-label="Quitar esta fecha"
                    className="rounded px-1 text-xs text-ink-faint hover:text-ink"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}

            {visibleSlots.length < remaining && (
              <button
                onClick={() => setSlots([...visibleSlots, defaultSlot(7 + visibleSlots.length)])}
                className="rounded-lg border border-edge px-2.5 py-1.5 text-xs text-ink-soft hover:bg-panel-soft"
              >
                + fecha
              </button>
            )}

            <button
              disabled={busy || visibleSlots.length === 0}
              onClick={() =>
                act(() => api.proposeDates(event.id, viewerId, visibleSlots.map(toUtcIso)))
              }
              className="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-500 disabled:opacity-40"
            >
              Proponer
            </button>
          </div>
        </Block>
      )}

      {isHost && remaining <= 0 && event.status === "voting" && (
        <p className="mb-3 text-[11px] text-ink-faint">
          Ya hay {MAX_PROPOSED_DATES} fechas en la mesa, el máximo por junta.
        </p>
      )}

      {canCloseVoting && (
        <Block label="Cerrar la votación (solo anfitrión/a)">
          <div className="flex flex-wrap items-center gap-2">
            <button
              disabled={busy || tally.leading_date_id === null}
              onClick={() => act(() => api.confirmDate(event.id, viewerId))}
              className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-40"
            >
              ✓ Confirmar la fecha que va ganando
            </button>
            {tally.is_tie && (
              <>
                <span className="text-xs text-warn-ink">
                  Hay empate: el sistema no elige por ti.
                </span>
                {tally.dates.map((date) => (
                  <button
                    key={date.proposed_date_id}
                    disabled={busy}
                    onClick={() =>
                      act(() => api.confirmDate(event.id, viewerId, date.proposed_date_id))
                    }
                    className="rounded-lg border border-edge px-2 py-1 text-xs hover:bg-panel-soft"
                  >
                    Elegir {new Date(date.starts_at).toLocaleDateString("es-CL")}
                  </button>
                ))}
              </>
            )}
          </div>
        </Block>
      )}

      {canSetAttendance && (
        <Block label="Tu asistencia">
          <div className="flex flex-wrap gap-1.5">
            {(["expected", "attended", "absent"] as AttendanceStatus[]).map((status) => (
              <button
                key={status}
                disabled={busy}
                onClick={() => act(() => api.setAttendance(event.id, viewerId, status))}
                className={`rounded-lg px-2.5 py-1 text-xs disabled:opacity-40 ${
                  myAttendance?.status === status
                    ? "bg-ink font-semibold text-canvas"
                    : "bg-panel-soft hover:bg-edge"
                }`}
              >
                {{ expected: "Voy", attended: "Fui", absent: "No fui" }[status]}
              </button>
            ))}
          </div>
        </Block>
      )}

      {canLogGames && (
        <Block label="Registrar lo que se jugó (solo anfitrión/a)">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={gameToLog}
              onChange={(changed) => setGameToLog(changed.target.value)}
              className="rounded-lg border border-edge bg-panel-soft px-2 py-1.5 text-xs"
            >
              <option value="">Elige un juego…</option>
              {games.map((game) => (
                <option key={game.id} value={game.id}>
                  {game.name}
                </option>
              ))}
            </select>
            <button
              disabled={busy || !gameToLog}
              onClick={async () => {
                const gameId = Number(gameToLog);
                setGameToLog("");
                await act(() => api.addGamePlayed(event.id, gameId));
              }}
              className="rounded-lg bg-edge px-3 py-1.5 text-xs text-ink hover:opacity-90 disabled:opacity-40"
            >
              + Se jugó
            </button>
            {event.status === "confirmed" && (
              <button
                disabled={busy}
                onClick={() => act(() => api.completeEvent(event.id, viewerId))}
                className="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-500 disabled:opacity-40"
              >
                🏁 Cerrar la noche
              </button>
            )}
          </div>
        </Block>
      )}

      {canRate && (
        <Block label="Valorar los juegos">
          <RatingForm workspace={workspace} viewerId={viewerId} />
        </Block>
      )}

      {hasNothingToDo && (
        <p className="text-xs text-ink-faint">
          Nada que hacer por ahora: responde la encuesta de arriba y espera a que quien
          organiza cierre la fecha.
        </p>
      )}
    </div>
  );
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-3 last:mb-0">
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
        {label}
      </p>
      {children}
    </div>
  );
}
