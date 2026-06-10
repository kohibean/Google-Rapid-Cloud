import { useEffect, useRef, useState } from "react";
import Masthead from "./components/layout/Masthead";
import Gallery from "./components/gallery/Gallery";
import Chat from "./components/chat/Chat";
import ConnectionBanner from "./components/ui/ConnectionBanner";
import Settings from "./components/ui/Settings";
import { createSession, pingServer } from "./lib/api";

export default function App() {
  const [sessionId] = useState(() => `sess_${Date.now()}`);
  const [conn, setConn] = useState({ state: "connecting", message: "" });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [pieces, setPieces] = useState(() => {
    try { return JSON.parse(localStorage.getItem("siningai_pieces") || "[]"); }
    catch { return []; }
  });
  const chatRef = useRef(null);

  async function connect() {
    setConn({ state: "connecting", message: "" });
    try {
      await pingServer();
      await createSession(sessionId);
      setConn({ state: "ok", message: "connected to studio companion" });
    } catch (e) {
      setConn({
        state: "bad",
        message: "can't reach ADK server — run `adk api_server --allow_origins \"*\"` and check the URL in settings",
      });
    }
  }

  useEffect(() => { connect(); /* eslint-disable-next-line */ }, []);

  // Pieces are persisted to localStorage; Chat reports updates via this callback
  function onAgentMessage(text) {
    setPieces(prev => {
      const next = [...prev];
      const save = text.match(/version\s+(\d+)\s+of\s+['"]([^'"]+)['"]\s+at\s+(\w+)/i);
      if (save) {
        const [, num, title, stage] = save;
        let p = next.find(x => x.title.toLowerCase() === title.toLowerCase());
        if (!p) { p = { title, versions: 0, stage: "sketch" }; next.push(p); }
        p.versions = Math.max(p.versions, parseInt(num, 10));
        p.stage = stage;
      }
      const start = text.match(/session started for\s+['"]([^'"]+)['"]/i);
      if (start) {
        const title = start[1];
        if (!next.find(x => x.title.toLowerCase() === title.toLowerCase())) {
          next.push({ title, versions: 0, stage: "sketch" });
        }
      }
      localStorage.setItem("siningai_pieces", JSON.stringify(next));
      return next;
    });
  }

  function askAbout(title) {
    chatRef.current?.prefill(`Where was I on ${title}`);
  }

  return (
    <div className="min-h-screen">
      <Masthead onSettings={() => setSettingsOpen(true)} />
      <ConnectionBanner conn={conn} />

      <main className="max-w-page mx-auto px-8 lg:px-12 pt-10 pb-16
                       grid grid-cols-12 gap-10 lg:gap-14">
        <section className="col-span-12 lg:col-span-7">
          <Gallery pieces={pieces} onAskAbout={askAbout} />
        </section>
        <section className="col-span-12 lg:col-span-5 lg:border-l lg:border-rule lg:pl-14">
          <Chat
            ref={chatRef}
            sessionId={sessionId}
            onAgentMessage={onAgentMessage}
          />
        </section>
      </main>

      {settingsOpen && (
        <Settings onClose={() => setSettingsOpen(false)} onSaved={connect} />
      )}
    </div>
  );
}
