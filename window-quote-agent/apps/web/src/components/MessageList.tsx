import type { Message } from "../types";

interface Props {
  messages: Message[];
}

export function MessageList({ messages }: Props) {
  return (
    <div className="message-list">
      {messages.map((msg, i) => (
        <div key={i} className={`message message--${msg.role}`}>
          <div className="message-inner">
            {msg.role === "assistant" && (
              <div className="message-avatar message-avatar--assistant" />
            )}
            <div className="message-content">
              {msg.role === "assistant" && msg.thinking_steps && msg.thinking_steps.length > 0 && !msg.status && (
                <details className="message-thinking">
                  <summary className="message-thinking-summary">思考过程</summary>
                  <ul className="message-thinking-steps">
                    {msg.thinking_steps.map((step, j) => (
                      <li key={j}>{step}</li>
                    ))}
                  </ul>
                </details>
              )}
              {msg.status === "loading" ? (
                <div className="message-loading">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </div>
              ) : (
                <div className="message-text">{msg.content}</div>
              )}
              {msg.quote_md && (
                <div
                  className="message-quote"
                  dangerouslySetInnerHTML={{ __html: simpleMarkdown(msg.quote_md) }}
                />
              )}
              {msg.current_intent && (
                <div className="message-intent">当前意图: {msg.current_intent}</div>
              )}
              {msg.status === "error" && (
                <div className="message-error">请检查网络或稍后重试</div>
              )}
            </div>
            {msg.role === "user" && (
              <div className="message-avatar message-avatar--user" />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function simpleMarkdown(md: string): string {
  return md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br/>");
}
