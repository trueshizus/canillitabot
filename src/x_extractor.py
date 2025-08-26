"""
X/Twitter content extractor for CanillitaBot.

Handles extraction of tweet content from X/Twitter URLs using the oEmbed API
and HTML parsing to generate Reddit-friendly comments.
"""

import requests
import logging
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)

class XContentExtractor:
    """Extracts content from X/Twitter posts using oEmbed API."""
    
    def __init__(self):
        self.oembed_url = "https://publish.twitter.com/oembed"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CanillitaBot/1.0 (Reddit News Bot)'
        })
    
    def is_x_url(self, url: str) -> bool:
        """Check if URL is from X/Twitter."""
        if not url:
            return False
        
        parsed = urlparse(url.lower())
        return parsed.netloc in ['twitter.com', 'x.com', 'www.twitter.com', 'www.x.com']
    
    def extract_tweet_id(self, url: str) -> Optional[str]:
        """Extract tweet ID from X/Twitter URL."""
        # Match pattern: /status/1234567890
        match = re.search(r'/status/(\d+)', url)
        return match.group(1) if match else None
    
    def get_oembed_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Get oEmbed data from X/Twitter."""
        try:
            params = {'url': url}
            response = self.session.get(self.oembed_url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"oEmbed API returned status {response.status_code} for {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching oEmbed data for {url}: {e}")
            return None
    
    def parse_tweet_html(self, html_content: str) -> Dict[str, str]:
        """Parse tweet HTML from oEmbed to extract clean content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        result = {
            'text': '',
            'author': '',
            'handle': '',
            'date': '',
            'has_media': False
        }
        
        try:
            # Extract tweet text from <p> tag
            tweet_p = soup.find('p')
            if tweet_p:
                # Check for media links before removing them
                media_links = tweet_p.find_all('a', href=re.compile(r'(pic\.twitter\.com|t\.co)'))
                result['has_media'] = len(media_links) > 0
                
                # Remove media links from text
                for link in media_links:
                    link.decompose()
                
                # Get clean text and handle line breaks
                text = tweet_p.get_text()
                # Replace multiple spaces with single space and clean up
                result['text'] = re.sub(r'\s+', ' ', text).strip()
            
            # Extract author info from citation (— Author (@handle))
            full_text = soup.get_text()
            if '—' in full_text:
                citation_part = full_text.split('—')[1]
                
                # Extract author name and handle
                # Format: "Maximiliano Firtman (@maxifirtman) August 25, 2025"
                author_match = re.search(r'([^(]+)\s*\((@\w+)\)', citation_part)
                if author_match:
                    result['author'] = author_match.group(1).strip()
                    result['handle'] = author_match.group(2)
            
            # Extract date from the link text
            date_link = soup.find('a', href=re.compile(r'status/\d+'))
            if date_link:
                result['date'] = date_link.get_text().strip()
                
        except Exception as e:
            logger.error(f"Error parsing tweet HTML: {e}")
        
        return result
    
    def extract_tweet_content(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract tweet content from X/Twitter URL.
        
        Returns:
            Dict with tweet data or None if extraction fails
        """
        if not self.is_x_url(url):
            logger.debug(f"URL is not from X/Twitter: {url}")
            return None
        
        tweet_id = self.extract_tweet_id(url)
        if not tweet_id:
            logger.warning(f"Could not extract tweet ID from URL: {url}")
            return None
        
        logger.info(f"Extracting content from X/Twitter post: {tweet_id}")
        
        # Get oEmbed data
        oembed_data = self.get_oembed_data(url)
        if not oembed_data:
            return None
        
        # Parse HTML content
        html_content = oembed_data.get('html', '')
        if not html_content:
            logger.warning(f"No HTML content in oEmbed response for {url}")
            return None
        
        parsed_content = self.parse_tweet_html(html_content)
        
        # Combine oEmbed and parsed data
        result = {
            'tweet_id': tweet_id,
            'url': url,
            'text': parsed_content['text'],
            'author': parsed_content['author'],
            'handle': parsed_content['handle'],
            'date': parsed_content['date'],
            'has_media': parsed_content['has_media'],
            'provider': 'X/Twitter',
            'extraction_method': 'oembed_html_parsing'
        }
        
        # Validate that we got essential content
        if not result['text'] or not result['author']:
            logger.warning(f"Incomplete tweet data extracted from {url}")
            return None
        
        logger.info(f"Successfully extracted tweet content: {len(result['text'])} chars")
        return result

# Convenience function for testing
def extract_tweet(url: str) -> Optional[Dict[str, Any]]:
    """Extract tweet content from URL. Convenience function for testing."""
    extractor = XContentExtractor()
    return extractor.extract_tweet_content(url)

if __name__ == "__main__":
    # Test with the sample tweet
    test_url = "https://x.com/maxifirtman/status/1959988414377267240"
    
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Testing X/Twitter Content Extractor")
    print("=" * 50)
    
    result = extract_tweet(test_url)
    
    if result:
        print("✅ Extraction successful!")
        print(f"Tweet ID: {result['tweet_id']}")
        print(f"Author: {result['author']} ({result['handle']})")
        print(f"Date: {result['date']}")
        print(f"Text: {result['text']}")
        print(f"Has media: {result['has_media']}")
    else:
        print("❌ Extraction failed!")
