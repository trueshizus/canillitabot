import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

class Config:
    def __init__(self, config_path: str = "config/settings.yaml", domains_path: str = "config/domains.yaml"):
        load_dotenv()
        
        self.project_root = Path(__file__).parent.parent
        self.config_path = self.project_root / config_path
        self.domains_path = self.project_root / domains_path
        self.providers_path = self.project_root / "config" / "providers"
        
        self.settings = self._load_yaml(self.config_path)
        self.domains = self._load_yaml(self.domains_path)
        
        # Cache for loaded provider configurations
        self._provider_cache = {}
        self._default_provider = None
        
        # Create necessary directories
        self._create_directories()
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")
    
    def _create_directories(self):
        """Create necessary directories"""
        # Database directory
        db_path = Path(self.settings['database']['path'])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Logs directory
        log_path = Path(self.settings['logging']['file'])
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Reddit configuration
    @property
    def reddit_client_id(self) -> str:
        return os.getenv('REDDIT_CLIENT_ID', '')
    
    @property
    def reddit_client_secret(self) -> str:
        return os.getenv('REDDIT_CLIENT_SECRET', '')
    
    @property
    def reddit_username(self) -> str:
        return os.getenv('REDDIT_USERNAME', '')
    
    @property
    def reddit_password(self) -> str:
        return os.getenv('REDDIT_PASSWORD', '')
    
    @property
    def reddit_user_agent(self) -> str:
        return os.getenv('REDDIT_USER_AGENT', self.settings['extraction']['user_agent'])
    
    @property
    def subreddits(self) -> List[str]:
        return self.settings['reddit']['subreddits']
    
    @property
    def check_interval(self) -> int:
        return self.settings['reddit']['check_interval']
    
    @property
    def max_posts_per_check(self) -> int:
        return self.settings['reddit']['max_posts_per_check']
    
    # Bot configuration
    @property
    def comment_template(self) -> str:
        return self.settings['bot']['comment_template']
    
    @property
    def continuation_template(self) -> str:
        return self.settings['bot']['continuation_template']
    
    @property
    def max_comment_length(self) -> int:
        return self.settings['bot']['max_comment_length']
    
    @property
    def max_article_length(self) -> int:
        return self.settings['bot']['max_article_length']
    
    @property
    def min_article_length(self) -> int:
        return self.settings['bot']['min_article_length']
    
    # Extraction configuration
    @property
    def extraction_timeout(self) -> int:
        return self.settings['extraction']['timeout']
    
    @property
    def max_retries(self) -> int:
        return self.settings['extraction']['max_retries']
    
    @property
    def extraction_user_agent(self) -> str:
        return self.settings['extraction']['user_agent']
    
    # Domain configuration
    @property
    def news_domains(self) -> List[str]:
        return self.domains['news_domains']
    
    @property
    def blocked_domains(self) -> List[str]:
        return self.domains['blocked_domains']
    
    # Provider-specific configuration methods
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return ""
    
    def _load_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Load provider configuration from file"""
        # Try different filename variations
        possible_names = [
            provider_name,  # exact match (e.g., "infobae.com")
            provider_name.replace('.com', ''),  # remove .com (e.g., "infobae") 
            provider_name.replace('.com.ar', ''),  # remove .com.ar (e.g., "lanacion")
            provider_name.split('.')[0]  # first part only (e.g., "infobae" from "infobae.com")
        ]
        
        for name in possible_names:
            provider_file = self.providers_path / f"{name}.yaml"
            if provider_file.exists():
                try:
                    return self._load_yaml(provider_file)
                except Exception as e:
                    print(f"Error loading provider config {name}: {e}")
                    continue
        
        return None
    
    def get_default_provider_config(self) -> Dict[str, Any]:
        """Get default provider configuration"""
        if self._default_provider is None:
            self._default_provider = self._load_provider_config("default") or {}
        return self._default_provider
    
    def get_provider_config(self, url: str) -> Dict[str, Any]:
        """Get provider-specific configuration for a URL"""
        domain = self._extract_domain(url)
        
        # Check cache first
        if domain in self._provider_cache:
            return self._provider_cache[domain]
        
        # Try to load domain-specific config
        provider_config = self._load_provider_config(domain)
        
        if provider_config:
            # Cache successful load
            self._provider_cache[domain] = provider_config
            return provider_config
        
        # Fallback to default config
        default_config = self.get_default_provider_config()
        self._provider_cache[domain] = default_config
        return default_config
    
    def get_provider_for_domain(self, domain: str) -> Dict[str, Any]:
        """Get provider config directly by domain name"""
        if domain in self._provider_cache:
            return self._provider_cache[domain]
        
        provider_config = self._load_provider_config(domain)
        if provider_config:
            self._provider_cache[domain] = provider_config
            return provider_config
        
        default_config = self.get_default_provider_config()
        self._provider_cache[domain] = default_config
        return default_config
    
    # Database configuration
    @property
    def database_path(self) -> str:
        return self.settings['database']['path']
    
    @property
    def cleanup_days(self) -> int:
        return self.settings['database']['cleanup_days']
    
    # Logging configuration
    @property
    def log_level(self) -> str:
        return self.settings['logging']['level']
    
    @property
    def log_format(self) -> str:
        return self.settings['logging']['format']
    
    @property
    def log_file(self) -> str:
        return self.settings['logging']['file']
    
    def validate(self):
        """Validate configuration"""
        required_env_vars = [
            'REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 
            'REDDIT_USERNAME', 'REDDIT_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        if not self.subreddits:
            raise ValueError("No subreddits configured")
        
        if self.check_interval < 10:
            raise ValueError("Check interval must be at least 10 seconds")
        
        return True