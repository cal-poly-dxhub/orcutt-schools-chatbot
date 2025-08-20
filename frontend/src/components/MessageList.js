// src/components/MessageList.js
import React, { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';

const MessageList = ({ messages, isLoading, sessionId }) => {
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.length === 0 && (
        <div className="welcome-message">
          <h3>Welcome to Orcutt Schools Assistant!</h3>
          <p>I'm here to help you with information about our schools. Ask me about:</p>
          <ul>
            <li>Academic programs and curriculum</li>
            <li>School hours and schedules</li>
            <li>Contact information and staff directory</li>
            <li>Sports and extracurricular activities</li>
            <li>Transportation and bus routes</li>
            <li>Lunch menus and nutrition</li>
            <li>School calendar and events</li>
            <li>Enrollment and registration</li>
          </ul>
        </div>
      )}
      
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} sessionId={sessionId} />
      ))}
      
      {isLoading && (
        <div className="loading-message">
          <div className="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <span>Assistant is typing...</span>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;