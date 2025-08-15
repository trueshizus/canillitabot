import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any

class Config:
    def __init__(self, config_path: str = "config/settings.yaml", domains_path: str = "config/domains.yaml"):
        load_dotenv()
        
        self.project_root = Path(__file__).parent.parent
        self.config_path = self.project_root / config_path
        self.domains_path = self.project_root / domains_path
        
        self.settings = self._load_yaml(self.config_path)
        self.domains = self._load_yaml(self.domains_path)
        
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