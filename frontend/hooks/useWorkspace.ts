"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type {
  Attendance,
  EventSummary,
  EventTally,
  Game,
  GameEvent,
  GamePlayed,
  Member,
  NextHost,
  ProposedDate,
  Reminder,
  Vote,
} from "@/lib/types";

export interface EventBundle {
  event: GameEvent;
  dates: ProposedDate[];
  votes: Vote[];
  tally: EventTally;
  attendance: Attendance[];
  gamesPlayed: GamePlayed[];
  summary: EventSummary;
}

export type Workspace = ReturnType<typeof useWorkspace>;

/**
 * All server state for one group, refetched wholesale after every action.
 *
 * Refetching everything is the right trade here: the data is tiny, and it means the screen
 * can never drift from what the backend actually decided — which is the point of the demo.
 */
export function useWorkspace(groupId: number) {
  const [games, setGames] = useState<Game[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [events, setEvents] = useState<GameEvent[]>([]);
  const [nextHost, setNextHost] = useState<NextHost | null>(null);
  const [bundle, setBundle] = useState<EventBundle | null>(null);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [eventId, setEventId] = useState<number | null>(null);

  // Membership drives the redirect home, so pages must be able to tell "not a member"
  // apart from "not loaded yet".
  const [membersLoaded, setMembersLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadGroup = useCallback(async () => {
    const [nextMembers, nextEvents, nextGames] = await Promise.all([
      api.listMembers(groupId),
      api.listEvents(groupId),
      api.listGames(),
    ]);
    setMembers(nextMembers);
    setEvents(nextEvents);
    setGames(nextGames);
    setMembersLoaded(true);
    // A group with no active members has no next host, which is not an error here.
    setNextHost(await api.nextHost(groupId).catch(() => null));
    return nextEvents;
  }, [groupId]);

  const loadEvent = useCallback(async (id: number) => {
    const [event, dates, votes, tally, attendance, gamesPlayed, summary] = await Promise.all([
      api.getEvent(id),
      api.listProposedDates(id),
      api.listVotes(id),
      api.getTally(id),
      api.listAttendance(id),
      api.listGamesPlayed(id),
      api.getSummary(id),
    ]);
    setBundle({ event, dates, votes, tally, attendance, gamesPlayed, summary });
  }, []);

  /** Runs an action, then refreshes everything it could have touched. */
  const act = useCallback(
    async (action: () => Promise<unknown>) => {
      setBusy(true);
      setError(null);
      try {
        await action();
        await loadGroup();
        if (eventId !== null) await loadEvent(eventId);
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : String(caught));
      } finally {
        setBusy(false);
      }
    },
    [eventId, loadGroup, loadEvent],
  );

  useEffect(() => {
    setMembersLoaded(false);
    setEventId(null);
    setBundle(null);
    setReminders([]);
    loadGroup()
      .then((loaded) => setEventId(loaded[0]?.id ?? null))
      .catch((caught) =>
        setError(
          caught instanceof ApiError
            ? caught.message
            : "No se pudo contactar la API. ¿Está corriendo el backend?",
        ),
      );
  }, [loadGroup]);

  useEffect(() => {
    if (eventId === null) {
      setBundle(null);
      return;
    }
    loadEvent(eventId).catch((caught) => setError(String(caught)));
  }, [eventId, loadEvent]);

  const runReminders = useCallback(async () => {
    setBusy(true);
    try {
      const fired = await api.runReminders();
      setReminders(fired.filter((reminder) => reminder.event_id === eventId));
      setError(
        fired.length === 0
          ? "El job no encontró eventos dentro de la ventana de recordatorio."
          : null,
      );
    } finally {
      setBusy(false);
    }
  }, [eventId]);

  return {
    groupId,
    games,
    members,
    events,
    nextHost,
    bundle,
    reminders,
    eventId,
    membersLoaded,
    busy,
    error,
    setEventId,
    setError,
    act,
    runReminders,
  };
}
