"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import PersonSwitcher from "@/components/PersonSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { useViewer } from "@/components/ViewerProvider";
import type { Workspace } from "@/hooks/useWorkspace";
import { api } from "@/lib/api";
import { STATUS_LABEL, avatarColor, initials } from "@/lib/format";

export default function Sidebar({ workspace }: { workspace: Workspace }) {
  const { groupId, members, events, nextHost, eventId, busy, act } = workspace;
  const { people, viewerId } = useViewer();
  const [groupName, setGroupName] = useState("");
  const [newPerson, setNewPerson] = useState("");
  const [memberToAdd, setMemberToAdd] = useState("");

  useEffect(() => {
    api
      .getGroup(groupId)
      .then((group) => setGroupName(group.name))
      .catch(() => setGroupName(""));
  }, [groupId]);

  const nonMembers = people.filter(
    (person) => !members.some((member) => member.person_id === person.id),
  );

  return (
    <aside className="thin-scroll flex w-72 shrink-0 flex-col overflow-y-auto border-r border-edge bg-panel">
      <div className="border-b border-edge p-4">
        <div className="flex items-center gap-2">
          <Link href="/" className="text-xs text-ink-soft hover:text-ink">
            ‹ Mis grupos
          </Link>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>
        <h2 className="mt-2 truncate text-base font-semibold">{groupName || "…"}</h2>
        <div className="mt-3">
          <PersonSwitcher />
        </div>
      </div>

      <Section title={`Miembros (${members.length})`}>
        {members.map((member) => (
          <div key={member.person_id} className="flex items-center gap-2 px-3 py-1.5 text-sm">
            <Avatar personId={member.person_id} name={member.name} />
            <span className="truncate">{member.name}</span>
            {member.person_id === viewerId && (
              <span className="shrink-0 text-[10px] text-ink-faint">(tú)</span>
            )}
            {nextHost?.person_id === member.person_id && (
              <span
                title={nextHost.reason}
                className="ml-auto shrink-0 rounded bg-warn-soft px-1.5 py-0.5 text-[10px] text-warn-ink"
              >
                próx. anfitrión/a
              </span>
            )}
          </div>
        ))}

        {nonMembers.length > 0 && (
          <div className="flex gap-1 px-3 py-2">
            <select
              value={memberToAdd}
              onChange={(event) => setMemberToAdd(event.target.value)}
              className="min-w-0 flex-1 rounded border border-edge bg-panel-soft px-2 py-1 text-xs"
            >
              <option value="">Agregar miembro…</option>
              {nonMembers.map((person) => (
                <option key={person.id} value={person.id}>
                  {person.name}
                </option>
              ))}
            </select>
            <button
              disabled={!memberToAdd || busy}
              onClick={async () => {
                const personId = Number(memberToAdd);
                setMemberToAdd("");
                await act(() => api.addMember(groupId, personId));
              }}
              className="rounded bg-edge px-2 text-xs text-ink hover:opacity-90 disabled:opacity-40"
            >
              +
            </button>
          </div>
        )}

        <form
          onSubmit={(event) => {
            event.preventDefault();
            const name = newPerson.trim();
            if (!name) return;
            setNewPerson("");
            act(async () => {
              const person = await api.createPerson(name);
              await api.addMember(groupId, person.id);
            });
          }}
          className="px-3 py-2"
        >
          <input
            value={newPerson}
            onChange={(event) => setNewPerson(event.target.value)}
            placeholder="Crear persona…"
            disabled={busy}
            className="w-full rounded border border-edge bg-panel-soft px-2 py-1 text-xs placeholder:text-ink-faint"
          />
        </form>
      </Section>

      <Section title="Juntas">
        {events.map((event) => (
          <button
            key={event.id}
            onClick={() => workspace.setEventId(event.id)}
            className={`flex w-full items-center gap-2 px-4 py-1.5 text-left text-sm hover:bg-panel-soft ${
              event.id === eventId ? "bg-panel-soft font-medium text-ink" : "text-ink-soft"
            }`}
          >
            <span className="truncate">{event.title}</span>
            <span className="ml-auto shrink-0 text-[10px] text-ink-faint">
              {STATUS_LABEL[event.status]}
            </span>
          </button>
        ))}
        <button
          disabled={busy || members.length === 0}
          onClick={async () => {
            const title = `Junta ${new Date().toLocaleDateString("es-CL")}`;
            await act(async () => {
              const created = await api.createEvent(groupId, title);
              workspace.setEventId(created.id);
            });
          }}
          className="mx-3 my-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-40"
        >
          + Nueva junta {nextHost ? `(anfitrión/a: ${nextHost.name})` : ""}
        </button>
      </Section>
    </aside>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-edge py-3">
      <p className="px-4 pb-1 text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
        {title}
      </p>
      {children}
    </div>
  );
}

export function Avatar({ personId, name }: { personId: number; name: string }) {
  return (
    <span
      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white ${avatarColor(
        personId,
      )}`}
    >
      {initials(name)}
    </span>
  );
}
