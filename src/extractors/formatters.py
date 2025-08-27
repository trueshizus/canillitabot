"""
Content formatting and cleanup utilities for article extraction.
"""

import re
from typing import List
from bs4 import BeautifulSoup, Tag

def process_article_structure(container: Tag, include_elements: List[str]) -> str:
    """Processes the structure of an article container into a formatted string."""
    structured_parts = []
    
    selector = ", ".join(include_elements)
    elements = container.select(selector)
    
    for element in elements:
        if not _is_meaningful_element(element):
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
    return content.strip()

def final_content_cleanup(content: str, provider_config: dict) -> str:
    """Applies final cleanup patterns to the extracted content."""
    if not content:
        return ""
    
    cleanup_patterns = provider_config.get('cleanup_patterns', [])
    
    for pattern in cleanup_patterns:
        content = re.sub(pattern, '', content, flags=re.I | re.MULTILINE)
    
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    content = re.sub(r'[ \t]+', ' ', content)
    content = content.strip()
    
    max_length = provider_config.get('content', {}).get('max_length', 50000)
    if len(content) > max_length:
        content = content[:max_length]
        last_sentence = max(content.rfind('.'), content.rfind('\n\n'))
        if last_sentence > max_length * 0.8:
            content = content[:last_sentence + 1]
    
    return content

def _is_meaningful_element(element: Tag) -> bool:
    """Checks if an element contains meaningful text."""
    text = element.get_text().strip()
    
    if not text or len(text) < 5:
        return False
    
    unwanted_patterns = [
        r'^\s*compartir\s*$',
        r'^\s*seguir\s*$',
        r'^\s*tags?[:.]',
        r'^\s*autor[:.]',
        r'^\s*fecha[:.]',
        r'^\s*fuente[:.]',
    ]
    
    for pattern in unwanted_patterns:
        if re.match(pattern, text.lower()):
            return False
    
    return True
