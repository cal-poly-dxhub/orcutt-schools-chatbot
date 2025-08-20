# React Chat Application

A modern, responsive chat application built with React featuring real-time messaging and API integration.

## Features

- **Chat Interface**: Clean message bubbles with user/bot distinction
- **Real-time Input**: Send button and Enter key support
- **Message History**: Persistent chat history display
- **Loading States**: Spinner animation while waiting for responses
- **Session Management**: UUID-based session tracking
- **Error Handling**: User-friendly error messages
- **Responsive Design**: Mobile-friendly interface

## API Integration

The app integrates with an API Gateway endpoint expecting:

**Request Format:**
```json
{
  "message": "user text",
  "session_id": "uuid"
}
```

**Response Format:**
```json
{
  "response": "bot text",
  "response_time": 1.23
}
```

## Setup

1. Install dependencies:
```bash
npm install
```

2. Update API endpoint in `src/App.js`:
```javascript
const response = await fetch('YOUR_API_GATEWAY_ENDPOINT', {
```

3. Start the development server:
```bash
npm start
```

## Usage

- Type messages in the input field
- Press Enter or click Send to submit
- View chat history with timestamps
- Session ID is automatically generated and displayed
- Error messages appear for failed requests

## Components

- **App.js**: Main chat component with state management
- **App.css**: Responsive styling with modern design
- **index.js**: React application entry point