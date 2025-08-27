#!/usr/bin/env python3
"""
Simple test script for Gemini API integration
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from src.clients.gemini import GeminiClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_gemini_basic():
    """Test basic Gemini functionality"""
    
    # Load environment variables
    load_dotenv()
    
    print("🤖 Testing Gemini API integration...")
    
    try:
        # Initialize Gemini client
        print("📡 Initializing Gemini client...")
        client = GeminiClient()
        
        # Test connection
        print("🔧 Testing connection...")
        if not client.test_connection():
            print("❌ Connection test failed!")
            return False
        
        print("✅ Connection test passed!")
        
        # Ask the test question
        print("\n🗣️ Asking: 'What color is the sky?'")
        response = client.ask_question("What color is the sky?")
        
        print(f"\n🤖 Gemini response:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
        print("\n✅ Basic Gemini test completed successfully!")
        return True
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\n💡 Make sure you have set the GEMINI_API_KEY environment variable")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_gemini_basic()
    sys.exit(0 if success else 1)
