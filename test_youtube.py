#!/usr/bin/env python3
"""
Test script for YouTube video summarization
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from gemini_client import GeminiClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_youtube_summary():
    """Test YouTube video summarization"""
    
    # Load environment variables
    load_dotenv()
    
    print("🎥 Testing YouTube video summarization...")
    
    # Test video URL (a short, public video)
    test_url = "https://www.youtube.com/watch?v=9hE5-98ZeCg"
    
    try:
        # Initialize Gemini client
        print("📡 Initializing Gemini client...")
        client = GeminiClient()
        
        # Summarize the video
        print(f"\n🔍 Summarizing video: {test_url}")
        video_data = client.summarize_youtube_video(test_url)
        
        print(f"\n🎬 Video Title:")
        print("-" * 60)
        print(video_data['title'])
        print("-" * 60)
        
        print(f"\n🤖 Video Summary:")
        print("-" * 60)
        print(video_data['summary'])
        print("-" * 60)
        
        print("\n✅ YouTube summarization test completed successfully!")
        return True
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n💡 Make sure you have set the GEMINI_API_KEY environment variable")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_youtube_summary()
    sys.exit(0 if success else 1)
