"use client";

import type { Workspace } from "@/hooks/useWorkspace";
import { api } from "@/lib/api";

const SCORES = [1, 2, 3, 4, 5];

export default function RatingForm({
  workspace,
  viewerId,
}: {
  workspace: Workspace;
  viewerId: number;
}) {
  const { bundle, busy, act } = workspace;
  if (!bundle) return null;

  // The same game can be logged twice in one night; it only needs one rating row.
  const uniqueGames = [...new Map(bundle.gamesPlayed.map((g) => [g.game_id, g])).values()];

  return (
    <div className="space-y-1.5">
      {uniqueGames.map((game) => (
        <div key={game.game_id} className="flex items-center gap-2">
          <span className="w-40 truncate text-xs text-ink-soft">{game.game_name}</span>
          <div className="flex gap-1">
            {SCORES.map((score) => (
              <button
                key={score}
                disabled={busy}
                title={`${score} de 5`}
                onClick={() => act(() => api.rateGame(bundle.event.id, viewerId, game.game_id, score))}
                className="h-6 w-6 rounded bg-panel-soft text-xs hover:bg-warn-soft disabled:opacity-40"
              >
                {score}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
