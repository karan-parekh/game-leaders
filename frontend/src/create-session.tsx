import { type FormEvent, useEffect, useState } from "react";
import { api, messageOf, type Game, type Session } from "./api";
import { useToast } from "./toast";

const inputClass = "rounded border border-gray-300 bg-white px-3 py-2.5 text-gray-900";
const buttonClass = "rounded bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white";

export function CreateSessionScreen({ onCreated, onBack }: { onCreated: (session: Session) => void; onBack: () => void }) {
  const [games, setGames] = useState<Game[]>([]);
  const [gameId, setGameId] = useState("");
  const [capacity, setCapacity] = useState("4");
  const [timeoutMinutes, setTimeoutMinutes] = useState("");
  const showToast = useToast();

  useEffect(() => {
    api.games().then((list) => {
      setGames(list);
      if (list.length > 0) setGameId(list[0].id);
    }).catch((error) => showToast(messageOf(error)));
  }, []);

  const selectedGame = games.find((game) => game.id === gameId);
  const defaultHint = selectedGame ? `Game default (${selectedGame.default_timeout_minutes} min)` : "Game default";

  async function create(event: FormEvent) {
    event.preventDefault();
    try {
      const capacityValue = Number(capacity);
      const timeout = timeoutMinutes === "" ? undefined : Number(timeoutMinutes);
      const session = await api.createSession({ game_id: gameId, capacity: capacityValue, timeout_minutes: timeout });
      onCreated(session);
    } catch (error) {
      showToast(messageOf(error));
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-sm flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <button className="self-start text-xs font-semibold text-blue-600" onClick={onBack}>← Back</button>
        <h1 className="text-2xl font-bold">New session</h1>
        <p className="text-sm text-gray-600">Pick a game, set the table size.</p>
      </header>
      <form onSubmit={create} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-sm text-gray-600">
          Game
          <select className={inputClass} value={gameId} onChange={(e) => setGameId(e.target.value)}>
            {games.length === 0 && <option>Loading...</option>}
            {games.map((game) => <option key={game.id} value={game.id}>{game.name}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-sm text-gray-600">
          Capacity (2–20)
          <input className={inputClass} type="number" min={2} max={20} value={capacity} onChange={(e) => setCapacity(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1.5 text-sm text-gray-600">
          Timeout in minutes (optional)
          <input className={inputClass} type="number" min={5} max={1440} value={timeoutMinutes} onChange={(e) => setTimeoutMinutes(e.target.value)} placeholder={defaultHint} />
        </label>
        <button className={buttonClass} type="submit">Create session</button>
      </form>
    </main>
  );
}