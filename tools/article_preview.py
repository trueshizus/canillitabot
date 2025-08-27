#!/usr/bin/env python3
"""
Article Extraction Test Tool for CanillitaBot

Test script to preview article extraction and comment formatting.
Usage: python article_preview.py "https://example.com/news-article"
"""

import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from core.config import Config
from extractors.article import ArticleExtractor
# Note: RedditClient is imported within the TestRedditClient class to avoid circular dependencies
# during initialization, but we could import it here if we restructured the test client.

def print_separator(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def print_comment_preview(comments, show_full=False):
    """Print formatted comments as they would appear on Reddit"""
    for i, comment in enumerate(comments):
        if len(comments) > 1:
            if i == 0:
                print("=== MAIN COMMENT ===")
            else:
                print(f"\n=== CONTINUATION {i} ===")
        
        print(comment)
        
        if not show_full and len(comment) > 2000:
            print(f"\n[Comment truncated - {len(comment)} total characters]")
            break

def test_extraction(url, show_full=False):
    """Test article extraction and comment formatting"""
    try:
        # Initialize components
        config = Config()
        extractor = ArticleExtractor(config)
        
        # Create a minimal Reddit client for formatting only
        class TestRedditClient:
            def __init__(self, config):
                self.config = config
            
            def format_comment(self, article_content, article_url, article_title=""):
                """Use the actual formatting logic from the refactored RedditClient"""
                # Import the refactored components
                from clients.reddit import RedditClient
                
                # Mock the PRAW Reddit instance to avoid authentication
                with patch('praw.Reddit') as mock_praw:
                    mock_reddit_instance = Mock()
                    mock_reddit_instance.user.me.return_value = Mock(name='testbot', is_suspended=False, created_utc=1234567890)
                    mock_praw.return_value = mock_reddit_instance
                    
                    # Mock environment variables
                    env_vars = {
                        'REDDIT_CLIENT_ID': 'test_id',
                        'REDDIT_CLIENT_SECRET': 'test_secret',
                        'REDDIT_USERNAME': 'testbot',
                        'REDDIT_PASSWORD': 'test_pass'
                    }
                    
                    with patch.dict(os.environ, env_vars):
                        # Create the Reddit client and use its comment formatting
                        client = RedditClient(self.config)
                        return client.format_comment(article_content, article_url, article_title)
        
        reddit_client = TestRedditClient(config)
        
        print_separator("EXTRACTING ARTICLE")
        print(f"URL: {url}")
        
        # Extract article
        article_data = extractor.extract_with_retry(url)
        
        if not article_data:
            print("❌ Failed to extract article")
            return False
        
        print(f"✅ Extraction successful!")
        print(f"Title: {article_data.get('title', 'N/A')}")
        print(f"Provider: {article_data.get('provider', 'Unknown')}")
        print(f"Method: {article_data.get('extraction_method', 'Unknown')}")
        print(f"Content length: {len(article_data.get('content', ''))} characters")
        
        # Format comments
        formatted_comments = reddit_client.format_comment(
            article_content=article_data.get('content', ''),
            article_url=url,
            article_title=article_data.get('title', '')
        )
        
        print_separator("REDDIT COMMENT PREVIEW")
        
        # Show comment preview
        print_comment_preview(formatted_comments, show_full)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python article_preview.py \"<news_url>\" [--full]")
        print("\nExample:")
        print("  python article_preview.py \"https://www.infobae.com/some-article\"")
        print("  python article_preview.py \"https://www.clarin.com/some-article\" --full")
        sys.exit(1)
    
    url = sys.argv[1]
    show_full = "--full" in sys.argv
    
    success = test_extraction(url, show_full)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
