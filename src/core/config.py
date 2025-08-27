"""
Enhanced configuration system with environment-based overrides and better structure.
Supports multiple environments (development, staging, production) and comprehensive validation.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Union, Type
from urllib.parse import urlparse
import logging
from .schemas import (
    RedditConfig, DatabaseConfig, QueueConfig, LoggingConfig,
    ExtractionConfig, YouTubeConfig, TwitterConfig, BotConfig, MonitoringConfig
)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Configuration-related errors"""
    pass

class EnvironmentConfig:
    """Environment-specific configuration management"""
    
    ENVIRONMENTS = ['development', 'staging', 'production']
    
    def __init__(self, environment: str = None):
        self.environment = environment or self._detect_environment()
        self.project_root = Path(__file__).parent.parent.parent
        self._load_env_file()
    
    def _detect_environment(self) -> str:
        """Detect current environment from ENV variable or default to development"""
        env = os.getenv('ENVIRONMENT', os.getenv('ENV', 'development')).lower()
        if env not in self.ENVIRONMENTS:
            logger.warning(f"Unknown environment '{env}', defaulting to 'development'")
            env = 'development'
        return env
    
    def _load_env_file(self):
        """Load environment-specific .env file"""
        # Try environment-specific env file first
        env_file = self.project_root / f".env.{self.environment}"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"Loaded environment file: {env_file}")
        
        # Then load general .env file for defaults
        general_env = self.project_root / ".env"
        if general_env.exists():
            load_dotenv(general_env)
            logger.debug(f"Loaded general environment file: {general_env}")
    
    def get_config_path(self, filename: str) -> Path:
        """Get path for a configuration file, with environment-specific override"""
        # Try environment-specific config first
        env_specific = self.project_root / "config" / self.environment / filename
        if env_specific.exists():
            return env_specific
        
        # Fall back to general config
        general = self.project_root / "config" / filename
        if general.exists():
            return general
        
        raise FileNotFoundError(f"Configuration file '{filename}' not found for environment '{self.environment}'")

