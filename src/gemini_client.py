import os
import google.generativeai as genai
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class GeminiClient:
    """Simple client for Google Gemini API interactions"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Gemini API key. If None, will try to get from environment
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Configure the API
        genai.configure(api_key=self.api_key)
        
        # Initialize the model (using Gemini Flash Lite)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        logger.info("Gemini client initialized successfully")
    
    def ask_question(self, question: str) -> str:
        """
        Ask a simple question to Gemini
        
        Args:
            question: The question to ask
            
        Returns:
            The response from Gemini
        """
        try:
            logger.info(f"Asking Gemini: {question}")
            response = self.model.generate_content(question)
            
            if response.text:
                logger.info("Received response from Gemini")
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return "No response received"
                
        except Exception as e:
            logger.error(f"Error communicating with Gemini: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test if the Gemini API connection is working
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = self.ask_question("What color is the sky?")
            return len(response) > 0
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
