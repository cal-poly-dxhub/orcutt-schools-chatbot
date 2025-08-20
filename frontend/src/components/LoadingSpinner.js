import React from 'react';

const LoadingSpinner = () => (
  <div className="loading-message">
    <div className="message-bubble loading">
      <div className="spinner"></div>
      Typing...
    </div>
  </div>
);

export default LoadingSpinner;