"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";

import ActionBar from "@/components/ActionBar";
import Chat from "@/components/Chat";
import RecommendationsPanel from "@/components/RecommendationsPanel";
import Sidebar from "@/components/Sidebar";
import { useViewer } from "@/components/ViewerProvider";
import { useWorkspace } from "@/hooks/useWorkspace";
import { STATUS_LABEL, STATUS_STYLE } from "@/lib/format";
import { buildTimeline } from "@/lib/timeline";

export default function Workspace({ groupId }: { groupId: number }) {
  const router = useRouter();
  const { viewerId, ready } = useViewer();
  const workspace = useWorkspace(groupId);
  const { bundle, members, membersLoaded, reminders, error, busy } = workspace;

  const isMember = members.some((member) => member.person_id === viewerId);

  // Whoever you are viewing as has to belong here. Switching to someone from another
  // group sends you back to the home screen instead of showing a group that is not theirs.
  useEffect(() => {
    if (!ready || !membersLoaded) return;
    if (viewerId === null || !isMember) router.replace("/");
  }, [ready, membersLoaded, viewerId, isMember, router]);

  const hostName =
    members.find((member) => member.person_id === bundle?.event.host_id)?.name ?? "Alguien";
  const isHost = bundle !== null && viewerId === bundle.event.host_id;

  const timeline = useMemo(() => {
    if (!bundle) return [];
    return buildTimeline({
      event: bundle.event,
      hostName,
      dates: bundle.dates,
      votes: bundle.votes,
      attendance: bundle.attendance,
      gamesPlayed: bundle.gamesPlayed,
      ratings: bundle.summary.ratings,
      reminders,
    });
  }, [bundle, hostName, reminders]);

  if (Number.isNaN(groupId)) {
    return <p className="p-10 text-sm text-ink-faint">Ese grupo no existe.</p>;
  }

  return (
    <div className="flex h-full">
      <Sidebar workspace={workspace} />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-edge bg-panel px-6 py-4">
          {bundle ? (
            <>
              <div className="min-w-0">
                <h1 className="truncate text-lg font-semibold">{bundle.event.title}</h1>
                <p className="text-xs text-ink-soft">
                  Anfitrión/a: {hostName} · {bundle.tally.eligible_voters} personas pueden votar
                </p>
              </div>
              <span
                className={`ml-auto shrink-0 rounded-full px-3 py-1 text-xs font-medium ${
                  STATUS_STYLE[bundle.event.status]
                }`}
              >
                {STATUS_LABEL[bundle.event.status]}
              </span>
              <button
                onClick={workspace.runReminders}
                disabled={busy}
                title="Ejecuta el job del scheduler, que registra en log en vez de enviar"
                className="shrink-0 rounded-lg border border-edge px-3 py-1.5 text-xs text-ink-soft hover:bg-panel-soft disabled:opacity-40"
              >
                🔔 Correr recordatorios
              </button>
            </>
          ) : (
            <h1 className="text-lg font-semibold text-ink-soft">
              Elige o crea una junta para empezar
            </h1>
          )}
        </header>

        {error && (
          <div className="flex items-start gap-2 border-b border-danger-ink/30 bg-danger-soft px-6 py-3 text-sm text-danger-ink">
            <span>⚠️</span>
            <p className="flex-1">{error}</p>
            <button
              onClick={() => workspace.setError(null)}
              className="text-danger-ink hover:opacity-70"
            >
              ✕
            </button>
          </div>
        )}

        <Chat items={timeline} workspace={workspace} isMember={isMember} />
        <ActionBar workspace={workspace} isHost={isHost} isMember={isMember} />
      </main>

      {bundle !== null && bundle.event.confirmed_date_id !== null && (
        <RecommendationsPanel eventId={bundle.event.id} />
      )}
    </div>
  );
}
