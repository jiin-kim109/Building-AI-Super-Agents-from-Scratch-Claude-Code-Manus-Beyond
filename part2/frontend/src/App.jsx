import { useEffect, useLayoutEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

const socketUrl = () => {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${location.host}/ws`;
};

function ToolCall({ message }) {
  return (
    <p className="tool">
      <span className="tool-dot" />
      {message.description}
    </p>
  );
}

function Interrupt({ message, onAnswer, answered }) {
  const [values, setValues] = useState({});

  const questions = message.request?.questions || [];
  const complete = questions.every((q) => (values[q.id] || "").trim());

  const submit = (event) => {
    event.preventDefault();
    if (!complete || answered) return;

    onAnswer(
      questions.map((q) => ({ question: q.question, answer: values[q.id] }))
    );
  };

  return (
    <form className={answered ? "ask ask--done" : "ask"} onSubmit={submit}>
      {questions.map((q) => (
        <fieldset key={q.id} className="ask-q">
          <legend>{q.question}</legend>

          {q.type === "select" ? (
            <div className="options">
              {q.options.map((option) => (
                <button
                  key={option}
                  type="button"
                  disabled={answered}
                  className={values[q.id] === option ? "option is-on" : "option"}
                  onClick={() => setValues((v) => ({ ...v, [q.id]: option }))}
                >
                  {option}
                </button>
              ))}
            </div>
          ) : (
            <input
              className="ask-input"
              disabled={answered}
              value={values[q.id] || ""}
              placeholder="Type your answer"
              onChange={(e) =>
                setValues((v) => ({ ...v, [q.id]: e.target.value }))
              }
            />
          )}
        </fieldset>
      ))}

      {!answered && (
        <button className="ask-send" disabled={!complete}>
          Send
        </button>
      )}
    </form>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [answered, setAnswered] = useState({});

  const socketRef = useRef(null);
  const threadRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const socket = new WebSocket(socketUrl());

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
    if (thread) thread.scrollTop = thread.scrollHeight;
  }, [messages, busy]);

  const send = (event) => {
    event.preventDefault();

    const text = draft.trim();
    if (!text || busy) return;

    socketRef.current.send(JSON.stringify({ text }));
    setDraft("");
    setBusy(true);
    inputRef.current?.focus();
  };

  const answer = (id, answers) => {
    setAnswered((a) => ({ ...a, [id]: true }));
    setBusy(true);
    socketRef.current.send(
      JSON.stringify({ type: "interrupt_response", answer: answers })
    );
  };

  const started = messages.length > 0;

  return (
    <div className={started ? "shell" : "shell shell--empty"}>
      {started && (
        <main className="thread" ref={threadRef}>
          <ol className="messages">
            {messages.map((message) => (
              <li key={message.id} className={`message message--${message.type}`}>
                {message.type === "human" && <p className="human">{message.text}</p>}

                {message.type === "tool" && <ToolCall message={message} />}

                {message.type === "interrupt" && (
                  <Interrupt
                    message={message}
                    answered={answered[message.id]}
                    onAnswer={(answers) => answer(message.id, answers)}
                  />
                )}

                {(message.type === "text" || message.type === "error") && (
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
              </li>
            )}
            <div />
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
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) send(event);
          }}
        />

        <button className="send" type="submit" disabled={!draft.trim() || busy}>
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