class Config:
    """Enhanced configuration system with environment support and validation"""
    
    def __init__(self, environment: str = None):
        self.env_config = EnvironmentConfig(environment)
        self.environment = self.env_config.environment
        
        # Load base configuration files
        self.settings = self._load_yaml(self.env_config.get_config_path("settings.yaml"))
        
        try:
            self.domains_config = self._load_yaml(self.env_config.get_config_path("domains.yaml"))
        except FileNotFoundError:
            logger.warning("domains.yaml not found, using empty domain configuration")
            self.domains_config = {'news_domains': [], 'blocked_domains': []}
        
        # Initialize configuration sections
        self._init_config_sections()
        
        # Cache for loaded provider configurations
        self._provider_cache = {}
        self._default_provider = None
        
        # Create necessary directories
        self._create_directories()
        
        # Log configuration summary
        logger.info(f"Configuration loaded for environment: {self.environment}")
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration file with better error handling"""
        try:
            with open(path, 'r', encoding='utf-8') as file:
                content = yaml.safe_load(file)
                return content or {}
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {path}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration from {path}: {e}")
    
    def _init_config_sections(self):
        """Initialize structured configuration sections"""
        self.reddit = self._create_reddit_config()
        self.database = self._create_database_config()
        self.queue = self._create_queue_config()
        self.logging = self._create_logging_config()
        self.extraction = self._create_extraction_config()
        self.youtube = self._create_youtube_config()
        self.twitter = self._create_twitter_config()
        self.bot = self._create_bot_config()
        self.monitoring = self._create_monitoring_config()
    
    def _create_reddit_config(self) -> RedditConfig:
        """Create Reddit configuration with environment overrides"""
        config = RedditConfig()
        
        # Environment variables take precedence
        config.client_id = os.getenv('REDDIT_CLIENT_ID', '')
        config.client_secret = os.getenv('REDDIT_CLIENT_SECRET', '')
        config.username = os.getenv('REDDIT_USERNAME', '')
        config.password = os.getenv('REDDIT_PASSWORD', '')
        config.user_agent = os.getenv('REDDIT_USER_AGENT', 
                                     self.settings.get('extraction', {}).get('user_agent', config.user_agent))
        
        # Subreddits from environment or config
        env_subreddits = os.getenv('REDDIT_SUBREDDITS')
        if env_subreddits:
            config.subreddits = [sub.strip() for sub in env_subreddits.split(',') if sub.strip()]
        else:
            config.subreddits = self.settings.get('reddit', {}).get('subreddits', 
                                ['argentina', 'ArgentinaBenderStyle', 'DerechoGenial'])
        
        return config
    
    def _create_database_config(self) -> DatabaseConfig:
        """Create database configuration"""
        config = DatabaseConfig()
        db_settings = self.settings.get('database', {})
        
        config.path = os.getenv('DATABASE_PATH', db_settings.get('path', config.path))
        config.cleanup_days = int(os.getenv('DATABASE_CLEANUP_DAYS', 
                                          db_settings.get('cleanup_days', config.cleanup_days)))
        config.backup_enabled = self._get_bool_env('DATABASE_BACKUP_ENABLED', 
                                                  db_settings.get('backup_enabled', config.backup_enabled))
        config.backup_interval_hours = int(os.getenv('DATABASE_BACKUP_INTERVAL', 
                                                   db_settings.get('backup_interval_hours', config.backup_interval_hours)))
        
        return config
    
    def _create_queue_config(self) -> QueueConfig:
        """Create queue configuration"""
        config = QueueConfig()
        queue_settings = self.settings.get('queue', {})
        
        config.enabled = self._get_bool_env('QUEUE_ENABLED', queue_settings.get('enabled', config.enabled))
        config.redis_url = os.getenv('REDIS_URL', queue_settings.get('redis_url', config.redis_url))
        config.worker_timeout = int(os.getenv('QUEUE_WORKER_TIMEOUT', 
                                            queue_settings.get('worker_timeout', config.worker_timeout)))
        config.max_retries = int(os.getenv('QUEUE_MAX_RETRIES', 
                                         queue_settings.get('max_retries', config.max_retries)))
        
        # Retry delays from config or default
        retry_delays = queue_settings.get('retry_delays', config.retry_delays)
        if isinstance(retry_delays, list):
            config.retry_delays = retry_delays
        
        return config
    
    def _create_logging_config(self) -> LoggingConfig:
        """Create logging configuration"""
        config = LoggingConfig()
        log_settings = self.settings.get('logging', {})
        
        config.level = os.getenv('LOG_LEVEL', log_settings.get('level', config.level))
        config.format = log_settings.get('format', config.format)
        config.file = os.getenv('LOG_FILE', log_settings.get('file', config.file))
        config.structured = self._get_bool_env('LOG_STRUCTURED', 
                                              log_settings.get('structured', config.structured))
        config.error_tracking = self._get_bool_env('LOG_ERROR_TRACKING', 
                                                  log_settings.get('error_tracking', config.error_tracking))
        config.max_file_size_mb = int(os.getenv('LOG_MAX_SIZE_MB', 
                                              log_settings.get('max_file_size_mb', config.max_file_size_mb)))
        config.backup_count = int(os.getenv('LOG_BACKUP_COUNT', 
                                          log_settings.get('backup_count', config.backup_count)))
        
        return config
    
    def _create_extraction_config(self) -> ExtractionConfig:
        """Create extraction configuration"""
        config = ExtractionConfig()
        ext_settings = self.settings.get('extraction', {})
        
        config.timeout = int(os.getenv('EXTRACTION_TIMEOUT', 
                                     ext_settings.get('timeout', config.timeout)))
        config.max_retries = int(os.getenv('EXTRACTION_MAX_RETRIES', 
                                         ext_settings.get('max_retries', config.max_retries)))
        config.user_agent = os.getenv('EXTRACTION_USER_AGENT', 
                                    ext_settings.get('user_agent', config.user_agent))
        
        return config
    
    def _create_youtube_config(self) -> YouTubeConfig:
        """Create YouTube configuration"""
        config = YouTubeConfig()
        yt_settings = self.settings.get('youtube', {})
        
        config.enabled = self._get_bool_env('YOUTUBE_ENABLED', yt_settings.get('enabled', config.enabled))
        config.summary_template = yt_settings.get('summary_template', config.summary_template)
        
        return config
    
    def _create_twitter_config(self) -> TwitterConfig:
        """Create Twitter configuration"""
        config = TwitterConfig()
        tw_settings = self.settings.get('x_twitter', {})
        
        config.enabled = self._get_bool_env('TWITTER_ENABLED', tw_settings.get('enabled', config.enabled))
        config.comment_template = tw_settings.get('comment_template', config.comment_template)
        
        return config
    
    def _create_bot_config(self) -> BotConfig:
        """Create bot configuration"""
        config = BotConfig()
        bot_settings = self.settings.get('bot', {})
        reddit_settings = self.settings.get('reddit', {})
        
        config.comment_template = bot_settings.get('comment_template', config.comment_template)
        config.continuation_template = bot_settings.get('continuation_template', config.continuation_template)
        config.max_comment_length = int(os.getenv('BOT_MAX_COMMENT_LENGTH', 
                                                bot_settings.get('max_comment_length', config.max_comment_length)))
        config.check_interval = int(os.getenv('BOT_CHECK_INTERVAL', 
                                            reddit_settings.get('check_interval', config.check_interval)))
        config.max_posts_per_check = int(os.getenv('BOT_MAX_POSTS_PER_CHECK', 
                                                 reddit_settings.get('max_posts_per_check', config.max_posts_per_check)))
        
        return config
    
    def _create_monitoring_config(self) -> MonitoringConfig:
        """Create monitoring configuration"""
        config = MonitoringConfig()
        mon_settings = self.settings.get('monitoring', {})
        
        config.enabled = self._get_bool_env('MONITORING_ENABLED', 
                                           mon_settings.get('enabled', config.enabled))
        config.health_check_interval = int(os.getenv('MONITORING_HEALTH_CHECK_INTERVAL', 
                                                    mon_settings.get('health_check_interval', config.health_check_interval)))
        config.metrics_retention_days = int(os.getenv('MONITORING_METRICS_RETENTION', 
                                                     mon_settings.get('metrics_retention_days', config.metrics_retention_days)))
        
        # Alert thresholds
        thresholds = mon_settings.get('alert_thresholds', {})
        config.alert_thresholds.update(thresholds)
        
        return config
    
    def _get_bool_env(self, env_var: str, default: bool) -> bool:
        """Get boolean value from environment variable"""
        value = os.getenv(env_var)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            Path(self.database.path).parent,
            Path(self.logging.file).parent,
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                raise ConfigurationError(f"Cannot create required directory: {directory}")
    
    def validate(self):
        """Validate configuration and raise errors if invalid"""
        errors = []
        
        # Reddit configuration validation
        if not self.reddit.client_id:
            errors.append("REDDIT_CLIENT_ID is required")
        if not self.reddit.client_secret:
            errors.append("REDDIT_CLIENT_SECRET is required")
        if not self.reddit.username:
            errors.append("REDDIT_USERNAME is required")
        if not self.reddit.password:
            errors.append("REDDIT_PASSWORD is required")
        if not self.reddit.subreddits:
            errors.append("At least one subreddit must be configured")
        
        # YouTube configuration validation
        if self.youtube.enabled:
            if not os.getenv('GEMINI_API_KEY'):
                errors.append("GEMINI_API_KEY is required when YouTube processing is enabled")
        
        # Queue configuration validation
        if self.queue.enabled:
            try:
                parsed_url = urlparse(self.queue.redis_url)
                if not parsed_url.scheme.startswith('redis'):
                    errors.append("Invalid Redis URL format")
            except Exception:
                errors.append("Invalid Redis URL")
        
        # Logging configuration validation
        if self.logging.level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            errors.append(f"Invalid log level: {self.logging.level}")
        
        if errors:
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
        
        logger.info("Configuration validation passed")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging/debugging"""
        return {
            'environment': self.environment,
            'reddit': {
                'subreddits': self.reddit.subreddits,
                'credentials_configured': bool(self.reddit.client_id and self.reddit.client_secret)
            },
            'features': {
                'youtube_enabled': self.youtube.enabled,
                'twitter_enabled': self.twitter.enabled,
                'queue_enabled': self.queue.enabled,
                'monitoring_enabled': self.monitoring.enabled
            },
            'intervals': {
                'check_interval': self.bot.check_interval,
                'cleanup_days': self.database.cleanup_days
            }
        }

    def _extract_domain(self, url: str) -> str:
        """Extracts the domain from a URL."""
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        return urlparse(url).netloc.replace('www.', '')
    
    # Legacy compatibility properties
    @property
    def subreddits(self) -> List[str]:
        return self.reddit.subreddits
    
    @property
    def check_interval(self) -> int:
        return self.bot.check_interval
    
    @property
    def max_posts_per_check(self) -> int:
        return self.bot.max_posts_per_check
    
    @property
    def youtube_enabled(self) -> bool:
        return self.youtube.enabled
    
    @property
    def x_twitter_enabled(self) -> bool:
        return self.twitter.enabled
    
    @property
    def queue_enabled(self) -> bool:
        return self.queue.enabled
    
    @property
    def database_path(self) -> str:
        return self.database.path
    
    @property
    def cleanup_days(self) -> int:
        return self.database.cleanup_days
    
    @property
    def log_level(self) -> str:
        return self.logging.level
    
    @property
    def log_format(self) -> str:
        return self.logging.format
    
    @property
    def log_file(self) -> str:
        return self.logging.file
    
    @property
    def structured_logging(self) -> bool:
        return self.logging.structured
    
    @property
    def comment_template(self) -> str:
        return self.bot.comment_template
    
    @property
    def youtube_summary_template(self) -> str:
        return self.youtube.summary_template
    
    @property
    def x_twitter_comment_template(self) -> str:
        return self.twitter.comment_template
    
    @property
    def news_domains(self) -> List[str]:
        return self.domains_config.get('news_domains', [])
    
    @property
    def blocked_domains(self) -> List[str]:
        return self.domains_config.get('blocked_domains', [])

    @property
    def max_retries(self) -> int:
        return self.extraction.max_retries
    
    @property
    def extraction_user_agent(self) -> str:
        return self.extraction.extraction_user_agent

    @property
    def extraction_timeout(self) -> int:
        return self.extraction.timeout

    @property
    def max_article_length(self) -> int:
        return self.extraction.max_article_length

    @property
    def min_article_length(self) -> int:
        return self.extraction.min_article_length

    @property
    def max_comment_length(self) -> int:
        return self.bot.max_comment_length
    
    # Additional legacy compatibility properties
    @property
    def reddit_client_id(self) -> str:
        return self.reddit.client_id
    
    @property
    def reddit_client_secret(self) -> str:
        return self.reddit.client_secret
    
    @property
    def reddit_username(self) -> str:
        return self.reddit.username
    
    @property
    def reddit_password(self) -> str:
        return self.reddit.password
    
    @property
    def reddit_user_agent(self) -> str:
        return self.reddit.user_agent
    
    @property
    def gemini_api_key(self) -> str:
        return os.getenv('GEMINI_API_KEY', '')
    
    # Provider configuration methods (from original config)
    def get_provider_config(self, domain: str) -> Dict[str, Any]:
        """Get provider configuration for a domain"""
        if domain in self._provider_cache:
            return self._provider_cache[domain]
        
        provider_file = self.env_config.project_root / "config" / "providers" / f"{domain}.yaml"
        
        if provider_file.exists():
            try:
                provider_config = self._load_yaml(provider_file)
                self._provider_cache[domain] = provider_config
                return provider_config
            except Exception as e:
                logger.warning(f"Failed to load provider config for {domain}: {e}")
        
        # Return default provider config
        return self.get_default_provider_config()
    
    def get_default_provider_config(self) -> Dict[str, Any]:
        """Get default provider configuration"""
        if self._default_provider is not None:
            return self._default_provider
        
        default_file = self.env_config.project_root / "config" / "providers" / "default.yaml"
        
        try:
            self._default_provider = self._load_yaml(default_file)
            return self._default_provider
        except Exception as e:
            logger.error(f"Failed to load default provider config: {e}")
            # Return minimal fallback config
            return {
                'content_selectors': ['article', '.content', '#content', 'main'],
                'remove_selectors': ['.advertisement', '.ads', '.related-articles'],
                'quality_threshold': 0.3
            }