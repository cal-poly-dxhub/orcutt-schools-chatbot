// src/components/Sidebar.js
import React from 'react';

const Sidebar = ({ 
  sources = [], 
  messageCount = 0, 
  averageResponseTime = 0, 
  sessionId,
  onClearChat,
  onSourceClick 
}) => {

  const handleFilenameClick = (source) => {
    if (source.presignedUrl) {
      window.open(source.presignedUrl, '_blank');
    }
  };

  const handleLinkClick = (source) => {
    if (source.url) {
      window.open(source.url, '_blank');
    }
  };

  return (
    <div className="sidebar">
      {/* Session Info */}
      <div className="sidebar-section">
        <h3>Current Session</h3>
        <div className="session-info">
          <div className="session-item">
            <span className="session-label">Session ID</span>
            <span className="session-value" title={sessionId}>
              {sessionId || 'Loading...'}
            </span>
          </div>
        </div>
        <button 
          onClick={onClearChat}
          className="new-session-button"
        >
          New Session
        </button>
      </div>

      {/* Sources */}
      {sources.length > 0 && (
        <div className="sidebar-section">
          <h3>Sources Used</h3>
          <div className="sources-list">
            {sources.map((source, index) => (
              <div key={index} className="source-item">
                <div className="source-content">
                  <span 
                    className="source-filename"
                    onClick={() => handleFilenameClick(source)}
                    style={{ cursor: 'pointer' }}
                  >
                    {source.filename}
                  </span>
                  {source.url && (
                    <span 
                      className="source-link-icon"
                      onClick={() => handleLinkClick(source)}
                      style={{ cursor: 'pointer' }}
                    >
                      🔗
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Help */}
      <div className="sidebar-section">
        <h3>Need Help?</h3>
        <p className="help-text">
          Contact Orcutt Schools directly if you need immediate assistance or can't find the information you're looking for.
        </p>
        <p className="help-text">
          Your conversation history is automatically saved for this session.
        </p>
      </div>
    </div>
  );
};

export default Sidebar;