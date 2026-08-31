import type {
  Attendance,
  AttendanceStatus,
  Availability,
  EventSummary,
  EventTally,
  Game,
  GameEvent,
  GamePlayed,
  Group,
  Member,
  NextHost,
  Person,
  ProposedDate,
  Recommendations,
  Reminder,
  Vote,
} from "./types";

/** Raised for any non-2xx response, carrying the backend's own message. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });

  if (!response.ok) {
    // Domain errors arrive as {"detail": "..."}; anything else falls back to the status.
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // Body was not JSON; keep the status-based message.
    }
    throw new ApiError(detail, response.status);
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  listPeople: () => request<Person[]>("/people"),
  createPerson: (name: string) => post<Person>("/people", { name }),

  listGroups: () => request<Group[]>("/groups"),
  listGroupsForPerson: (personId: number) => request<Group[]>(`/people/${personId}/groups`),
  getGroup: (groupId: number) => request<Group>(`/groups/${groupId}`),
  createGroup: (name: string) => post<Group>("/groups", { name }),
  listMembers: (groupId: number) => request<Member[]>(`/groups/${groupId}/members`),
  addMember: (groupId: number, personId: number, lastHostedAt: string | null = null) =>
    post<Member>(`/groups/${groupId}/members`, {
      person_id: personId,
      last_hosted_at: lastHostedAt,
    }),
  nextHost: (groupId: number) => request<NextHost>(`/groups/${groupId}/next-host`),

  listEvents: (groupId: number) => request<GameEvent[]>(`/groups/${groupId}/events`),
  createEvent: (groupId: number, title: string) =>
    post<GameEvent>(`/groups/${groupId}/events`, { title }),
  getEvent: (eventId: number) => request<GameEvent>(`/events/${eventId}`),
  listProposedDates: (eventId: number) =>
    request<ProposedDate[]>(`/events/${eventId}/proposed-dates`),
  proposeDates: (eventId: number, personId: number, startsAt: string[]) =>
    post<ProposedDate[]>(`/events/${eventId}/proposed-dates`, {
      person_id: personId,
      starts_at: startsAt,
    }),

  listVotes: (eventId: number) => request<Vote[]>(`/events/${eventId}/votes`),
  getTally: (eventId: number) => request<EventTally>(`/events/${eventId}/tally`),
  castVote: (eventId: number, dateId: number, personId: number, availability: Availability) =>
    post<void>(`/events/${eventId}/proposed-dates/${dateId}/votes`, {
      person_id: personId,
      availability,
    }),

  confirmDate: (eventId: number, personId: number, proposedDateId: number | null = null) =>
    post<GameEvent>(`/events/${eventId}/confirm`, {
      person_id: personId,
      proposed_date_id: proposedDateId,
    }),
  listAttendance: (eventId: number) => request<Attendance[]>(`/events/${eventId}/attendance`),
  setAttendance: (eventId: number, personId: number, status: AttendanceStatus) =>
    request<void>(`/events/${eventId}/attendance`, {
      method: "PUT",
      body: JSON.stringify({ person_id: personId, status }),
    }),
  completeEvent: (eventId: number, personId: number) =>
    post<GameEvent>(`/events/${eventId}/complete?person_id=${personId}`),

  listGames: () => request<Game[]>("/games"),
  listGamesPlayed: (eventId: number) => request<GamePlayed[]>(`/events/${eventId}/games-played`),
  addGamePlayed: (eventId: number, gameId: number) =>
    post<GamePlayed>(`/events/${eventId}/games-played`, { game_id: gameId }),
  rateGame: (eventId: number, personId: number, gameId: number, score: number) =>
    post<unknown>(`/events/${eventId}/ratings`, {
      person_id: personId,
      game_id: gameId,
      score,
    }),

  getSummary: (eventId: number) => request<EventSummary>(`/events/${eventId}/summary`),
  getRecommendations: (eventId: number) =>
    request<Recommendations>(`/events/${eventId}/recommendations`),
  runReminders: () => post<Reminder[]>("/jobs/reminders"),
};
