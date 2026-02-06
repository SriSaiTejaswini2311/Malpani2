import React, { useState, useEffect, useRef } from 'react';
import './ChatWindow.css';

const ChatWindow = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [sessionId, setSessionId] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        // Generate a simple session ID if one doesn't exist
        let storedSessionId = localStorage.getItem('ivf_session_id');
        if (!storedSessionId) {
            storedSessionId = 'session_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('ivf_session_id', storedSessionId);
        }
        setSessionId(storedSessionId);

        // Initial greeting trigger (optional, if backend doesn't send first)
        // For now we'll wait for user or just send a 'Hi' hiddenly if we wanted.
        // But per spec, the bot should lead. Let's send an empty init message to get the opening.
        // actually, let's just let the user say "Hi" or trigger it manually.
        // Better: Send a "start_session" signal or just "Hi" automatically on load if history is empty?
        // Let's stick to simple: User types or we trigger "Hi" on mount.
        // To match screenshot "Dr. Malpani's AI Assistant" header.
    }, []);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleOptionClick = (optionText) => {
        // Send the option as a user message
        sendMessage(optionText);
    };

    const sendMessage = async (textOverride = null) => {
        const textToSend = textOverride || input; // Changed userMessage to input
        if (!textToSend.trim()) return;

        const newMessage = { text: textToSend, sender: 'user' };
        setMessages((prev) => [...prev, newMessage]);
        if (!textOverride) setInput(''); // Changed setUserMessage to setInput
        setIsLoading(true);

        try {
            const response = await fetch('http://127.0.0.1:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, message: textToSend }),
            });

            // Check for network response status
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            // Expect backend to return { reply: "Text", options: ["Op1", "Op2"] }
            const botMessage = {
                text: data.reply,
                sender: 'bot',
                options: data.options || []
            };

            setMessages((prev) => [...prev, botMessage]);
        } catch (error) {
            console.error('Error:', error);
            setMessages((prev) => [...prev, { text: "Error connecting to server.", sender: 'bot' }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    };

    return (
        <div className="chat-container">
            <div className="chat-header">
                <span className="online-indicator">●</span> Dr. Malpani's AI Assistant
            </div>
            <div className="messages-area">
                {messages.map((msg, index) => (
                    <React.Fragment key={index}>
                        <div className={`message ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`}>
                            <div className="message-bubble">
                                {msg.text}
                            </div>
                        </div>
                        {msg.options && (
                            <div className="options-container" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '4px', marginLeft: '10px' }}>
                                {msg.options.map((option, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => handleOptionClick(option)}
                                        style={{
                                            padding: '8px 16px',
                                            borderRadius: '18px',
                                            border: '1px solid #007bff',
                                            backgroundColor: 'white',
                                            color: '#007bff',
                                            cursor: 'pointer',
                                            fontSize: '0.9rem'
                                        }}
                                    >
                                        {option}
                                    </button>
                                ))}
                            </div>
                        )}
                    </React.Fragment>
                ))}
                {isLoading && <div className="typing-indicator">Typing...</div>}
                <div ref={messagesEndRef} />
            </div>
            <div className="input-area">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Type your medical history..."
                />
                <button onClick={sendMessage} disabled={isLoading}>Send</button>
            </div>
        </div>
    );
};

export default ChatWindow;
