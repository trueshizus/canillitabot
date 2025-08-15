import requests
import logging
from newspaper import Article
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
import time
from config import Config

logger = logging.getLogger(__name__)

class ArticleExtractor:
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.extraction_user_agent
        })
    
    def extract_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract article content from URL"""
        try:
            # Try newspaper3k first (most reliable)
            article_data = self._extract_with_newspaper(url)
            
            if article_data and self._is_valid_article(article_data):
                return article_data
            
            # Fallback to BeautifulSoup
            logger.info(f"Newspaper extraction failed for {url}, trying BeautifulSoup")
            article_data = self._extract_with_beautifulsoup(url)
            
            if article_data and self._is_valid_article(article_data):
                return article_data
            
            logger.warning(f"Could not extract valid content from {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting article from {url}: {e}")
            return None
    
    def _extract_with_newspaper(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract article using newspaper3k"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            # Get additional metadata
            article.nlp()
            
            return {
                'title': article.title,
                'content': article.text,
                'summary': article.summary if hasattr(article, 'summary') else '',
                'authors': article.authors,
                'publish_date': article.publish_date,
                'url': url,
                'extraction_method': 'newspaper3k'
            }
            
        except Exception as e:
            logger.debug(f"Newspaper extraction failed for {url}: {e}")
            return None
    
    def _extract_with_beautifulsoup(self, url: str) -> Optional[Dict[str, Any]]:
        """Fallback extraction using BeautifulSoup"""
        try:
            response = self.session.get(
                url, 
                timeout=self.config.extraction_timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup)
            
            # Extract content
            content = self._extract_content(soup)
            
            if not title or not content:
                return None
            
            return {
                'title': title,
                'content': content,
                'summary': '',
                'authors': [],
                'publish_date': None,
                'url': url,
                'extraction_method': 'beautifulsoup'
            }
            
        except Exception as e:
            logger.debug(f"BeautifulSoup extraction failed for {url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title"""
        # Try various title selectors
        selectors = [
            'h1',
            '[property="og:title"]',
            'title',
            '.headline',
            '.article-title',
            '.post-title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get('content') if element.get('content') else element.get_text()
                if title and len(title.strip()) > 5:
                    return title.strip()
        
        return ""
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content"""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
            element.decompose()
        
        # Try various content selectors
        content_selectors = [
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content',
            'article p',
            '.story-body',
            '.article-body',
            '[property="articleBody"]'
        ]
        
        best_content = ""
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = " ".join([elem.get_text().strip() for elem in elements])
                if len(content) > len(best_content):
                    best_content = content
        
        # If no specific selectors work, try to find the largest text block
        if not best_content or len(best_content) < 100:
            paragraphs = soup.find_all('p')
            content_blocks = []
            
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 50:  # Only consider substantial paragraphs
                    content_blocks.append(text)
            
            if content_blocks:
                best_content = " ".join(content_blocks)
        
        # Clean up the content
        best_content = self._clean_content(best_content)
        
        return best_content
    
    def _clean_content(self, content: str) -> str:
        """Clean and format extracted content"""
        if not content:
            return ""
        
        # Remove extra whitespace
        content = ' '.join(content.split())
        
        # Remove common unwanted phrases
        unwanted_phrases = [
            "Click here to subscribe",
            "Sign up for our newsletter",
            "Follow us on",
            "Share this article",
            "Advertisement",
            "Read more:",
            "Related:",
        ]
        
        for phrase in unwanted_phrases:
            content = content.replace(phrase, "")
        
        # Limit length
        if len(content) > self.config.max_article_length:
            content = content[:self.config.max_article_length]
            # Try to end at a sentence
            last_period = content.rfind('.')
            if last_period > self.config.max_article_length * 0.8:
                content = content[:last_period + 1]
        
        return content.strip()
    
    def _is_valid_article(self, article_data: Dict[str, Any]) -> bool:
        """Validate extracted article data"""
        if not article_data:
            return False
        
        content = article_data.get('content', '')
        title = article_data.get('title', '')
        
        # Check minimum content length
        if len(content) < self.config.min_article_length:
            logger.debug(f"Article too short: {len(content)} characters")
            return False
        
        # Check if we have a title
        if not title or len(title) < 10:
            logger.debug("Article missing valid title")
            return False
        
        # Check content quality (basic heuristics)
        if self._is_low_quality_content(content):
            return False
        
        return True
    
    def _is_low_quality_content(self, content: str) -> bool:
        """Check if content appears to be low quality"""
        # Too many short sentences might indicate poor extraction
        sentences = content.split('.')
        short_sentences = [s for s in sentences if len(s.strip()) < 20]
        
        if len(short_sentences) > len(sentences) * 0.7:
            return True
        
        # Check for repetitive content
        words = content.lower().split()
        if len(set(words)) < len(words) * 0.3:  # Less than 30% unique words
            return True
        
        return False
    
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