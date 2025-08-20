import React from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import Sidebar from './Sidebar';
import SchoolSelector from './SchoolSelector';
import PDFDownload from './PDFDownload';
import { useChat } from '../hooks/useChat';
import '../styles/Chat.css';
import logo from '../assets/logo.png';

const ChatInterface = () => {
  const {
    messages,
    isLoading,
    error,
    sources,
    sessionId,
    selectedSchool,
    setSelectedSchool,
    sendMessage,
    clearChat,
    getAverageResponseTime,
    messageCount
  } = useChat();

  const handleSourceClick = async (source) => {
    if (source.presignedUrl) {
      window.open(source.presignedUrl, '_blank');
    }
  };

  return (
    <div className="chat-container">
      {/* Main Chat Area with Sidebar */}
      <div className="chat-main">
        <div className="chat-content">
          <MessageList 
            messages={messages} 
            isLoading={isLoading}
            sessionId={sessionId}
          />
          
          {/* Error Display */}
          {error && (
            <div className="error-banner">
              <p>⚠️ {error}</p>
            </div>
          )}
          
          <ChatInput 
            onSendMessage={sendMessage}
            isLoading={isLoading}
          />
        </div>

        {/* Sidebar */}
        <div className="chat-sidebar">
          <SchoolSelector 
            selectedSchool={selectedSchool}
            onSchoolChange={setSelectedSchool}
          />
          <PDFDownload />
          <Sidebar 
            sources={sources || []}
            messageCount={messageCount}
            averageResponseTime={getAverageResponseTime()}
            sessionId={sessionId}
            onClearChat={clearChat}
            onSourceClick={handleSourceClick}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;