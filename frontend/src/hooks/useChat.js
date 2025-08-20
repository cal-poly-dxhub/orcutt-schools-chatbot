// src/hooks/useChat.js - Clean version with no duplicates
import { useState, useCallback } from 'react';
import { chatService } from '../services/apiService';

export const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sources, setSources] = useState([]);
  const [selectedSchool, setSelectedSchool] = useState(null);
  
  // Helper function to generate session ID
  const generateSessionId = () => {
    return Date.now().toString();
  };

  // Initialize session ID immediately - NEW SESSION ON EVERY REFRESH
  const [sessionId, setSessionId] = useState(() => {
    // Always generate a new session ID (don't check localStorage)
    const newSessionId = generateSessionId();
    console.log('New session created:', newSessionId);
    return newSessionId;
  });

  // Add message to chat
  const addMessage = useCallback((role, content, metadata = {}) => {
    const newMessage = {
      id: Date.now() + Math.random(),
      role,
      content,
      timestamp: new Date(),
      ...metadata
    };
    
    setMessages(prev => [...prev, newMessage]);
    return newMessage;
  }, []);

  // Send message to API
  const sendMessage = useCallback(async (message) => {
    if (!message.trim() || isLoading || !sessionId) return;

    // Clear any previous errors
    setError(null);
    
    // Add user message
    addMessage('user', message);
    
    // Set loading state
    setIsLoading(true);

    try {
      // Call API with session ID and selected school
      const response = await chatService.sendMessage(message, sessionId, selectedSchool);
      console.log(response.prompt);
      if (response.success) {
        // Add assistant response with messageId from Lambda
        const assistantMessage = addMessage('assistant', response.response, {
          responseTime: response.responseTime,
          queryType: response.queryType,
          sources: response.sources || []
        });
        
        // Update the message with the correct messageId from Lambda
        if (response.messageId) {
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessage.id 
              ? { ...msg, id: response.messageId }
              : msg
          ));
        }
        
        // Update sources for sidebar
        setSources(response.sources || []);
      } else {
        throw new Error(response.error || 'Failed to get response');
      }
      
    } catch (err) {
      setError(err.message);
      
      // Add error message to chat
      addMessage('assistant', 
        'I apologize, but I encountered an error. Please try again or contact the school directly for assistance.',
        { isError: true }
      );
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, addMessage, sessionId, selectedSchool]);

  // Clear chat and start new session
  const clearChat = useCallback(() => {
    setMessages([]);
    setSources([]);
    setError(null);
    
    // Generate new session ID
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    
    console.log('New session started:', newSessionId);
  }, []);

  // Get response times for metrics
  const getAverageResponseTime = useCallback(() => {
    const responseTimes = messages
      .filter(msg => msg.role === 'assistant' && msg.responseTime)
      .map(msg => msg.responseTime);
    
    if (responseTimes.length === 0) return 0;
    
    return responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length;
  }, [messages]);

  return {
    messages,
    isLoading,
    error,
    sources,
    sessionId,
    selectedSchool,
    setSelectedSchool,
    sendMessage,
    clearChat,
    addMessage,
    getAverageResponseTime,
    messageCount: messages.length
  };
};