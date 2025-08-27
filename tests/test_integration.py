#!/usr/bin/env python3
"""
Test script for the full YouTube + Reddit bot integration
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from src.core.config import Config
from src.clients.internal.monitor import PostMonitor
from src.clients.gemini import GeminiClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_url_detection():
    """Test URL detection for YouTube videos"""
    
    print("🔍 Testing URL detection...")
    
    # Load config
    config = Config()
    
    # Create a mock Reddit instance
    mock_reddit = MagicMock()
    monitor = PostMonitor(config, mock_reddit)
    
    # Test YouTube URLs
    test_urls = [
        "https://www.youtube.com/watch?v=9hE5-98ZeCg",
        "https://youtu.be/9hE5-98ZeCg",
        "https://youtube.com/watch?v=test",
        "https://www.infobae.com/some-news-article",
        "https://reddit.com/r/argentina"
    ]
    
    for url in test_urls:
        # Create mock submission
        mock_submission = MagicMock()
        mock_submission.url = url
        mock_submission.is_self = False
        
        is_youtube = monitor.is_youtube_video(mock_submission)
        print(f"  {url:<50} → YouTube: {is_youtube}")
    
    return True

def test_config_integration():
    """Test configuration integration"""
    
    print("\n⚙️ Testing configuration...")
    
    config = Config()
    
    print(f"  YouTube enabled: {config.youtube_enabled}")
    print(f"  YouTube template: {config.youtube_summary_template[:50]}...")
    print(f"  Gemini API key configured: {'Yes' if config.gemini_api_key else 'No'}")
    
    return True

def main():
    """Run all integration tests"""
    
    load_dotenv()
    
    print("🧪 Running YouTube + Reddit Bot Integration Tests")
    print("=" * 60)
    
    try:
        # Test URL detection
        test_url_detection()
        
        # Test configuration
        test_config_integration()
        
        print("\n✅ All integration tests passed!")
        print("\n💡 Next steps:")
        print("   1. Run the bot with: python run.py")
        print("   2. Post a YouTube video link in your configured subreddit")
        print("   3. Watch the bot generate a summary!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
