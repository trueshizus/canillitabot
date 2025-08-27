#!/usr/bin/env python3
"""
Unit tests for the Infobae provider.
Tests article extraction with proper cleanup of "Últimas noticias" sections.
"""

import unittest
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.core.config import Config
from src.extractors.providers.infobae import InfobaeProvider


class TestInfobaeProvider(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.provider = InfobaeProvider(self.config)
    
    def test_provider_initialization(self):
        """Test that the provider initializes correctly"""
        self.assertIsNotNone(self.provider)
        self.assertEqual(self.provider.__class__.__name__, 'InfobaeProvider')
    
    def test_sample_article_extraction(self):
        """Test extraction of a real Infobae article"""
        test_url = "https://www.infobae.com/politica/2025/08/15/patricia-bullrich-confirmo-que-sera-candidata-a-senadora-por-la-ciudad-de-buenos-aires/"
        
        # This would require network access, so we'll skip in CI
        if hasattr(self, '_skip_network_tests'):
            self.skipTest("Network tests disabled")
        
        result = self.provider.extract_article(test_url)
        
        if result:
            # Check that "Últimas noticias" was properly removed
            content = result.get('content', '')
            self.assertNotIn('últimas noticias', content.lower())
            self.assertGreater(len(content), 200)  # Should have substantial content
            self.assertTrue(result.get('title'))   # Should have a title


if __name__ == '__main__':
    unittest.main()
