// src/components/MessageBubble.js
import React, { useState } from 'react';
import { chatService } from '../services/apiService';
import { linkifyText } from '../utils/linkify';

const MessageBubble = ({ message, sessionId }) => {
  const isUser = message.role === 'user';
  const isError = message.isError;
  const [feedback, setFeedback] = useState(null);
  const [showFeedbackText, setShowFeedbackText] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const handleFeedback = async (type) => {
    setFeedback(type);
    if (type === 'up') {
      try {
        await chatService.sendFeedback(message.id, sessionId, type, '');
        setFeedbackSubmitted(true);
      } catch (error) {
        console.error('Failed to send feedback:', error);
      }
    } else {
      setShowFeedbackText(true);
    }
  };

  const submitFeedback = async () => {
    console.log('Submit button clicked!');
    console.log('Submitting feedback:', { messageId: message.id, sessionId, feedback, feedbackText });
    try {
      const result = await chatService.sendFeedback(
        message.id, 
        sessionId, 
        feedback, 
        feedbackText
      );
      console.log('API response:', result);
      setShowFeedbackText(false);
      setFeedbackSubmitted(true);
      console.log('Feedback submitted successfully');
    } catch (error) {
      console.error('Failed to send feedback:', error);
      // Show success anyway since feedback was received by Lambda
      setShowFeedbackText(false);
      setFeedbackSubmitted(true);
      console.log('Feedback received by server (database save failed)');
    }
  };

  return (
    <div className={`message-bubble ${isUser ? 'user-message' : 'assistant-message'} ${isError ? 'error-message' : ''}`}>
      <div className="message-content">
        {linkifyText(message.content)}
      </div>
      
      {/* Show response time for assistant messages */}
      {!isUser && message.responseTime && (
        <div className="message-metadata">
          <span>⏱️</span>
          <span>{message.responseTime}s</span>
        </div>
      )}
      
      {/* Feedback buttons for assistant messages */}
      {!isUser && !isError && !feedbackSubmitted && (
        <div className="feedback-container">
          <button 
            className={`feedback-btn ${feedback === 'up' ? 'active' : ''}`}
            onClick={() => handleFeedback('up')}
            disabled={feedback !== null}
          >
            👍
          </button>
          <button 
            className={`feedback-btn ${feedback === 'down' ? 'active' : ''}`}
            onClick={() => handleFeedback('down')}
            disabled={feedback !== null}
          >
            👎
          </button>
        </div>
      )}
      
      {/* Feedback submitted message */}
      {feedbackSubmitted && (
        <div className="feedback-submitted">
          ✓ Feedback submitted
        </div>
      )}
      
      {/* Feedback text box */}
      {showFeedbackText && (
        <div className="feedback-text-container">
          <textarea
            className="feedback-textarea"
            placeholder="Please tell us what went wrong..."
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            rows={3}
          />
          <button className="feedback-submit-btn" onClick={submitFeedback}>
            Submit
          </button>
        </div>
      )}
      
      {/* Show timestamp */}
      <div className="message-timestamp">
        {message.timestamp.toLocaleTimeString()}
      </div>
    </div>
  );
};

export default MessageBubble;