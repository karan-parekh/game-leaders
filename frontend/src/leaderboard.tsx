import { useEffect, useRef, useState } from "react";
import { api, messageOf, type Game, type LeaderboardRow } from "./api";
import { useToast } from "./toast";

const inputClass = "rounded border border-gray-300 bg-white px-3 py-2.5 text-gray-900";

export function LeaderboardScreen({ onBack }: { onBack: () => void }) {
  const [games, setGames] = useState<Game[]>([]);
  const [gameId, setGameId] = useState("");
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const showToast = useToast();
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    api.games().then((list) => {
      setGames(list);
      if (list.length > 0 && gameId === "") {
        setGameId(list[0].id);
      }
    }).catch((error) => showToast(messageOf(error)));
  }, []);

  useEffect(() => {
    if (!gameId) return;

    eventSourceRef.current?.close();

    api.leaderboard(gameId).then(setRows).catch((error) => showToast(messageOf(error)));

    const es = new EventSource(`/api/leaderboards/${gameId}/events`);
    eventSourceRef.current = es;

    es.addEventListener("leaderboard", (event) => {
      try {
        setRows(JSON.parse(event.data));
      } catch {
        // ignore malformed events
      }
    });

    es.onerror = () => {
      es.close();
    };

    return () => { es.close(); };
  }, [gameId]);

  const currentGame = games.find((g) => g.id === gameId);

  return (
    <main className="mx-auto flex w-full max-w-sm flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <button className="self-start text-xs font-semibold text-blue-600" onClick={onBack}>← Back</button>
        <h1 className="text-2xl font-bold">Leaderboard</h1>
        <p className="text-sm text-gray-600">{currentGame ? `Best result per player for ${currentGame.name}.` : "Select a game to view the leaderboard."}</p>
      </header>
      <label className="flex flex-col gap-1.5 text-sm text-gray-600">
        Game
        <select className={inputClass} value={gameId} onChange={(e) => setGameId(e.target.value)}>
          {games.length === 0 && <option>Loading...</option>}
          {games.map((game) => <option key={game.id} value={game.id}>{game.name}</option>)}
        </select>
      </label>
      {rows.length === 0 ? (
        <p className="px-1 text-sm text-gray-500">No finalized results yet. Finalize a session to see it here.</p>
      ) : (
        <section className="flex flex-col gap-2">
          {rows.slice(0, 10).map((row) => (
            <div className="flex items-center gap-3 rounded border border-gray-100 bg-white px-3 py-2" key={row.user_id}>
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-gray-100 text-xs font-bold text-gray-600">{row.rank}</span>
              <div className="flex min-w-0 flex-1 flex-col">
                <strong className="truncate text-sm font-semibold">{row.username}</strong>
                <span className="text-[11px] text-gray-400">{row.games_played} games played</span>
              </div>
              <span className="text-lg font-semibold">{row.score}</span>
            </div>
          ))}
        </section>
      )}
    </main>
  );
}
