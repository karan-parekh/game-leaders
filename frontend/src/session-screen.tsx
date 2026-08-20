import { useEffect, useState } from "react";
import { api, messageOf, type Me, type Session } from "./api";
import { rankOf as rankForUser, rankParticipants, totalScore } from "./session-ranking";
import { useToast } from "./toast";

const STATE_LABELS: Record<string, string> = {
  setup: "setup",
  live: "live",
  timed_out: "timed out",
  finalized: "finalized",
  discarded: "discarded",
};

function stateLabel(state: string) {
  return STATE_LABELS[state] ?? state;
}

function rankOf(session: Session, userId: string) {
  return rankForUser(session.participants, session.ranking_direction, userId);
}

function ScoreActions({ session, metric, disabled, onDelta, onCustom }: {
  session: Session;
  metric: string;
  disabled: boolean;
  onDelta: (delta: number) => void;
  onCustom: () => void;
}) {
  const base = "rounded border border-gray-300 bg-white font-semibold text-gray-800 active:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40";
  return <div className="mt-3 flex w-full flex-col gap-2" aria-label="Update your score">
    <div className="flex w-full gap-2">
      <button className={`${base} flex-1 py-2.5 text-sm`} disabled={disabled} onClick={() => onDelta(1)}>+1</button>
      <button className={`${base} flex-1 py-2.5 text-sm`} disabled={disabled} onClick={() => onDelta(5)}>+5</button>
      <button className={`${base} flex-1 py-2.5 text-sm`} disabled={disabled} onClick={() => onDelta(10)}>+10</button>
    </div>
    <button className={`${base} w-full border-gray-200 bg-gray-50 py-2 text-xs`} disabled={disabled} onClick={onCustom}>Custom</button>
  </div>;
}

