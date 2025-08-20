// src/components/ChatInput.js
import React, { useState, useRef, useEffect } from 'react';

const ChatInput = ({ onSendMessage, isLoading, disabled = false }) => {
  const [message, setMessage] = useState('');
  const inputRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
    }
  }, [message]);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!message.trim() || isLoading || disabled) return;
    
    onSendMessage(message);
    setMessage('');
    
    // Reset height and focus
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleChange = (e) => {
    setMessage(e.target.value);
  };

  return (
    <div className="chat-input-container">
      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="input-wrapper">
          <textarea
            ref={inputRef}
            value={message}
            onChange={handleChange}
            onKeyPress={handleKeyPress}
            placeholder="Ask me about Orcutt Schools..."
            disabled={isLoading || disabled}
            rows={1}
            className="message-input"
            style={{ minHeight: '52px', maxHeight: '120px' }}
          />
          
          <button
            type="submit"
            disabled={!message.trim() || isLoading || disabled}
            className="send-button"
            title="Send message"
          >
            {isLoading ? (
              <div className="loading-spinner">⟳</div>
            ) : (
              <span style={{ fontSize: '18px' }}>➤</span>
            )}
          </button>
        </div>
      </form>
      
    </div>
  );
};

export default ChatInput;