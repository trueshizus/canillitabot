from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup

class BaseProvider(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def extract_article(self, url: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_title(self, soup: BeautifulSoup) -> str:
        pass

    @abstractmethod
    def get_content(self, soup: BeautifulSoup) -> str:
        pass

    def get_authors(self, soup: BeautifulSoup) -> List[str]:
        return []

    def get_publish_date(self, soup: BeautifulSoup) -> Optional[str]:
        return None
