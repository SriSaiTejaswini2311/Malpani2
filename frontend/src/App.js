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
      const botMsg = {
        role: 'bot',
        content: data.reply,
        options: data.options || []
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
                <div className="message-bubble">
                  {m.content}
                </div>
              </div>
              {m.role === 'bot' && m.options && m.options.length > 0 && (
                <div className="options-container" style={{
                  display: 'flex',
                  gap: '10px',
                  flexWrap: 'wrap',
                  marginTop: '10px',
                  paddingLeft: '40px'
                }}>
                  {m.options.map((opt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleOptionClick(opt)}
                      style={{
                        padding: '10px 20px',
                        borderRadius: '20px',
                        border: '1px solid var(--primary-accent)',
                        background: 'rgba(6, 182, 212, 0.1)',
                        color: 'var(--primary-accent)',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        transition: 'all 0.2s'
                      }}
                      onMouseOver={(e) => {
                        e.target.style.background = 'var(--primary-accent)';
                        e.target.style.color = 'white';
                      }}
                      onMouseOut={(e) => {
                        e.target.style.background = 'rgba(6, 182, 212, 0.1)';
                        e.target.style.color = 'var(--primary-accent)';
                      }}
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
          <button className="send-button" onClick={() => sendMessage()} disabled={isLoading}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;