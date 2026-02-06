import React, { useState, useEffect, useRef } from 'react';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    let storedId = localStorage.getItem('ivf_session_id');
    if (!storedId) {
      storedId = 'session_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('ivf_session_id', storedId);
    }
    setSessionId(storedId);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleOptionClick = (optionText) => {
    sendMessage(optionText);
  };

  const sendMessage = async (textOverride = null) => {
    const textToSend = textOverride || input;
    if (!textToSend.trim()) return;

    const userMsg = { role: 'user', content: textToSend };
    setMessages((prev) => [...prev, userMsg]);
    if (!textOverride) setInput("");
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: textToSend })
      });

      const data = await response.json();

      // Detect if it is a summary message for special styling
      const isSummary = data.reply.includes("Section A: My Understanding");

      const botMsg = {
        role: 'bot',
        content: data.reply,
        options: data.options || [],
        isSummary: isSummary
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [...prev, { role: 'bot', content: "Error connecting to server." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Premium Mesh Background */}
      <div className="mesh-background">
        <div className="mesh-blob blob-1"></div>
        <div className="mesh-blob blob-2"></div>
      </div>

      <div className="main-chat-area">
        <div className="chat-header">
          <div className="status-dot"></div>
          <h1>Dr. Malpani's AI Assistant</h1>
        </div>

        <div className="messages-container">
          {messages.map((m, i) => (
            <React.Fragment key={i}>
              <div className={`message-wrapper ${m.role}`}>
                <span className="message-sender">{m.role === 'user' ? 'You' : 'Dr. AI'}</span>
                <div className={`message-bubble ${m.isSummary ? 'summary-bubble' : ''}`}>
                  {m.content}
                </div>
              </div>
              {m.role === 'bot' && m.options && m.options.length > 0 && (
                <div className="options-container">
                  {m.options.map((opt, idx) => (
                    <button
                      key={idx}
                      className="option-btn"
                      onClick={() => handleOptionClick(opt)}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              )}
            </React.Fragment>
          ))}
          {isLoading && (
            <div className="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <input
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your medical history..."
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            disabled={isLoading}
          />
          <button className="send-button" onClick={() => sendMessage()} disabled={isLoading || !input.trim()}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;