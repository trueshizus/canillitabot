#!/usr/bin/env python3
"""
Test script for the new provider-based article extraction system.
Specifically tests Infobae extraction with "Últimas noticias" removal.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from article_extractor import ArticleExtractor

def test_infobae_extraction():
    """Test Infobae article extraction with provider-specific configuration"""
    
    # The real Infobae article we analyzed
    test_url = "https://www.infobae.com/politica/2025/08/15/patricia-bullrich-confirmo-que-sera-candidata-a-senadora-por-la-ciudad-de-buenos-aires/"
    
    print("🧪 Testing Provider-Based Article Extraction")
    print("=" * 60)
    print(f"URL: {test_url}")
    print()
    
    try:
        # Initialize config and extractor
        config = Config()
        extractor = ArticleExtractor(config)
        
        # Test provider config loading
        provider_config = config.get_provider_config(test_url)
        print(f"✓ Loaded provider: {provider_config.get('name', 'Unknown')}")
        print(f"✓ Domain: {config._extract_domain(test_url)}")
        print()
        
        # Extract the article
        print("🔍 Extracting article...")
        article_data = extractor.extract_article(test_url)
        
        if article_data:
            print("✅ EXTRACTION SUCCESSFUL")
            print("-" * 40)
            print(f"Title: {article_data['title']}")
            print(f"Method: {article_data.get('extraction_method', 'unknown')}")
            print(f"Provider: {article_data.get('provider', 'unknown')}")
            print(f"Content Length: {len(article_data['content'])} characters")
            print()
            
            # Check if "Últimas noticias" was removed
            content = article_data['content']
            ultimas_noticias_found = 'últimas noticias' in content.lower()
            
            if ultimas_noticias_found:
                print("❌ FAILED: 'Últimas noticias' section still present in content")
                # Show where it appears
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'últimas noticias' in line.lower():
                        print(f"   Found at line {i+1}: {line.strip()[:100]}...")
            else:
                print("✅ SUCCESS: 'Últimas noticias' section successfully removed")
            
            print()
            print("📄 CONTENT PREVIEW:")
            print("-" * 40)
            # Show first 500 characters
            preview = content[:500]
            print(preview)
            if len(content) > 500:
                print("...")
                print(f"[{len(content) - 500} more characters]")
            
            print()
            print("🔍 CONTENT ANALYSIS:")
            print("-" * 40)
            
            # Check for other unwanted patterns
            unwanted_patterns = [
                ("Te puede interesar", "te puede interesar"),
                ("Seguí leyendo", "seguí leyendo"), 
                ("Compartir en", "compartir en"),
                ("Suscribite", "suscrib"),
                ("Tags:", "tags:")
            ]
            
            for pattern_name, pattern in unwanted_patterns:
                if pattern in content.lower():
                    print(f"⚠ Warning: '{pattern_name}' pattern found in content")
                else:
                    print(f"✓ '{pattern_name}' pattern successfully removed")
            
            return True
            
        else:
            print("❌ EXTRACTION FAILED")
            print("No article data returned")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_infobae_extraction()
    sys.exit(0 if success else 1)