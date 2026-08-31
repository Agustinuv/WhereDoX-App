import type { Availability, AttendanceStatus, EventStatus } from "./types";

const DATE_TIME = new Intl.DateTimeFormat("es-CL", {
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

const SHORT_DATE = new Intl.DateTimeFormat("es-CL", {
  weekday: "short",
  day: "numeric",
  month: "short",
});

/** Backend timestamps are UTC; everything on screen is the viewer's local time. */
export const formatDateTime = (iso: string) => DATE_TIME.format(new Date(iso));
export const formatShortDate = (iso: string) => SHORT_DATE.format(new Date(iso));

/** Turns a datetime-local input value into the UTC instant the backend stores. */
export const toUtcIso = (localValue: string) => new Date(localValue).toISOString();

export const AVAILABILITY_ICON: Record<Availability, string> = {
  yes: "✅",
  maybe: "❓",
  no: "❌",
};

export const AVAILABILITY_LABEL: Record<Availability, string> = {
  yes: "Sí",
  maybe: "Quizá",
  no: "No",
};

export const STATUS_LABEL: Record<EventStatus, string> = {
  draft: "Sin fechas",
  voting: "Votando",
  confirmed: "Confirmado",
  completed: "Cerrado",
  cancelled: "Cancelado",
};

export const STATUS_STYLE: Record<EventStatus, string> = {
  draft: "bg-panel-soft text-ink-soft",
  voting: "bg-warn-soft text-warn-ink",
  confirmed: "bg-ok-soft text-ok-ink",
  completed: "bg-info-soft text-info-ink",
  cancelled: "bg-danger-soft text-danger-ink",
};

export const ATTENDANCE_LABEL: Record<AttendanceStatus, string> = {
  expected: "Confirmó",
  attended: "Asistió",
  absent: "No fue",
};

/** Stable, readable colour per person so avatars stay recognisable across the timeline. */
const AVATAR_COLORS = [
  "bg-rose-500",
  "bg-amber-500",
  "bg-emerald-500",
  "bg-sky-500",
  "bg-violet-500",
  "bg-fuchsia-500",
  "bg-teal-500",
];

export const avatarColor = (personId: number) => AVATAR_COLORS[personId % AVATAR_COLORS.length];

export const initials = (name: string) =>
  name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
