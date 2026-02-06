import React, { useState } from 'react';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isPaused, setIsPaused] = useState(false);

  const sendMessage = async () => {
    if (!input) return;

    const newMessages = [...messages, { role: 'user', content: input }];
    setMessages(newMessages);
    setInput("");

    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: "test-session", message: input })
    });

    const data = await response.json();

    // Check if we hit the Day 3 "Summarize & Confirm" Checkpoint
    if (data.reply.includes("Section A: My Understanding")) {
      setIsPaused(true);
    }

    setMessages([...newMessages, { role: 'bot', content: data.reply }]);
  };

  return (
    <div className="app-container">
      {/* Main Chat Area */}
      <div className="main-chat-area">
        {/* Header */}
        <div className="chat-header">
          <div className="status-dot"></div>
          <h1>Dr. Malpani's AI Assistant</h1>
        </div>

        {/* Messages */}
        <div className="messages-container">
          {messages.map((m, i) => (
            <div key={i} className={`message-wrapper ${m.role}`}>
              <span className="message-sender">{m.role === 'user' ? 'You' : 'Dr. AI'}</span>
              <div className="message-bubble">
                {m.content}
              </div>
            </div>
          ))}
          {/* Invisible ref for auto-scroll could go here */}
        </div>

        {/* Input Area */}
        <div className="input-area">
          <input
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isPaused ? "Please confirm the summary above..." : "Type your medical history..."}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          />
          <button className="send-button" onClick={sendMessage}>
            {isPaused ? "Confirm" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;