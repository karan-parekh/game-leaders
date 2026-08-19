import { type FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Session = { id: string; name: string; state: string; revision: number; participants: { username: string; scores: Record<string, number> }[] };

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [room, setRoom] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session) return;
    const stream = new EventSource(`/api/sessions/${session.id}/events`);
    stream.addEventListener("snapshot", (event) => setSession(JSON.parse((event as MessageEvent).data)));
    stream.onerror = () => setError("Live connection interrupted. Reconnecting...");
    return () => stream.close();
  }, [session?.id]);

  async function openRoom(event: FormEvent) {
    event.preventDefault();
    setError("");
    const response = await fetch(`/api/sessions/${room}`);
    if (!response.ok) return setError("Room not found");
    setSession(await response.json());
  }

  return <main>
    <header><span className="eyebrow">GAME LEADERS</span><h1>Local tables.<br /><em>Lasting bragging rights.</em></h1><p>Track the score together, then see who rules the table.</p></header>
    {!session ? <form onSubmit={openRoom} className="room-form"><label htmlFor="room">Join a room</label><div><input id="room" value={room} onChange={(event) => setRoom(event.target.value)} placeholder="6-character code" /><button>Open room</button></div>{error && <small>{error}</small>}</form> : <section className="table"><div className="table-head"><div><span className="eyebrow">LIVE SESSION</span><h2>{session.name}</h2></div><span className="state">{session.state} · v{session.revision}</span></div><div className="players">{session.participants.map((player) => <article key={player.username}><strong>{player.username}</strong><span>{player.scores.points ?? 0}</span></article>)}</div></section>}
  </main>;
}

createRoot(document.getElementById("root")!).render(<App />);
