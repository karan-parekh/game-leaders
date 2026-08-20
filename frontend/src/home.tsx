import { type FormEvent, useEffect, useState } from "react";
import { api, messageOf, type Me, type RecentSession } from "./api";
import { useToast } from "./toast";

const inputClass = "rounded border border-gray-300 bg-white px-3 py-2.5 text-gray-900";

function stateLabel(state: string) {
  return state.replace("_", " ");
}

export function HomeScreen({ me, onOpenSession, onCreate, onLeaderboard, onLogout }: {
  me: Me | null;
  onOpenSession: (sessionId: string) => void;
  onCreate: () => void;
  onLeaderboard: () => void;
  onLogout: () => void;
}) {
  const [code, setCode] = useState("");
  const [recent, setRecent] = useState<RecentSession[]>([]);
  const showToast = useToast();

  useEffect(() => {
    api.recentSessions().then(setRecent).catch((error) => showToast(messageOf(error)));
  }, []);

  async function joinByCode(event: FormEvent) {
    event.preventDefault();
    try {
      const session = await api.getSession(code);
      onOpenSession(session.id);
    } catch (error) {
      showToast(messageOf(error));
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-sm flex-col gap-6 px-6 py-10">
      <header className="flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-widest text-gray-500">Game Leaders</span>
          <h1 className="text-2xl font-bold">Hi, {me?.username}</h1>
        </div>
        <button className="rounded border border-gray-300 bg-white px-3 py-2 text-xs font-semibold text-gray-700" onClick={onLogout}>Log out</button>
      </header>

      <form onSubmit={joinByCode} className="flex flex-col gap-2 border-t border-gray-200 pt-5">
        <label htmlFor="room-code" className="text-sm text-gray-600">Join a session by room code</label>
        <div className="flex gap-2">
          <input id="room-code" className={`${inputClass} flex-1 uppercase`} placeholder="6-character code" value={code} onChange={(e) => setCode(e.target.value)} />
          <button className="rounded bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white" type="submit">Join</button>
        </div>
      </form>

      <section className="flex flex-col gap-3 border-t border-gray-200 pt-5">
        <div className="flex items-baseline justify-between px-1">
          <h2 className="text-sm font-semibold">Recent sessions</h2>
          <button className="text-xs font-semibold text-blue-600" onClick={onCreate}>New session</button>
        </div>
        {recent.length === 0 ? (
          <p className="px-1 text-sm text-gray-500">No open sessions right now.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {recent.map((session) => (
              <button className="flex items-center gap-3 rounded border border-gray-100 bg-white px-3 py-2 text-left" key={session.id} onClick={() => onOpenSession(session.id)}>
                <div className="flex min-w-0 flex-1 flex-col">
                  <strong className="truncate text-sm font-semibold">{session.name}</strong>
                  <span className="font-mono text-[11px] text-gray-400">{session.room_code}</span>
                </div>
                <div className="flex flex-col items-end">
                  <span className="text-xs font-semibold text-gray-600">Up to {session.capacity}</span>
                  <span className="text-[11px] text-gray-400">{stateLabel(session.state)}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      <button className="rounded border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-800" onClick={onLeaderboard}>Leaderboard</button>
    </main>
  );
}