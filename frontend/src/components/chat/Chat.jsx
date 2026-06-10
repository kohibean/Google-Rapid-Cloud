import { forwardRef, useImperativeHandle, useRef, useState } from "react";
import SectionLabel from "../layout/SectionLabel";
import Message from "./Message";
import Composer from "./Composer";
import QuickActions from "./QuickActions";
import { sendMessage, extractReply, fileToBase64 } from "../../lib/api";

const Chat = forwardRef(({ sessionId, onAgentMessage }, ref) => {
  const [messages, setMessages] = useState([
    {
      who: "agent",
      text: "Welcome back to the studio. Tell me you're starting a session, drop an image of your work, or ask me where you left off on any piece.",
    },
  ]);
  const [thinking, setThinking] = useState(false);
  const [prefill, setPrefill] = useState("");
  const scroller = useRef(null);

  useImperativeHandle(ref, () => ({
    prefill: (text) => setPrefill(text),
  }));

  function scrollToEnd() {
    requestAnimationFrame(() => {
      if (scroller.current) scroller.current.scrollTop = scroller.current.scrollHeight;
    });
  }

  async function send({ text, image }) {
    if (!text && !image) return;
    const parts = [{ text: text || "Please analyze this artwork." }];

    if (image) {
      const b64 = await fileToBase64(image);
      parts.push({ inlineData: { mimeType: image.type, data: b64 } });
      setMessages((m) => [...m, { who: "user", text: `🖼  attached: ${image.name}` }]);
    }
    if (text) setMessages((m) => [...m, { who: "user", text }]);
    scrollToEnd();

    setThinking(true);
    try {
      const events = await sendMessage(sessionId, parts);
      const reply = extractReply(events) || "(no response)";
      const isBriefing = /welcome back/i.test(reply);
      setMessages((m) => [...m, { who: "agent", text: reply, briefing: isBriefing }]);
      onAgentMessage?.(reply);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { who: "agent", text: `Something went wrong reaching the agent. (${e.message})` },
      ]);
    } finally {
      setThinking(false);
      scrollToEnd();
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-180px)] min-h-[560px]">
      <SectionLabel no="II.">Studio Companion</SectionLabel>

      <div
        ref={scroller}
        className="flex-1 overflow-y-auto pr-2 space-y-5"
      >
        {messages.map((m, i) => (
          <Message key={i} {...m} />
        ))}
        {thinking && (
          <p className="font-serif italic text-ink-soft border-l-2 border-rule pl-4 py-1">
            consulting the studio memory<span className="animate-pulse">…</span>
          </p>
        )}
      </div>

      <QuickActions onPick={setPrefill} />
      <Composer onSend={send} prefill={prefill} onPrefillUsed={() => setPrefill("")} disabled={thinking} />
    </div>
  );
});

Chat.displayName = "Chat";
export default Chat;
