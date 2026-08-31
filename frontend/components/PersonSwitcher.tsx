"use client";

import { useViewer } from "@/components/ViewerProvider";

/** The whole authentication story of this prototype, in one dropdown. */
export default function PersonSwitcher({ compact = false }: { compact?: boolean }) {
  const { people, viewerId, setViewerId } = useViewer();

  return (
    <div>
      {!compact && (
        <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
          Viendo como
        </p>
      )}
      <select
        value={viewerId ?? ""}
        aria-label="Viendo como"
        onChange={(event) =>
          setViewerId(event.target.value === "" ? null : Number(event.target.value))
        }
        className={`w-full rounded-lg border border-edge bg-panel-soft px-3 py-2 text-sm ${
          compact ? "" : "mt-2"
        }`}
      >
        <option value="">— elige una persona —</option>
        {people.map((person) => (
          <option key={person.id} value={person.id}>
            {person.name}
          </option>
        ))}
      </select>
    </div>
  );
}
