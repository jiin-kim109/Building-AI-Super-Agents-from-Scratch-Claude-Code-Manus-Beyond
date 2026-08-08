import { useEffect, useLayoutEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

const socketUrl = () => {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${location.host}/ws`;
};

export default function App() {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);

  const socketRef = useRef(null);
  const threadRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const socket = new WebSocket(socketUrl());

    socket.onopen = () => setReady(true);
    socket.onclose = () => setReady(false);

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === "idle") {
        setBusy(false);
        return;
      }

      setMessages((current) => [...current, message]);
    };

    socketRef.current = socket;
    return () => socket.close();
  }, []);

  useLayoutEffect(() => {
    const thread = threadRef.current;
    if (thread) {
      thread.scrollTop = thread.scrollHeight;
    }
  }, [messages, busy]);

  const send = (event) => {
    event.preventDefault();

    const text = draft.trim();
    if (!text || busy || !ready) return;

    socketRef.current.send(JSON.stringify({ text }));
    setDraft("");
    setBusy(true);
    inputRef.current?.focus();
  };

  const onKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      send(event);
    }
  };

  const started = messages.length > 0;

  return (
    <div className={started ? "shell" : "shell shell--empty"}>
      {started && (
        <main className="thread" ref={threadRef}>
          <ol className="messages">
            {messages.map((message) => (
              <li key={message.id} className={`message message--${message.type}`}>
                {message.type === "human" ? (
                  <p className="human">{message.text}</p>
                ) : (
                  <div className="prose">
                    <Markdown remarkPlugins={[remarkGfm]}>{message.text}</Markdown>
                  </div>
                )}
              </li>
            ))}

            {busy && (
              <li className="message message--pending" aria-live="polite">
                <span className="pulse">
                  <i />
                  <i />
                  <i />
                </span>
                <span className="visually-hidden">Working</span>
              </li>
            )}
          </ol>
        </main>
      )}

      <form className="composer" onSubmit={send}>
        <label className="visually-hidden" htmlFor="draft">
          Message
        </label>

        <textarea
          id="draft"
          ref={inputRef}
          className="input"
          value={draft}
          rows={1}
          autoFocus
          placeholder="Ask anything"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
        />

        <button className="send" type="submit" disabled={!draft.trim() || busy || !ready}>
          <span className="visually-hidden">Send</span>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M6 12h11m0 0-4.2-4.2M17 12l-4.2 4.2"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.9"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </form>
    </div>
  );
}
