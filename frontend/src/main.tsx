import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, type Me } from "./api";
import { ToastProvider } from "./toast";
import { LoginScreen, RegisterScreen } from "./auth";
import { HomeScreen } from "./home";
import { CreateSessionScreen } from "./create-session";
import { SessionScreen } from "./session-screen";
import { LeaderboardScreen } from "./leaderboard";
import "./styles.css";

type Screen =
  | { name: "landing" }
  | { name: "login" }
  | { name: "register" }
  | { name: "home" }
  | { name: "create" }
  | { name: "session"; id: string }
  | { name: "leaderboard" };

function pathFor(screen: Screen) {
  switch (screen.name) {
    case "landing": return "/";
    case "login": return "/login";
    case "register": return "/register";
    case "home": return "/home";
    case "create": return "/create";
    case "session": return `/session/${screen.id}`;
    case "leaderboard": return "/leaderboard";
  }
}

function screenForPath(path: string): Screen {
  if (path.startsWith("/session/")) return { name: "session", id: path.slice("/session/".length) };
  if (path === "/login") return { name: "login" };
  if (path === "/register") return { name: "register" };
  if (path === "/home") return { name: "home" };
  if (path === "/create") return { name: "create" };
  if (path === "/leaderboard") return { name: "leaderboard" };
  return { name: "landing" };
}

function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [screen, setScreen] = useState<Screen>(() => screenForPath(window.location.pathname));
  const [notice, setNotice] = useState("");

  useEffect(() => {
    api.me().then(setMe).catch(() => setMe(null)).finally(() => setAuthChecked(true));
  }, []);

  useEffect(() => {
    if (!authChecked) return;
    if (me && screen.name === "landing") {
      setScreen({ name: "home" });
      window.history.replaceState({}, "", "/home");
    }
    if (!me && screen.name !== "landing" && screen.name !== "login" && screen.name !== "register" && screen.name !== "leaderboard") {
      setScreen({ name: "landing" });
      window.history.replaceState({}, "", "/");
    }
  }, [authChecked, me, screen]);

  useEffect(() => {
    const onPop = () => setScreen(screenForPath(window.location.pathname));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = (next: Screen) => {
    setScreen(next);
    window.history.pushState({}, "", pathFor(next));
  };

  if (!authChecked) {
    return <main className="mx-auto flex max-w-sm px-6 py-16 text-sm text-gray-500">Loading...</main>;
  }

  let content: React.ReactNode;
  switch (screen.name) {
    case "landing":
      content = (
        <main className="mx-auto flex max-w-2xl flex-col gap-10 px-6 py-16">
          <header className="flex flex-col gap-2">
            <span className="text-xs font-semibold uppercase tracking-widest text-gray-500">Game Leaders</span>
            <h1 className="text-5xl font-bold leading-tight">Local tables.<br /><em className="text-blue-600 not-italic">Lasting bragging rights.</em></h1>
            <p className="text-gray-600">Track the score together, then see who rules the table.</p>
          </header>
          <div className="flex flex-col gap-3">
            <button className="rounded bg-blue-600 px-4 py-3 text-sm font-semibold text-white" onClick={() => navigate({ name: "login" })}>Log in</button>
            <button className="rounded border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-800" onClick={() => navigate({ name: "register" })}>Register</button>
            <button className="rounded border border-gray-200 bg-gray-50 px-4 py-3 text-sm font-semibold text-gray-600" onClick={() => navigate({ name: "leaderboard" })}>View Leaderboard</button>
          </div>
        </main>
      );
      break;
    case "login":
      content = (
        <LoginScreen
          notice={notice}
          onSuccess={async () => {
            try {
              setMe(await api.me());
            } catch {
              setMe(null);
            }
            navigate({ name: "home" });
          }}
          onRegister={() => navigate({ name: "register" })}
        />
      );
      break;
    case "register":
      content = (
        <RegisterScreen
          onSuccess={() => { setNotice("Account created. Log in."); navigate({ name: "login" }); }}
          onLogin={() => navigate({ name: "login" })}
        />
      );
      break;
    case "home":
      content = <HomeScreen me={me} onOpenSession={(id) => navigate({ name: "session", id })} onCreate={() => navigate({ name: "create" })} onLeaderboard={() => navigate({ name: "leaderboard" })} onLogout={async () => { try { await api.logout(); } finally { setMe(null); navigate({ name: "landing" }); } }} />;
      break;
    case "create":
      content = <CreateSessionScreen onCreated={(session) => navigate({ name: "session", id: session.id })} onBack={() => navigate({ name: "home" })} />;
      break;
    case "session":
      content = <SessionScreen sessionId={screen.id} me={me} onFinished={() => navigate({ name: "home" })} />;
      break;
    case "leaderboard":
      content = <LeaderboardScreen onBack={() => navigate(me ? { name: "home" } : { name: "landing" })} />;
      break;
  }

  return <ToastProvider>{content}</ToastProvider>;
}

createRoot(document.getElementById("root")!).render(<App />);