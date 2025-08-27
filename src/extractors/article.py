import logging
import time
from typing import Optional, Dict, Any
from core.config import Config
from extractors.providers import get_provider

logger = logging.getLogger(__name__)

class ArticleExtractor:
    def __init__(self, config: Config):
        self.config = config

    def extract_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract article content from URL using the appropriate provider."""
        provider = get_provider(self.config, url)
        return provider.extract_article(url)

    def extract_with_retry(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract article with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                result = self.extract_article(url)
                if result:
                    return result
                    
            except Exception as e:
                logger.warning(f"Extraction attempt {attempt + 1} failed for {url}: {e}")
                
            if attempt < self.config.max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"Failed to extract article after {self.config.max_retries} attempts: {url}")
        return None
