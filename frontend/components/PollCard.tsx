"use client";

import { useViewer } from "@/components/ViewerProvider";
import type { Workspace } from "@/hooks/useWorkspace";
import { api } from "@/lib/api";
import { AVAILABILITY_ICON, AVAILABILITY_LABEL, formatDateTime } from "@/lib/format";
import type { Availability } from "@/lib/types";

const CHOICES: Availability[] = ["yes", "maybe", "no"];

export default function PollCard({
  workspace,
  isMember,
}: {
  workspace: Workspace;
  isMember: boolean;
}) {
  const { bundle, busy, act } = workspace;
  const { viewerId } = useViewer();
  if (!bundle) return null;

  const { tally, votes, event } = bundle;
  const isOpen = event.status === "voting";
  const maxScore = Math.max(1, ...tally.dates.map((date) => date.score));

  const myVote = (dateId: number) =>
    votes.find((vote) => vote.proposed_date_id === dateId && vote.person_id === viewerId)
      ?.availability ?? null;

  return (
    <div className="max-w-2xl rounded-2xl border border-edge bg-panel p-4">
      <div className="mb-3 flex items-baseline gap-2">
        <h3 className="text-sm font-semibold">Encuesta de disponibilidad</h3>
        <span className="text-xs text-ink-faint">
          {tally.eligible_voters} pueden votar · puntaje = sí + ½ · quizá
        </span>
      </div>

      <div className="space-y-3">
        {tally.dates.map((date) => {
          const leading = tally.leading_date_id === date.proposed_date_id;
          const mine = myVote(date.proposed_date_id);
          const confirmed = event.confirmed_date_id === date.proposed_date_id;

          return (
            <div
              key={date.proposed_date_id}
              className={`rounded-xl border p-3 ${
                confirmed
                  ? "border-ok-ink/40 bg-ok-soft"
                  : leading && isOpen
                    ? "border-warn-ink/40 bg-warn-soft"
                    : "border-edge"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{formatDateTime(date.starts_at)}</span>
                {confirmed && <span className="text-xs text-ok-ink">✓ confirmada</span>}
                {!confirmed && leading && isOpen && (
                  <span className="text-xs text-warn-ink">
                    va ganando{tally.is_tie ? " (empate)" : ""}
                  </span>
                )}
                <span className="ml-auto text-xs tabular-nums text-ink-soft">
                  {date.score.toFixed(1)}
                </span>
              </div>

              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-panel-soft">
                <div
                  className={`h-full rounded-full ${confirmed ? "bg-emerald-500" : "bg-amber-500"}`}
                  style={{ width: `${(date.score / maxScore) * 100}%` }}
                />
              </div>

              <p className="mt-2 text-[11px] text-ink-faint">
                {date.yes} sí · {date.maybe} quizá · {date.no} no
                {date.missing_voters.length > 0 && ` · faltan: ${date.missing_voters.join(", ")}`}
              </p>

              {isOpen && isMember && viewerId !== null && (
                <div className="mt-2 flex gap-1.5">
                  {CHOICES.map((choice) => (
                    <button
                      key={choice}
                      disabled={busy}
                      onClick={() =>
                        act(() =>
                          api.castVote(event.id, date.proposed_date_id, viewerId, choice),
                        )
                      }
                      className={`rounded-lg px-2.5 py-1 text-xs transition disabled:opacity-40 ${
                        mine === choice
                          ? "bg-ink font-semibold text-canvas"
                          : "bg-panel-soft text-ink-soft hover:bg-edge"
                      }`}
                    >
                      {AVAILABILITY_ICON[choice]} {AVAILABILITY_LABEL[choice]}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {isOpen && !isMember && (
        <p className="mt-3 text-xs text-ink-faint">
          Quien estás viendo no es miembro de este grupo, así que no puede votar.
        </p>
      )}
    </div>
  );
}
