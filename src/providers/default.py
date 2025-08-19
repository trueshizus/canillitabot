import requests
import logging
import re
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup, Tag
from newspaper import Article
from providers.base import BaseProvider

logger = logging.getLogger(__name__)

class DefaultProvider(BaseProvider):
    def __init__(self, config):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.extraction_user_agent
        })

    def extract_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract article content from URL with provider-specific formatting"""
        try:
            provider_config = self.config.get_provider_config(url)
            domain = self.config._extract_domain(url)
            
            logger.info(f"Using provider '{provider_config.get('name', 'default')}' for domain '{domain}'")
            
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
                    
                    if article_data and self.is_valid_article(article_data, provider_config):
                        article_data['extraction_method'] = method
                        article_data['provider'] = provider_config.get('name', 'default')
                        return article_data
                        
                except Exception as e:
                    logger.error(f"Extraction method '{method}' failed for {url}: {e}")
                    continue
            
            logger.warning(f"All extraction methods failed for {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting article from {url}: {e}")
            return None

    def get_title(self, soup: BeautifulSoup, provider_config: Dict[str, Any]) -> str:
        title_selectors = provider_config.get('title', {}).get('selectors', ['h1', 'title'])
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get('content') if element.get('content') else element.get_text()
                if title and len(title.strip()) > 5:
                    return self._clean_title(title.strip(), provider_config)
        
        return ""

    def get_content(self, soup: BeautifulSoup, provider_config: Dict[str, Any]) -> str:
        content_selectors = provider_config.get('content', {}).get('selectors', ['article'])
        
        article_container = None
        for selector in content_selectors:
            container = soup.select_one(selector)
            if container:
                article_container = container
                break
        
        if not article_container:
            return ""
        
        include_elements = provider_config.get('content', {}).get('include_elements', ['p', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        return self._process_article_structure(article_container, include_elements)

    def get_authors(self, soup: BeautifulSoup, provider_config: Dict[str, Any]) -> List[str]:
        author_selectors = provider_config.get('author', {}).get('selectors', ['.author', '.autor'])
        
        authors = []
        for selector in author_selectors:
            elements = soup.select(selector)
            for element in elements:
                author = element.get('content') or element.get_text()
                if author and author.strip():
                    authors.append(author.strip())
        
        return list(set(authors))

    def get_publish_date(self, soup: BeautifulSoup, provider_config: Dict[str, Any]) -> Optional[str]:
        date_selectors = provider_config.get('date', {}).get('selectors', ['time', '.date'])
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date_str = element.get('content') or element.get('datetime') or element.get_text()
                if date_str:
                    return date_str.strip()
        
        return None

    def _extract_structured_content(self, url: str, provider_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(
                url, 
                timeout=self.config.extraction_timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            self._remove_unwanted_elements(soup, provider_config)
            
            title = self.get_title(soup, provider_config)
            
            structured_content = self.get_content(soup, provider_config)
            
            if not title or not structured_content:
                return None
            
            cleaned_content = self._final_content_cleanup(structured_content, provider_config)
            
            return {
                'title': title,
                'content': cleaned_content,
                'summary': '',
                'authors': self.get_authors(soup, provider_config),
                'publish_date': self.get_publish_date(soup, provider_config),
                'url': url,
                'extraction_method': 'provider_structured'
            }
            
        except Exception as e:
            logger.debug(f"Provider structured extraction failed for {url}: {e}")
            return None

    def _extract_with_newspaper_enhanced(self, url: str, provider_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            response = self.session.get(url, timeout=self.config.extraction_timeout)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            self._remove_unwanted_elements(soup, provider_config)
            
            enhanced_content = self._enhance_newspaper_content(article.text, soup)
            
            cleaned_content = self._final_content_cleanup(enhanced_content, provider_config)
            
            cleaned_title = self._clean_title(article.title, provider_config) if article.title else ""
            
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

    def _remove_unwanted_elements(self, soup: BeautifulSoup, provider_config: Dict[str, Any]):
        remove_elements = provider_config.get('remove_elements', [])
        for selector in remove_elements:
            for element in soup.select(selector):
                element.decompose()
        
        remove_classes = provider_config.get('remove_classes', [])
        for class_pattern in remove_classes:
            for element in soup.find_all(class_=re.compile(class_pattern, re.I)):
                element.decompose()

    def _process_article_structure(self, container: Tag, include_elements: List[str]) -> str:
        structured_parts = []
        
        selector = ', '.join(include_elements)
        elements = container.select(selector)
        
        for element in elements:
            if not self._is_meaningful_element(element):
                continue
                
            text = element.get_text().strip()
            if not text:
                continue
            
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
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        content = content.strip()
        
        max_length = provider_config.get('content', {}).get('max_length', self.config.max_article_length)
        if len(content) > max_length:
            content = content[:max_length]
            last_sentence = max(content.rfind('.'), content.rfind('\n\n'))
            if last_sentence > max_length * 0.8:
                content = content[:last_sentence + 1]
        
        return content

    def _is_meaningful_element(self, element: Tag) -> bool:
        text = element.get_text().strip()
        
        if not text or len(text) < 5:
            return False
        
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
        if not newspaper_text:
            return ""
        
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        heading_texts = [h.get_text().strip() for h in headings if h.get_text().strip()]
        
        enhanced_text = newspaper_text
        
        for heading in heading_texts:
            if heading in enhanced_text and len(heading) > 10:
                enhanced_text = enhanced_text.replace(
                    heading,
                    f"## {heading}"
                )
        
        return self._final_content_cleanup(enhanced_text, self.config.get_default_provider_config())

    def _clean_title(self, title: str, provider_config: Dict[str, Any]) -> str:
        cleanup_patterns = provider_config.get('title', {}).get('cleanup_patterns', [])
        
        for pattern in cleanup_patterns:
            title = re.sub(pattern, '', title, flags=re.I)
        
        return title.strip()

    def _final_content_cleanup(self, content: str, provider_config: Dict[str, Any]) -> str:
        if not content:
            return ""
        
        cleanup_patterns = provider_config.get('cleanup_patterns', [])
        
        for pattern in cleanup_patterns:
            content = re.sub(pattern, '', content, flags=re.I | re.MULTILINE)
        
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        content = content.strip()
        
        max_length = provider_config.get('content', {}).get('max_length', self.config.max_article_length)
        if len(content) > max_length:
            content = content[:max_length]
            last_sentence = max(content.rfind('.'), content.rfind('\n\n'))
            if last_sentence > max_length * 0.8:
                content = content[:last_sentence + 1]
        
        return content

    def is_valid_article(self, article_data: Dict[str, Any], provider_config: Dict[str, Any]) -> bool:
        if not article_data:
            return False
        
        content = article_data.get('content', '')
        title = article_data.get('title', '')
        
        min_length = provider_config.get('content', {}).get('min_length', self.config.min_article_length)
        
        if len(content) < min_length:
            logger.debug(f"Article too short: {len(content)} characters (min: {min_length})")
            return False
        
        if not title or len(title) < 10:
            logger.debug("Article missing valid title")
            return False
        
        reject_patterns = provider_config.get('quality', {}).get('reject_if_contains', [])
        for pattern in reject_patterns:
            if re.search(pattern, content, re.I | re.MULTILINE):
                logger.debug(f"Article content matches rejection pattern: {pattern}")
                return False
        
        min_ratio = provider_config.get('quality', {}).get('min_text_ratio', 0.6)
        if self._is_low_quality_content(content, min_ratio):
            return False
        
        return True

    def _is_low_quality_content(self, content: str, min_text_ratio: float) -> bool:
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if len(lines) > 5 and len(set(lines)) < len(lines) * min_text_ratio:
            logger.debug("Content has too many duplicate lines")
            return True
        
        words = content.lower().split()
        if len(words) > 50 and len(set(words)) < len(words) * (min_text_ratio * 0.7):
            logger.debug("Content has poor word diversity")
            return True
        
        return False
