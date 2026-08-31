"use client";

import { useEffect, useRef } from "react";

import PollCard from "@/components/PollCard";
import { Avatar } from "@/components/Sidebar";
import type { Workspace } from "@/hooks/useWorkspace";
import { formatDateTime } from "@/lib/format";
import type { TimelineItem } from "@/lib/timeline";

export default function Chat({
  items,
  workspace,
  isMember,
}: {
  items: TimelineItem[];
  workspace: Workspace;
  isMember: boolean;
}) {
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [items]);

  if (!workspace.bundle) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-ink-faint">
        Elige un grupo y una junta en la barra lateral, o crea una nueva.
      </div>
    );
  }

  return (
    <div className="thin-scroll flex-1 space-y-3 overflow-y-auto px-6 py-5">
      {items.map((item) => {
        switch (item.kind) {
          case "system":
            return <SystemLine key={item.id} icon={item.icon} text={item.text} />;

          case "reminder":
            return (
              <div
                key={item.id}
                className="mx-auto max-w-xl rounded-xl border border-warn-ink/40 bg-warn-soft px-4 py-3 text-sm"
              >
                <p className="font-medium text-warn-ink">🔔 {item.text}</p>
                <p className="mt-1 text-xs text-warn-ink/80">
                  Se notificaría a: {item.recipients.join(", ") || "nadie"}
                </p>
                <p className="mt-1 text-[11px] text-warn-ink/60">
                  El scheduler es un stub: escribe en el log, no envía nada.
                </p>
              </div>
            );

          case "poll":
            return <PollCard key={item.id} workspace={workspace} isMember={isMember} />;

          case "message":
            return (
              <div key={item.id} className="flex gap-3">
                <Avatar personId={item.personId} name={item.author} />
                <div className="min-w-0">
                  <p className="text-xs text-ink-soft">
                    <span className="font-medium text-ink-soft">{item.author}</span>{" "}
                    <span className="text-ink-faint">· {formatDateTime(item.at)}</span>
                  </p>
                  <div className="mt-1 inline-block rounded-2xl rounded-tl-sm bg-panel-soft px-3 py-2 text-sm">
                    {item.text}
                  </div>
                </div>
              </div>
            );
        }
      })}
      <div ref={bottom} />
    </div>
  );
}

function SystemLine({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="flex justify-center">
      <p className="rounded-full bg-panel px-4 py-1.5 text-center text-xs text-ink-soft">
        {icon} {text}
      </p>
    </div>
  );
}
