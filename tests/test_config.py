#!/usr/bin/env python3
"""
Quick test to verify the configuration works with environment variables
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import Config

def test_config():
    print("Testing configuration...")
    config = Config()
    
    print(f"Subreddits from config: {config.subreddits}")
    print(f"Reddit username: {config.reddit_username}")
    print(f"Check interval: {config.check_interval}")
    
    # Test validation
    try:
        config.validate()
        print("✅ Configuration validation passed!")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")

if __name__ == "__main__":
    test_config()
