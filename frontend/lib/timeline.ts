import { AVAILABILITY_ICON, ATTENDANCE_LABEL, formatDateTime, formatShortDate } from "./format";
import type {
  Attendance,
  GameEvent,
  GamePlayed,
  GameRatingSummary,
  ProposedDate,
  Reminder,
  Vote,
} from "./types";

export type TimelineItem =
  | { kind: "system"; id: string; icon: string; text: string }
  | { kind: "message"; id: string; personId: number; author: string; text: string; at: string }
  | { kind: "poll"; id: string }
  | { kind: "reminder"; id: string; text: string; recipients: string[] };

export interface TimelineInput {
  event: GameEvent;
  hostName: string;
  dates: ProposedDate[];
  votes: Vote[];
  attendance: Attendance[];
  gamesPlayed: GamePlayed[];
  ratings: GameRatingSummary[];
  reminders: Reminder[];
}

/**
 * Builds the chat from the API's own data. Pure on purpose — same reasoning as the
 * backend's rotation and tally: no fetching here, so what the timeline shows is a
 * function of state alone and can be reasoned about (and tested) directly.
 */
export function buildTimeline(input: TimelineInput): TimelineItem[] {
  const { event, hostName, dates, votes, attendance, gamesPlayed, ratings, reminders } = input;
  const items: TimelineItem[] = [];

  items.push({
    id: "created",
    kind: "system",
    icon: "🎲",
    text: `Se abrió «${event.title}». El sistema asignó a ${hostName} como anfitrión/a por rotación.`,
  });

  // A closed event that never collected votes has nothing to show as a poll — its
  // confirmed date is already announced by the system line further down.
  const pollIsInteresting =
    dates.length > 0 && (event.status === "voting" || votes.length > 0);

  if (pollIsInteresting) {
    items.push({
      id: "proposal",
      kind: "message",
      personId: event.host_id,
      author: hostName,
      text: "Propongo estas fechas. ¿Cuáles les sirven?",
      at: dates[0].starts_at,
    });
    items.push({ id: "poll", kind: "poll" });
    items.push(...voteMessages(dates, votes));
  }

  items.push(...reminders.map(reminderItem));

  if (event.confirmed_date_id !== null) {
    const confirmed = dates.find((date) => date.id === event.confirmed_date_id);
    if (confirmed) {
      items.push({
        id: "confirmed",
        kind: "system",
        icon: "📅",
        text: `${hostName} confirmó la fecha: ${formatDateTime(confirmed.starts_at)}.`,
      });
    }
    if (attendance.length > 0) {
      items.push({
        id: "attendance",
        kind: "system",
        icon: "👥",
        text: `Lista de asistencia: ${attendance
          .map((row) => `${row.name} (${ATTENDANCE_LABEL[row.status].toLowerCase()})`)
          .join(", ")}.`,
      });
    }
  }

  if (event.status === "completed") {
    items.push({ id: "completed", kind: "system", icon: "🏁", text: "La noche se cerró." });
  }

  if (gamesPlayed.length > 0) {
    items.push({
      id: "games",
      kind: "system",
      icon: "🃏",
      text: `Se jugó: ${gamesPlayed.map((game) => game.game_name).join(", ")}.`,
    });
  }

  for (const rating of ratings) {
    items.push({
      id: `rating-${rating.game_id}`,
      kind: "system",
      icon: "⭐",
      text: `${rating.game_name}: ${rating.average_score} de 5 (${rating.votes} ${
        rating.votes === 1 ? "voto" : "votos"
      }).`,
    });
  }

  if (event.status === "cancelled") {
    items.push({ id: "cancelled", kind: "system", icon: "🚫", text: "El evento fue cancelado." });
  }

  return items;
}

/** One message per person summarising their whole answer, ordered by when they first voted. */
function voteMessages(dates: ProposedDate[], votes: Vote[]): TimelineItem[] {
  const labels = new Map(dates.map((date) => [date.id, formatShortDate(date.starts_at)]));
  const byPerson = new Map<number, Vote[]>();

  for (const vote of votes) {
    const existing = byPerson.get(vote.person_id);
    if (existing) existing.push(vote);
    else byPerson.set(vote.person_id, [vote]);
  }

  return [...byPerson.entries()].map(([personId, personVotes]) => {
    const ordered = dates
      .map((date) => personVotes.find((vote) => vote.proposed_date_id === date.id))
      .filter((vote): vote is Vote => vote !== undefined);

    return {
      kind: "message" as const,
      id: `votes-${personId}`,
      personId,
      author: personVotes[0].person_name,
      text: ordered
        .map((vote) => `${labels.get(vote.proposed_date_id)} ${AVAILABILITY_ICON[vote.availability]}`)
        .join("   "),
      at: personVotes[personVotes.length - 1].voted_at,
    };
  });
}

function reminderItem(reminder: Reminder, index: number): TimelineItem {
  return {
    kind: "reminder",
    id: `reminder-${index}`,
    text: `Recordatorio: «${reminder.title}» es el ${formatDateTime(reminder.starts_at)}.`,
    recipients: reminder.recipients,
  };
}
