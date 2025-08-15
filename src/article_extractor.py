import requests
import logging
from newspaper import Article
from bs4 import BeautifulSoup, NavigableString, Tag
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, urljoin
import time
import re
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
        """Extract article content from URL with provider-specific formatting"""
        try:
            # Get provider-specific configuration for this URL
            provider_config = self.config.get_provider_config(url)
            domain = self.config._extract_domain(url)
            
            logger.info(f"Using provider '{provider_config.get('name', 'unknown')}' for domain '{domain}'")
            
            # Try extraction methods in configured priority order
            extraction_methods = provider_config.get('method_priority', ['structured_beautifulsoup', 'enhanced_newspaper3k'])
            
            for method in extraction_methods:
                try:
                    if method == 'structured_beautifulsoup':
                        article_data = self._extract_structured_content(url, provider_config)
                    elif method == 'enhanced_newspaper3k':
                        article_data = self._extract_with_newspaper_enhanced(url, provider_config)
                    else:
                        logger.warning(f"Unknown extraction method: {method}")
                        continue
                    
                    if article_data and self._is_valid_article(article_data, provider_config):
                        article_data['extraction_method'] = method
                        article_data['provider'] = provider_config.get('name', 'unknown')
                        return article_data
                        
                except Exception as e:
                    logger.warning(f"Extraction method '{method}' failed for {url}: {e}")
                    continue
            
            logger.warning(f"All extraction methods failed for {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting article from {url}: {e}")
            return None
    
    def _extract_structured_content(self, url: str, provider_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract article with preserved structure using BeautifulSoup and provider config"""
        try:
            response = self.session.get(
                url, 
                timeout=self.config.extraction_timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements first using provider config
            self._remove_unwanted_elements_provider(soup, provider_config)
            
            # Extract title using provider config
            title = self._extract_title_provider(soup, provider_config)
            
            # Extract structured content using provider config
            structured_content = self._extract_content_provider(soup, provider_config)
            
            if not title or not structured_content:
                return None
            
            # Apply provider-specific text cleanup
            cleaned_content = self._apply_provider_cleanup(structured_content, provider_config)
            
            return {
                'title': title,
                'content': cleaned_content,
                'summary': '',
                'authors': self._extract_authors_provider(soup, provider_config),
                'publish_date': self._extract_publish_date_provider(soup, provider_config),
                'url': url,
                'extraction_method': 'provider_structured'
            }
            
        except Exception as e:
            logger.debug(f"Provider structured extraction failed for {url}: {e}")
            return None
    
    def _extract_with_newspaper_enhanced(self, url: str, provider_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract article using newspaper3k with provider-specific enhancements"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            # Get the raw HTML and enhance the text formatting
            response = self.session.get(url, timeout=self.config.extraction_timeout)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Use provider-specific cleanup instead of generic
            self._remove_unwanted_elements_provider(soup, provider_config)
            
            # Try to enhance newspaper3k output with structure
            enhanced_content = self._enhance_newspaper_content(article.text, soup)
            
            # Apply provider-specific text cleanup
            cleaned_content = self._apply_provider_cleanup(enhanced_content, provider_config)
            
            # Clean title using provider config
            cleaned_title = self._clean_title_provider(article.title, provider_config) if article.title else ""
            
            return {
                'title': cleaned_title,
                'content': cleaned_content,
                'summary': article.summary if hasattr(article, 'summary') else '',
                'authors': article.authors,
                'publish_date': article.publish_date,
                'url': url,
                'extraction_method': 'enhanced_newspaper3k_provider'
            }
            
        except Exception as e:
            logger.debug(f"Enhanced newspaper extraction failed for {url}: {e}")
            return None
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove unwanted elements from soup"""
        unwanted_tags = [
            'script', 'style', 'nav', 'header', 'footer', 'aside', 
            'advertisement', 'ads', 'social-share', 'comments',
            'related-articles', 'sidebar', 'menu'
        ]
        
        unwanted_classes = [
            'ad', 'ads', 'advertisement', 'social', 'share', 'comments',
            'related', 'sidebar', 'menu', 'navigation', 'footer',
            'header', 'promo', 'newsletter', 'subscription'
        ]
        
        # Remove by tag name
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove by class name
        for class_name in unwanted_classes:
            for element in soup.find_all(class_=re.compile(class_name, re.I)):
                element.decompose()
        
        # Remove elements with specific text patterns
        unwanted_text_patterns = [
            r'suscr[ií]bete',
            r'newsletter',
            r'compartir',
            r'seguir.*redes',
            r'publicidad',
            r'anuncio',
        ]
        
        for pattern in unwanted_text_patterns:
            for element in soup.find_all(text=re.compile(pattern, re.I)):
                if element.parent:
                    element.parent.decompose()
    
    def _extract_structured_content_from_soup(self, soup: BeautifulSoup) -> str:
        """Extract content with preserved structure"""
        # Try different article content selectors for Argentine news sites
        content_selectors = [
            # Generic article selectors
            'article',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content',
            '.story-body',
            '.article-body',
            '[property="articleBody"]',
            
            # Argentine news site specific selectors
            '.nota-contenido',          # Clarín
            '.article-text',            # La Nación
            '.contenido',               # Página/12
            '.article-body-text',       # Infobae
            '.nota-texto',              # Ámbito
            '.cuerpo-nota',             # TN
            '.entry-content-text',      # General
        ]
        
        article_container = None
        for selector in content_selectors:
            container = soup.select_one(selector)
            if container:
                article_container = container
                break
        
        if not article_container:
            # Fallback: find the largest text container
            article_container = self._find_largest_text_container(soup)
        
        if not article_container:
            return ""
        
        # Extract structured content from the container
        return self._process_article_structure(article_container)
    
    def _find_largest_text_container(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the container with the most text content"""
        candidates = soup.find_all(['div', 'section', 'article'])
        
        best_container = None
        max_text_length = 0
        
        for container in candidates:
            text_length = len(container.get_text().strip())
            if text_length > max_text_length:
                max_text_length = text_length
                best_container = container
        
        return best_container if max_text_length > 500 else None
    
    def _process_article_structure(self, container: Tag) -> str:
        """Process article structure preserving formatting"""
        structured_parts = []
        
        for element in container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'blockquote']):
            if not self._is_meaningful_element(element):
                continue
                
            text = element.get_text().strip()
            if not text:
                continue
            
            # Process based on element type
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Headers
                level = int(element.name[1])
                if level == 1:
                    structured_parts.append(f"# {text}\n")
                elif level == 2:
                    structured_parts.append(f"## {text}\n")
                elif level == 3:
                    structured_parts.append(f"### {text}\n")
                else:
                    structured_parts.append(f"**{text}**\n")
            
            elif element.name == 'p':
                # Paragraphs
                structured_parts.append(f"{text}\n")
            
            elif element.name in ['ul', 'ol']:
                # Lists
                list_items = []
                for li in element.find_all('li'):
                    li_text = li.get_text().strip()
                    if li_text:
                        if element.name == 'ul':
                            list_items.append(f"• {li_text}")
                        else:
                            list_items.append(f"{len(list_items) + 1}. {li_text}")
                
                if list_items:
                    structured_parts.append('\n'.join(list_items) + '\n')
            
            elif element.name == 'blockquote':
                # Quotes
                structured_parts.append(f"> {text}\n")
        
        # If no structured content found, fall back to all paragraphs
        if not structured_parts:
            paragraphs = container.find_all('p')
            for p in paragraphs:
                p_text = p.get_text().strip()
                if p_text and len(p_text) > 20:  # Only substantial paragraphs
                    structured_parts.append(f"{p_text}\n")
        
        content = '\n'.join(structured_parts).strip()
        
        # Clean up extra newlines but preserve structure
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return self._final_content_cleanup(content)
    
    def _is_meaningful_element(self, element: Tag) -> bool:
        """Check if element contains meaningful content"""
        text = element.get_text().strip()
        
        # Skip empty elements
        if not text or len(text) < 5:
            return False
        
        # Skip elements that are likely navigation or metadata
        unwanted_patterns = [
            r'^\s*compartir\s*$',
            r'^\s*seguir\s*$',
            r'^\s*tags?\s*[:.]',
            r'^\s*autor\s*[:.]',
            r'^\s*fecha\s*[:.]',
            r'^\s*fuente\s*[:.]',
        ]
        
        for pattern in unwanted_patterns:
            if re.match(pattern, text.lower()):
                return False
        
        return True
    
    def _enhance_newspaper_content(self, newspaper_text: str, soup: BeautifulSoup) -> str:
        """Enhance newspaper3k content with structure from HTML"""
        if not newspaper_text:
            return ""
        
        # Try to find headings in the original HTML
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        heading_texts = [h.get_text().strip() for h in headings if h.get_text().strip()]
        
        enhanced_text = newspaper_text
        
        # Add markdown formatting to headings that appear in the text
        for heading in heading_texts:
            if heading in enhanced_text and len(heading) > 10:
                # Replace heading with markdown formatted version
                enhanced_text = enhanced_text.replace(
                    heading,
                    f"## {heading}"
                )
        
        return self._final_content_cleanup(enhanced_text)
    
    # Provider-specific extraction methods
    def _remove_unwanted_elements_provider(self, soup: BeautifulSoup, provider_config: Dict[str, Any]):
        """Remove unwanted elements based on provider configuration"""
        # Remove elements by selector
        remove_elements = provider_config.get('remove_elements', [])
        for selector in remove_elements:
            for element in soup.select(selector):
                element.decompose()
        
        # Remove elements by class patterns  
        remove_classes = provider_config.get('remove_classes', [])
        for class_pattern in remove_classes:
            for element in soup.find_all(class_=re.compile(class_pattern, re.I)):
                element.decompose()
    
    def _extract_title_provider(self, soup: BeautifulSoup, provider_config: Dict[str, Any]) -> str:
        """Extract title using provider-specific selectors"""
        title_selectors = provider_config.get('title', {}).get('selectors', ['h1', 'title'])
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get('content') if element.get('content') else element.get_text()
                if title and len(title.strip()) > 5:
                    return self._clean_title_provider(title.strip(), provider_config)
        
        return ""
    
    def _clean_title_provider(self, title: str, provider_config: Dict[str, Any]) -> str:
        """Clean title using provider-specific patterns"""
        cleanup_patterns = provider_config.get('title', {}).get('cleanup_patterns', [])
        
        for pattern in cleanup_patterns:
            title = re.sub(pattern, '', title, flags=re.I)
        
        return title.strip()
    
    def _extract_content_provider(self, soup: BeautifulSoup, provider_config: Dict[str, Any]) -> str:
        """Extract content using provider-specific selectors"""
        content_selectors = provider_config.get('content', {}).get('selectors', ['article'])
        
        article_container = None
        for selector in content_selectors:
            container = soup.select_one(selector)
            if container:
                article_container = container
                break
        
        if not article_container:
            return ""
        
        # Extract content using provider-specific elements
        include_elements = provider_config.get('content', {}).get('include_elements', ['p', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        return self._process_provider_content_structure(article_container, include_elements)
    
    def _process_provider_content_structure(self, container: Tag, include_elements: List[str]) -> str:
        """Process content structure based on provider configuration"""
        structured_parts = []
        
        # Create CSS selector from include_elements list
        selector = ', '.join(include_elements)
        elements = container.select(selector)
        
        for element in elements:
            if not self._is_meaningful_element(element):
                continue
                
            text = element.get_text().strip()
            if not text:
                continue
            
            # Process based on element type (same as before but more flexible)
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(element.name[1])
                if level == 1:
                    structured_parts.append(f"# {text}\n")
                elif level == 2:
                    structured_parts.append(f"## {text}\n")
                elif level == 3:
                    structured_parts.append(f"### {text}\n")
                else:
                    structured_parts.append(f"**{text}**\n")
            
            elif element.name == 'p':
                structured_parts.append(f"{text}\n")
            
            elif element.name in ['ul', 'ol']:
                list_items = []
                for li in element.find_all('li'):
                    li_text = li.get_text().strip()
                    if li_text:
                        if element.name == 'ul':
                            list_items.append(f"• {li_text}")
                        else:
                            list_items.append(f"{len(list_items) + 1}. {li_text}")
                
                if list_items:
                    structured_parts.append('\n'.join(list_items) + '\n')
            
            elif element.name == 'blockquote':
                structured_parts.append(f"> {text}\n")
        
        content = '\n'.join(structured_parts).strip()
        content = re.sub(r'\n{3,}', '\n\n', content)  # Clean up excessive newlines
        
        return content
    
    def _apply_provider_cleanup(self, content: str, provider_config: Dict[str, Any]) -> str:
        """Apply provider-specific text cleanup patterns"""
        if not content:
            return ""
        
        cleanup_patterns = provider_config.get('cleanup_patterns', [])
        
        for pattern in cleanup_patterns:
            content = re.sub(pattern, '', content, flags=re.I | re.MULTILINE)
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Max 2 consecutive newlines
        content = re.sub(r'[ \t]+', ' ', content)  # Normalize spaces
        content = content.strip()
        
        # Apply length limits from provider config
        max_length = provider_config.get('content', {}).get('max_length', self.config.max_article_length)
        if len(content) > max_length:
            content = content[:max_length]
            # Try to end at a sentence or paragraph
            last_sentence = max(content.rfind('.'), content.rfind('\n\n'))
            if last_sentence > max_length * 0.8:
                content = content[:last_sentence + 1]
        
        return content
    
    def _extract_authors_provider(self, soup: BeautifulSoup, provider_config: Dict[str, Any]) -> List[str]:
        """Extract authors using provider configuration"""
        author_selectors = provider_config.get('author', {}).get('selectors', ['.author', '.autor'])
        
        authors = []
        for selector in author_selectors:
            elements = soup.select(selector)
            for element in elements:
                author = element.get('content') or element.get_text()
                if author and author.strip():
                    authors.append(author.strip())
        
        return list(set(authors))  # Remove duplicates
    
    def _extract_publish_date_provider(self, soup: BeautifulSoup, provider_config: Dict[str, Any]):
        """Extract publish date using provider configuration"""
        date_selectors = provider_config.get('date', {}).get('selectors', ['time', '.date'])
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date_str = element.get('content') or element.get('datetime') or element.get_text()
                if date_str:
                    return date_str.strip()
        
        return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title"""
        selectors = [
            'h1.titulo',                # Clarín specific
            'h1.title',
            'h1',
            '[property="og:title"]',
            'title',
            '.headline',
            '.article-title',
            '.post-title',
            '.nota-titulo',
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get('content') if element.get('content') else element.get_text()
                if title and len(title.strip()) > 5:
                    return self._clean_title(title.strip())
        
        return ""
    
    def _clean_title(self, title: str) -> str:
        """Clean extracted title"""
        # Remove common title suffixes from Argentine news sites
        suffixes_to_remove = [
            r'\s*\|\s*Clarín',
            r'\s*\|\s*LA NACION',
            r'\s*\|\s*Página\/12',
            r'\s*\|\s*Infobae',
            r'\s*\|\s*Ámbito',
            r'\s*\|\s*TN',
            r'\s*-\s*[^-]*$',  # Remove trailing site names
        ]
        
        for suffix in suffixes_to_remove:
            title = re.sub(suffix, '', title, flags=re.I)
        
        return title.strip()
    
    def _extract_authors(self, soup: BeautifulSoup) -> List[str]:
        """Extract article authors"""
        author_selectors = [
            '[property="author"]',
            '.author',
            '.autor',
            '.byline',
            '.writer',
        ]
        
        authors = []
        for selector in author_selectors:
            elements = soup.select(selector)
            for element in elements:
                author = element.get('content') or element.get_text()
                if author and author.strip():
                    authors.append(author.strip())
        
        return list(set(authors))  # Remove duplicates
    
    def _extract_publish_date(self, soup: BeautifulSoup):
        """Extract publish date"""
        date_selectors = [
            '[property="article:published_time"]',
            '[name="publish_date"]',
            '.fecha',
            '.date',
            'time',
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date_str = element.get('content') or element.get('datetime') or element.get_text()
                if date_str:
                    return date_str.strip()
        
        return None
    
    def _final_content_cleanup(self, content: str) -> str:
        """Final cleanup of extracted content"""
        if not content:
            return ""
        
        # Remove common unwanted phrases
        unwanted_phrases = [
            r'Suscribite.*?newsletter.*?\n',
            r'Seguinos.*?redes.*?\n',
            r'Compartir.*?\n',
            r'Tags.*?\n',
            r'Publicidad.*?\n',
            r'Te puede interesar.*?\n',
            r'Más información.*?\n',
        ]
        
        for phrase in unwanted_phrases:
            content = re.sub(phrase, '', content, flags=re.I | re.DOTALL)
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Max 2 consecutive newlines
        content = re.sub(r'[ \t]+', ' ', content)  # Normalize spaces
        content = content.strip()
        
        # Don't truncate here - let Reddit client handle splitting
        # Just ensure we don't process extremely long articles
        if len(content) > self.config.max_article_length:
            content = content[:self.config.max_article_length]
            # Try to end at a sentence or paragraph
            last_sentence = max(content.rfind('.'), content.rfind('\n\n'))
            if last_sentence > self.config.max_article_length * 0.8:
                content = content[:last_sentence + 1]
        
        return content
    
    def _is_valid_article(self, article_data: Dict[str, Any], provider_config: Dict[str, Any]) -> bool:
        """Validate extracted article data using provider configuration"""
        if not article_data:
            return False
        
        content = article_data.get('content', '')
        title = article_data.get('title', '')
        
        # Get provider-specific limits
        min_length = provider_config.get('content', {}).get('min_length', self.config.min_article_length)
        
        # Check minimum content length
        if len(content) < min_length:
            logger.debug(f"Article too short: {len(content)} characters (min: {min_length})")
            return False
        
        # Check if we have a title
        if not title or len(title) < 10:
            logger.debug("Article missing valid title")
            return False
        
        # Check provider-specific rejection patterns
        reject_patterns = provider_config.get('quality', {}).get('reject_if_contains', [])
        for pattern in reject_patterns:
            if re.search(pattern, content, re.I | re.MULTILINE):
                logger.debug(f"Article content matches rejection pattern: {pattern}")
                return False
        
        # Check content quality with provider-specific ratio
        min_ratio = provider_config.get('quality', {}).get('min_text_ratio', 0.6)
        if self._is_low_quality_content_provider(content, min_ratio):
            return False
        
        return True
    
    def _is_low_quality_content_provider(self, content: str, min_text_ratio: float) -> bool:
        """Check if content appears to be low quality using provider config"""
        # Check for excessive repetition
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if len(lines) > 5 and len(set(lines)) < len(lines) * min_text_ratio:
            logger.debug("Content has too many duplicate lines")
            return True
        
        # Check for reasonable word diversity
        words = content.lower().split()
        if len(words) > 50 and len(set(words)) < len(words) * (min_text_ratio * 0.7):
            logger.debug("Content has poor word diversity")
            return True
        
        return False
    
    def _is_low_quality_content(self, content: str) -> bool:
        """Check if content appears to be low quality"""
        # Check for excessive repetition
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if len(set(lines)) < len(lines) * 0.7:  # Too many duplicate lines
            return True
        
        # Check for reasonable word diversity
        words = content.lower().split()
        if len(words) > 50 and len(set(words)) < len(words) * 0.4:
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