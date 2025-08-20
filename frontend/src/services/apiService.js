// src/services/apiService.js
import axios from 'axios';

// API Gateway URL
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timeout - please try again');
    }
    
    if (error.response) {
      const message = error.response.data?.error || error.response.data?.message || 'Server error occurred';
      throw new Error(message);
    } else if (error.request) {
      throw new Error('Network error - please check your connection');
    } else {
      throw new Error('An unexpected error occurred');
    }
  }
);

export const chatService = {
  /**
   * Send a chat message
   * @param {string} message - User message
   * @param {string} sessionId - Session identifier
   * @param {string} selectedSchool - Selected school (optional)
   * @returns {Promise} API response
   */
  sendMessage: async (message, sessionId, selectedSchool = null) => {
    try {
      const payload = {
        message: message.trim(),
        sessionId,
      };
      
      if (selectedSchool) {
        payload.selectedSchool = selectedSchool;
      }
      
      const response = await apiClient.post('/chat', payload);
      console.log("Session ID sent:", sessionId);
      console.log("Selected school:", selectedSchool);
      console.log("Chat response:", response.data);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get presigned URL for a source document
   * @param {string} sourceId - Source identifier
   * @param {string} s3Uri - S3 URI of the document
   * @returns {Promise} Presigned URL response
   */
  getSourceUrl: async (sourceId, s3Uri) => {
    try {
      const response = await apiClient.get(`/sources/${sourceId}`, {
        params: {
          s3Uri: s3Uri
        }
      });
      
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Send feedback for a message
   * @param {string} messageId - Message identifier
   * @param {string} sessionId - Session identifier
   * @param {string} feedbackType - 'up' or 'down'
   * @param {string} feedbackText - Optional feedback text
   * @returns {Promise} API response
   */
  sendFeedback: async (messageId, sessionId, feedbackType, feedbackText = '') => {
    try {
      const response = await apiClient.post('/feedback', {
        messageId: String(messageId),
        sessionId: String(sessionId),
        feedbackType,
        feedbackText
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },


};

export default chatService;
