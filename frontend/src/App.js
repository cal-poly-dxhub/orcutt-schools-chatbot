import React from 'react';
import ChatInterface from './components/ChatInterface';
import logo from './assets/logo.png';
import './App.css';

function App() {
  return (
    <div>
      <div style={{ 
        padding: '0.5rem',
        color: 'white',
        display: 'flex',
        justifyContent: 'center'
      }}>
        <div className="chat-header">
          <div className="header-content">
            <img src={logo} alt="Orcutt Union School District" className="header-logo" />
            <div className="header-text">
              <h1>Orcutt Schools Assistant</h1>
              <p style={{marginTop:-7}}>Get help with school information, schedules, and more</p>
            </div>
          </div>
        </div>
      </div>
      <ChatInterface />
    </div>
  );
}

export default App;