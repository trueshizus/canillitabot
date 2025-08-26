#!/usr/bin/env python3
"""
Test X/Twitter integration with the bot
"""

import sys
import os
# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import Config
from x_extractor import XContentExtractor

def test_x_twitter_config():
    """Test X/Twitter configuration loading"""
    print("Testing X/Twitter configuration...")
    
    config = Config("config/settings.yaml")
    
    print(f"X/Twitter enabled: {config.x_twitter_enabled}")
    print(f"X/Twitter template: {config.x_twitter_comment_template[:100]}...")
    
    return config.x_twitter_enabled

def test_x_twitter_extractor():
    """Test X/Twitter content extraction"""
    print("\nTesting X/Twitter content extraction...")
    
    extractor = XContentExtractor()
    
    # Test URL
    test_url = "https://x.com/maxifirtman/status/1959988414377267240"
    
    print(f"Extracting content from: {test_url}")
    
    result = extractor.extract_tweet_content(test_url)
    
    if result:
        print(f"✓ Author: {result['author']}")
        print(f"✓ Date: {result['date']}")
        print(f"✓ Text: {result['text'][:100]}...")
        print(f"✓ Media count: {result.get('media_count', 0)}")
        return True
    else:
        print("✗ Failed to extract content")
        return False

def test_comment_formatting():
    """Test comment formatting with X/Twitter template"""
    print("\nTesting comment formatting...")
    
    config = Config("config/settings.yaml")
    
    # Sample tweet data
    tweet_data = {
        'author': 'Test User (@testuser)',
        'date': 'January 20, 2025',
        'text': 'This is a test tweet content for formatting.',
        'media_count': 1
    }
    
    # Format media note
    media_note = ""
    if tweet_data.get('media_count', 0) > 0:
        media_note = f"📎 *Contiene {tweet_data['media_count']} archivo(s) multimedia*"
    
    # Format comment
    formatted_comment = config.x_twitter_comment_template.format(
        author=tweet_data['author'],
        date=tweet_data['date'],
        text=tweet_data['text'],
        media_note=media_note,
        url="https://x.com/testuser/status/123456789"
    )
    
    print("Formatted comment:")
    print("=" * 50)
    print(formatted_comment)
    print("=" * 50)
    
    return True

def main():
    """Run all X/Twitter integration tests"""
    print("Running X/Twitter integration tests...\n")
    
    tests = [
        ("Configuration", test_x_twitter_config),
        ("Content Extraction", test_x_twitter_extractor),
        ("Comment Formatting", test_comment_formatting)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success, error in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name:20} : {status}")
        if error:
            print(f"                     Error: {error}")
        if success:
            passed += 1
    
    print(f"\nTests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All X/Twitter integration tests passed!")
        return True
    else:
        print("✗ Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
