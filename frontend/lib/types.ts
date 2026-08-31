// Mirrors app/domain/models.py on the backend.

export type Availability = "yes" | "maybe" | "no";
export type EventStatus = "draft" | "voting" | "confirmed" | "completed" | "cancelled";
export type AttendanceStatus = "expected" | "attended" | "absent";

export interface Person {
  id: number;
  name: string;
  telegram_user_id: number | null;
}

export interface Group {
  id: number;
  name: string;
}

export interface Member {
  person_id: number;
  name: string;
  is_active: boolean;
  last_hosted_at: string | null;
}

export interface NextHost {
  person_id: number;
  name: string;
  last_hosted_at: string | null;
  reason: string;
}

export interface GameEvent {
  id: number;
  group_id: number;
  host_id: number;
  title: string;
  status: EventStatus;
  confirmed_date_id: number | null;
}

export interface ProposedDate {
  id: number;
  event_id: number;
  starts_at: string;
}

export interface Vote {
  person_id: number;
  person_name: string;
  proposed_date_id: number;
  availability: Availability;
  voted_at: string;
}

export interface DateTally {
  proposed_date_id: number;
  starts_at: string;
  yes: number;
  maybe: number;
  no: number;
  score: number;
  missing_voters: string[];
}

export interface EventTally {
  event_id: number;
  status: EventStatus;
  eligible_voters: number;
  dates: DateTally[];
  leading_date_id: number | null;
  is_tie: boolean;
}

export interface Attendance {
  person_id: number;
  name: string;
  status: AttendanceStatus;
}

export interface Game {
  id: number;
  name: string;
  min_players: number;
  max_players: number;
  duration_minutes: number | null;
}

export interface GamePlayed {
  id: number;
  game_id: number;
  game_name: string;
}

export interface GameRatingSummary {
  game_id: number;
  game_name: string;
  average_score: number;
  votes: number;
}

export interface EventSummary {
  event: GameEvent;
  host_name: string;
  confirmed_starts_at: string | null;
  attendees: Attendance[];
  games_played: GamePlayed[];
  ratings: GameRatingSummary[];
}

export interface Recommendation {
  game_id: number;
  game_name: string;
  score: number;
  owners: string[];
  reasons: string[];
}

export interface Recommendations {
  event_id: number;
  player_count: number;
  recommendations: Recommendation[];
  excluded: Record<string, string>;
}

export interface Reminder {
  event_id: number;
  title: string;
  starts_at: string;
  recipients: string[];
}
