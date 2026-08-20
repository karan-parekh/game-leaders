export type Me = { id: string; username: string };

export type Game = {
  id: string;
  name: string;
  default_timeout_minutes: number;
  ranking_direction: string;
  metrics: { id: string; label: string }[];
};

export type SessionParticipant = {
  user_id: string;
  username: string;
  active: boolean;
  scores: Record<string, number>;
};

export type Session = {
  id: string;
  room_code: string;
  name: string;
  game_id: string;
  ranking_direction: string;
  host_id: string;
  capacity: number;
  timeout_minutes: number;
  state: string;
  metrics: { id: string; label: string }[];
  revision: number;
  deadline: string | null;
  participants: SessionParticipant[];
};

export type RecentSession = {
  id: string;
  name: string;
  room_code: string;
  game_id: string;
  capacity: number;
  state: string;
};

export type LeaderboardRow = {
  user_id: string;
  username: string;
  score: number;
  session_id: string;
  games_played: number;
  rank: number;
};

export function messageOf(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong";
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // keep the default message
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (username: string, password: string) =>
    request("/api/auth/register", { method: "POST", body: JSON.stringify({ username, password }) }),
  login: (username: string, password: string) =>
    request("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request<Me>("/api/auth/me"),
  games: () => request<Game[]>("/api/games"),
  createSession: (payload: { game_id: string; capacity: number; timeout_minutes?: number }) =>
    request<Session>("/api/sessions", { method: "POST", body: JSON.stringify(payload) }),
  recentSessions: () => request<RecentSession[]>("/api/sessions/recent"),
  getSession: (key: string) => request<Session>(`/api/sessions/${encodeURIComponent(key)}`),
  joinSession: (sessionId: string) => request<Session>(`/api/sessions/${sessionId}/join`, { method: "POST" }),
  leaveSession: (sessionId: string) => request<Session>(`/api/sessions/${sessionId}/leave`, { method: "POST" }),
  startSession: (sessionId: string) => request<Session>(`/api/sessions/${sessionId}/start`, { method: "POST" }),
  finalizeSession: (sessionId: string) => request<Session>(`/api/sessions/${sessionId}/finalize`, { method: "POST" }),
  discardSession: (sessionId: string) => request(`/api/sessions/${sessionId}/discard`, { method: "POST" }),
  updateScore: (sessionId: string, userId: string, metric: string, value: number) =>
    request<Session>(`/api/sessions/${sessionId}/scores/${userId}`, { method: "POST", body: JSON.stringify({ metric, value }) }),
  leaderboard: (gameId: string) => request<LeaderboardRow[]>(`/api/leaderboards/${gameId}`),
  globalLeaderboard: () => request<LeaderboardRow[]>("/api/leaderboards"),
};
