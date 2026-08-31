"use client";

import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { Recommendations } from "@/lib/types";

export default function RecommendationsPanel({ eventId }: { eventId: number }) {
  const [data, setData] = useState<Recommendations | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setMessage(null);
    api
      .getRecommendations(eventId)
      .then(setData)
      .catch((caught) =>
        setMessage(caught instanceof ApiError ? caught.message : String(caught)),
      );
  }, [eventId]);

  return (
    <aside className="thin-scroll w-80 shrink-0 overflow-y-auto border-l border-edge bg-panel p-4">
      <h2 className="text-sm font-semibold">¿Qué jugamos?</h2>
      <p className="mt-0.5 text-[11px] text-ink-faint">
        Filtra por quién trae qué y por cuántos son; luego ordena por gusto del grupo y novedad.
      </p>

      {message && <p className="mt-3 text-xs text-ink-faint">{message}</p>}

      {data && (
        <>
          <p className="mt-3 text-[11px] text-ink-faint">
            {data.player_count} jugadores confirmados
          </p>

          <ol className="mt-2 space-y-2">
            {data.recommendations.map((game, index) => (
              <li key={game.game_id} className="rounded-xl border border-edge p-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-xs text-ink-faint">#{index + 1}</span>
                  <span className="text-sm font-medium">{game.game_name}</span>
                  <span className="ml-auto text-xs tabular-nums text-ink-soft">
                    {game.score.toFixed(3)}
                  </span>
                </div>
                <ul className="mt-1.5 space-y-0.5">
                  {game.reasons.map((reason) => (
                    <li key={reason} className="text-[11px] leading-snug text-ink-soft">
                      · {reason}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>

          {Object.keys(data.excluded).length > 0 && (
            <div className="mt-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
                Descartados
              </p>
              <ul className="mt-1 space-y-0.5">
                {Object.entries(data.excluded).map(([name, reason]) => (
                  <li key={name} className="text-[11px] leading-snug text-ink-faint">
                    <span className="text-ink-soft">{name}</span>: {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </aside>
  );
}