export function SessionScreen({ sessionId, me, onFinished }: { sessionId: string; me: Me | null; onFinished: () => void }) {
  const [session, setSession] = useState<Session | null>(null);
  const [connection, setConnection] = useState<"live" | "offline">("live");
  const [selectedMetric, setSelectedMetric] = useState("");
  const [customOpen, setCustomOpen] = useState(false);
  const [customValue, setCustomValue] = useState("");
  const showToast = useToast();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        let snapshot = await api.getSession(sessionId);
        const isHost = me?.id === snapshot.host_id;
        const isActiveMember = snapshot.participants.some((p) => p.active && p.user_id === me?.id);
        if (!isHost && !isActiveMember && me) snapshot = await api.joinSession(sessionId);
        if (!cancelled) {
          setSession(snapshot);
          setSelectedMetric(snapshot.metrics[0]?.id ?? "");
        }
      } catch (error) {
        showToast(messageOf(error));
        onFinished();
      }
    })();
    return () => { cancelled = true; };
  }, [sessionId]);

  useEffect(() => {
    if (!session) return;
    const isHost = session.host_id === me?.id;
    const isActiveMember = session.participants.some((p) => p.active && p.user_id === me?.id);
    if (!isHost && !isActiveMember) {
      setConnection("offline");
      return;
    }
    setConnection("live");
    const stream = new EventSource(`/api/sessions/${session.id}/events`);
    stream.addEventListener("snapshot", (event) => {
      const next = JSON.parse((event as MessageEvent).data) as Session;
      if (next.state === "discarded") {
        showToast("Session discarded");
        onFinished();
        return;
      }
      setSession(next);
      setConnection("live");
    });
    stream.onerror = () => {
      setConnection("offline");
      showToast("Live connection interrupted. Reconnecting...");
    };
    return () => stream.close();
  }, [session?.id]);

  if (!session || !me) {
    return <main className="mx-auto flex max-w-sm px-6 py-16 text-sm text-gray-500">Loading session...</main>;
  }

  const isHost = session.host_id === me.id;
  const self = session.participants.find((p) => p.user_id === me.id && p.active);
  const others = rankParticipants(session.participants, session.ranking_direction).filter((p) => p.user_id !== me.id);
  const currentMetric = session.metrics.find((m) => m.id === selectedMetric) ?? session.metrics[0];
  const scoresEditable = session.state === "live" || session.state === "timed_out";
  const selfScore = self ? (self.scores[selectedMetric] ?? 0) : 0;
  const deadline = session.deadline ? new Date(session.deadline).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : null;

  const applyDelta = async (delta: number) => {
    if (!self) return;
    try {
      const next = await api.updateScore(session.id, me.id, selectedMetric, selfScore + delta);
      setSession(next);
    } catch (error) {
      showToast(messageOf(error));
    }
  };

  const applyCustom = async () => {
    const value = Number(customValue);
    setCustomOpen(false);
    setCustomValue("");
    if (!self || Number.isNaN(value)) return;
    try {
      const next = await api.updateScore(session.id, me.id, selectedMetric, value);
      setSession(next);
    } catch (error) {
      showToast(messageOf(error));
    }
  };

  const hostAction = async (action: "start" | "finalize" | "discard") => {
    try {
      if (action === "discard") {
        await api.discardSession(session.id);
        showToast("Session discarded");
        onFinished();
        return;
      }
      const next = await (action === "start" ? api.startSession(session.id) : api.finalizeSession(session.id));
      setSession(next);
    } catch (error) {
      showToast(messageOf(error));
    }
  };

  const leave = async () => {
    try {
      await api.leaveSession(session.id);
      onFinished();
    } catch (error) {
      showToast(messageOf(error));
    }
  };

  return <div className="flex min-h-screen flex-col bg-gray-50 text-gray-900">
    <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
      <div className="flex flex-col gap-0.5">
        <span className="text-sm font-semibold">{session.name}</span>
        <span className="font-mono text-[11px] text-gray-400">{session.room_code}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className={`flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs font-semibold ${connection === "offline" ? "text-red-600" : "text-gray-500"}`}>
          <i className={`h-1.5 w-1.5 rounded-full ${connection === "live" ? "bg-green-500" : "bg-red-500"}`} />
          {connection === "live" ? "Live" : "No live connection"}
        </span>
        <span className="rounded bg-gray-100 px-2 py-1 text-[11px] font-semibold uppercase text-gray-500">{stateLabel(session.state)}</span>
      </div>
    </header>

    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col items-center gap-5 px-4 py-6">
      {isHost && (
        <div className="flex w-full max-w-xs flex-wrap items-center justify-center gap-2">
          {session.state === "setup" && <button className="rounded bg-blue-600 px-4 py-2 text-xs font-semibold text-white" onClick={() => hostAction("start")}>Start session</button>}
          {(session.state === "live" || session.state === "timed_out") && (
            <>
              <button className="rounded bg-green-600 px-4 py-2 text-xs font-semibold text-white" onClick={() => hostAction("finalize")}>Finalize</button>
              <button className="rounded border border-gray-300 bg-white px-4 py-2 text-xs font-semibold text-gray-700" onClick={() => hostAction("discard")}>Discard</button>
            </>
          )}
          <span className="text-[11px] text-gray-400">You host · v{session.revision}</span>
        </div>
      )}

      <div className="flex flex-col items-center gap-1 text-center">
        <p className="text-xs font-semibold uppercase tracking-widest text-gray-500">{session.metrics[0]?.label ?? "Score"}</p>
        <p className="text-sm text-gray-600">{scoresEditable ? "Tap your score to update." : `Session is ${stateLabel(session.state)}.`}</p>
        {deadline && session.state === "live" && <p className="text-[11px] text-gray-400">Ends {deadline}</p>}
      </div>

      {self ? (
        <section className="flex w-full max-w-xs flex-col items-center gap-2 rounded-lg border border-gray-200 bg-white p-4" aria-label="Your score">
          <div className="flex w-full items-center justify-between">
            <span className="flex h-9 w-9 items-center justify-center rounded border border-gray-300 bg-gray-100 text-xs font-bold text-gray-600">{self.username.slice(0, 2).toUpperCase()}</span>
            <span className="rounded bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-600">#{rankOf(session, me.id)}</span>
          </div>
          <span className="text-7xl font-bold leading-none tracking-tight">{selfScore}</span>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">{currentMetric?.label}</span>
          <ScoreActions session={session} metric={selectedMetric} disabled={!scoresEditable} onDelta={applyDelta} onCustom={() => setCustomOpen(true)} />
        </section>
      ) : (
        <section className="flex w-full max-w-xs flex-col items-center gap-2 rounded-lg border border-gray-200 bg-white p-4" aria-label="Your score">
          <span className="text-5xl font-bold leading-none tracking-tight">—</span>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">Not a participant</span>
        </section>
      )}

      {session.metrics.length > 1 && (
        <div className="flex w-full max-w-xs gap-2 overflow-x-auto">
          {session.metrics.map((m) => (
            <button className={`rounded border px-3 py-1.5 text-[11px] font-semibold whitespace-nowrap ${m.id === selectedMetric ? "border-blue-600 bg-blue-600 text-white" : "border-gray-300 bg-white text-gray-600"}`} key={m.id} onClick={() => setSelectedMetric(m.id)}>{m.label}</button>
          ))}
        </div>
      )}

      <section className="flex w-full max-w-xs flex-col gap-2">
        <div className="flex items-baseline justify-between px-1">
          <h2 className="text-sm font-semibold">Players</h2>
          <span className="font-mono text-[11px] text-gray-400">{session.participants.filter((p) => p.active).length}/{session.capacity}</span>
        </div>
        {others.map((p, i) => (
          <div className="flex items-center gap-3 rounded border border-gray-100 bg-white px-3 py-2" key={p.user_id}>
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-gray-200 bg-gray-50 text-[11px] font-bold text-gray-500">{p.username.slice(0, 2).toUpperCase()}</span>
            <div className="flex min-w-0 flex-1 flex-col">
              <strong className="truncate text-sm font-semibold">{p.username}</strong>
              <span className="text-[11px] text-gray-400">#{i + 2}</span>
            </div>
            <span className="text-lg font-semibold">{totalScore(p)}</span>
          </div>
        ))}
      </section>

      {!isHost && (
        <button className="rounded border border-gray-300 bg-white px-4 py-2 text-xs font-semibold text-gray-700" onClick={leave}>Leave session</button>
      )}
    </main>

    {customOpen && <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/30 p-6" role="presentation">
      <form className="flex w-full max-w-xs flex-col gap-3 rounded-lg border border-gray-200 bg-white p-5" onSubmit={(e) => { e.preventDefault(); applyCustom(); }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-400">Custom score</p>
        <h2 className="text-lg font-semibold">Set your score</h2>
        <p className="text-sm text-gray-500">Replaces your total for {currentMetric?.label}.</p>
        <label className="text-xs font-semibold text-gray-600" htmlFor="custom-score">New total</label>
        <input id="custom-score" type="number" autoFocus className="rounded border border-gray-300 bg-gray-50 px-3 py-2 font-mono text-lg text-gray-900" value={customValue} onChange={(e) => setCustomValue(e.target.value)} />
        <div className="flex justify-end gap-2">
          <button type="button" className="rounded border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-600" onClick={() => setCustomOpen(false)}>Cancel</button>
          <button type="submit" className="rounded bg-blue-600 px-3 py-2 text-xs font-semibold text-white">Set score</button>
        </div>
      </form>
    </div>}
  </div>;
}
