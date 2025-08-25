import os
import re
import requests
from google import genai
from google.genai import types
from typing import Optional
import logging
# New imports for transcript fetching and handling errors
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

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
        
        self.client = genai.Client(api_key=self.api_key)
        logger.info("Gemini client initialized successfully")
    
    def _get_youtube_title(self, youtube_url: str) -> str:
        """
        Extract YouTube video title from the page HTML
        
        Args:
            youtube_url: The YouTube video URL
            
        Returns:
            The video title
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(youtube_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            title_match = re.search(r'<title>(.+?)</title>', response.text)
            if title_match:
                title = re.sub(r'\s*-\s*YouTube\s*$', '', title_match.group(1))
                return title.strip()
            return "Video de YouTube"
        except Exception as e:
            logger.warning(f"Failed to extract YouTube title: {e}")
            return "Video de YouTube"

    def _get_youtube_transcript(self, youtube_url: str) -> Optional[str]:
        """
        [OPTIMIZATION] Fetches the transcript for a YouTube video.

        Args:
            youtube_url: The YouTube video URL.

        Returns:
            The full transcript as a single string, or None if not available.
        """
        try:
            # Extract video ID from any YouTube URL format
            video_id_match = re.search(r'(?:v=|\/|embed\/|youtu.be\/)([a-zA-Z0-9_-]{11})', youtube_url)
            if not video_id_match:
                logger.warning(f"Could not extract video ID from URL: {youtube_url}")
                return None

            video_id = video_id_match.group(1)
            logger.info(f"Fetching transcript for video ID: {video_id}")
            
            # Use the new API structure
            ytt_api = YouTubeTranscriptApi()
            fetched_transcript = ytt_api.fetch(video_id, languages=['es', 'en'])
            
            # Convert to text
            return " ".join([snippet.text for snippet in fetched_transcript])

        except (TranscriptsDisabled, NoTranscriptFound):
            logger.warning(f"No transcript found or transcripts are disabled for video: {youtube_url}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching YouTube transcript: {e}")
            return None

    def ask_question(self, question: str) -> str:
        """
        Ask a simple question to Gemini. Already uses a cost-effective model.
        """
        try:
            logger.info(f"Asking Gemini: {question}")
            # This model is great for cost-effective text tasks
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=question
            )
            return response.text.strip() if response.text else "No response received"
        except Exception as e:
            logger.error(f"Error communicating with Gemini: {e}")
            raise
    
    def summarize_youtube_video(self, youtube_url: str) -> dict:
        """
        [REFACTORED] Generate a summary using a cost-optimized, transcript-first approach.
        """
        logger.info(f"Summarizing YouTube video (cost-optimized): {youtube_url}")
        
        # Step 1: Get title cheaply (current implementation is already good)
        video_title = self._get_youtube_title(youtube_url)
        
        # Step 2: Attempt to summarize using the transcript (very cheap)
        transcript = self._get_youtube_transcript(youtube_url)
        if transcript:
            logger.info("Transcript found. Summarizing using cheap text model.")
            try:
                prompt = f"""
                Resumí el siguiente texto, que es la transcripción de un video, en exactamente 3 oraciones concisas que capturen los puntos principales e información clave. No incluyas introduciones como "este video trata sobre" o comentarios adicionales. Escribí solo el resumen directo.

                Transcripción:
                {transcript}
                """
                summary = self.ask_question(prompt) # Reuse the cheap text model method
                if summary != "No response received":
                    return {'title': video_title, 'summary': summary}
            except Exception as e:
                logger.error(f"Failed to summarize transcript, falling back to video model. Error: {e}")

        # Step 3: Fallback to the more expensive video model if no transcript is found
        logger.warning("No transcript available or text summary failed. Falling back to expensive video model.")
        try:
            summary_response = self.client.models.generate_content(
                model='models/gemini-2.5-flash',
                contents=[
                    types.Part(file_data=types.FileData(file_uri=youtube_url)),
                    types.Part(text='Resumí este video en exactamente 3 oraciones concisas que capturen los puntos principales e información clave. No incluyas introduciones como "este video trata sobre" o comentarios adicionales. Escribí solo el resumen directo.')
                ]
            )
            
            summary_text = summary_response.text.strip() if summary_response.text else "No se pudo generar un resumen del video en este momento."
            return {'title': video_title, 'summary': summary_text}
                
        except Exception as e:
            logger.error(f"Error summarizing YouTube video with video model: {e}")
            return {'title': video_title, 'summary': "No se pudo procesar el video en este momento."}
    
    def test_connection(self) -> bool:
        """Test if the Gemini API connection is working"""
        try:
            response = self.ask_question("What color is the sky?")
            return len(response) > 0 and "No response" not in response
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
