import { useState, useRef, useEffect } from "react";
import "./App.css";
import { ChatInput } from "./components/ChatInput";
import { MessageList } from "./components/MessageList";
import type { Message } from "./types";

const API_BASE = "/api";

async function sendMessage(
  message: string,
  sessionId: string | null
): Promise<{
  reply: string;
  quote_md?: string;
  current_intent?: string;
  session_id: string;
  thinking_steps?: string[];
}> {
  const body: { message: string; session_id?: string } = { message };
  if (sessionId) body.session_id = sessionId;
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "请求失败");
  }
  return res.json();
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef<string | null>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMessage: Message = { role: "user", content: text.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "", status: "loading" }]);

    try {
      const data = await sendMessage(text.trim(), sessionIdRef.current);
      if (data.session_id) sessionIdRef.current = data.session_id;
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant" && last?.status === "loading") {
          next[next.length - 1] = {
            role: "assistant",
            content: data.reply,
            quote_md: data.quote_md,
            current_intent: data.current_intent,
            thinking_steps: data.thinking_steps ?? undefined,
          };
        }
        return next;
      });
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : "网络错误，请稍后重试";
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant" && last?.status === "loading") {
          next[next.length - 1] = { role: "assistant", content: errMsg, status: "error" };
        }
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="app">
      <header className="header">
        <div className="header-title">
          <span>智能报价助手</span>
          <span className="header-arrow">▼</span>
        </div>
      </header>

      <main className="main">
        {isEmpty ? (
          <div className="welcome">
            <p className="welcome-text">准备好了，随时开始</p>
          </div>
        ) : (
          <div className="messages-wrap" ref={listRef}>
            <MessageList messages={messages} />
          </div>
        )}
      </main>

      <footer className="footer">
        <ChatInput onSend={handleSend} disabled={loading} placeholder="有问题，尽管问" />
      </footer>
    </div>
  );
}
