#!/usr/bin/env python3
"""
Test script to preview article extraction and comment formatting
Usage: python test_extraction.py "https://example.com/news-article"
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from config import Config
from article_extractor import ArticleExtractor
from reddit_client import RedditClient

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
        
        # Create a dummy Reddit client for formatting only
        class TestRedditClient:
            def __init__(self, config):
                self.config = config
            
            def format_comment(self, article_content, article_url, article_title=""):
                """Use the actual formatting logic from RedditClient"""
                from reddit_client import RedditClient
                client = RedditClient.__new__(RedditClient)
                client.config = config
                return client.format_comment(article_content, article_url, article_title)
        
        reddit_client = TestRedditClient(config)
        
        # Extract article
        article_data = extractor.extract_with_retry(url)
        
        if not article_data:
            print("Failed to extract article")
            return False
        
        # Format comments
        formatted_comments = reddit_client.format_comment(
            article_content=article_data.get('content', ''),
            article_url=url,
            article_title=article_data.get('title', '')
        )
        
        # Show comment preview
        print_comment_preview(formatted_comments, show_full)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_extraction.py \"<news_url>\" [--full]")
        sys.exit(1)
    
    url = sys.argv[1]
    show_full = "--full" in sys.argv
    
    success = test_extraction(url, show_full)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()