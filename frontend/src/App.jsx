import { useState } from 'react';
const API_URL = import.meta.env.VITE_API_URL;

const starterMessages = [
  {
    role: 'assistant',
    content:
      'Hello! Ask me anything about the demo database. I can follow up on earlier questions in the same chat.',
  },
];

function createSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}`;
}

function App() {
  const [messages, setMessages] = useState(starterMessages);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(createSessionId);

  const handleSend = async (event) => {
    event.preventDefault();

    const trimmed = input.trim();
    if (!trimmed || loading) {
      return;
    }

    const userMessage = { role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: trimmed }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'The chat service is unavailable right now.');
      }

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          sql: data.sql,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, I hit an error: ${error.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const startNewChat = () => {
    setMessages(starterMessages);
    setInput('');
    setLoading(false);
    setSessionId(createSessionId());
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Demo UI</p>
          <h1>Chat with your database</h1>
          <p className="subtitle">
            Ask follow-up questions and keep the conversation going in the same session.
          </p>
        </div>
        <button type="button" onClick={startNewChat} className="ghost-button">
          New chat
        </button>
      </header>

      <main className="chat-card">
        <div className="message-list">
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`message-row ${message.role}`}>
              <div className="message-bubble">
                <div className="message-role">{message.role === 'user' ? 'You' : 'Assistant'}</div>
                <div className="message-content">{message.content}</div>
                {message.sql ? <pre className="sql-block">{message.sql}</pre> : null}
              </div>
            </div>
          ))}
          {loading ? (
            <div className="message-row assistant">
              <div className="message-bubble loading">Thinking…</div>
            </div>
          ) : null}
        </div>

        <form onSubmit={handleSend} className="composer">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about customers, orders, products, or reviews..."
            autoFocus
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Sending…' : 'Send'}
          </button>
        </form>
      </main>
    </div>
  );
}

export default App;
