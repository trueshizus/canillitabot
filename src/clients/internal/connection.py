import praw
import logging
from typing import Optional
from src.core.config import Config

logger = logging.getLogger(__name__)

class RedditConnection:
    """Handles Reddit API connection and authentication"""
    
    def __init__(self, config: Config):
        self.config = config
        self.reddit: Optional[praw.Reddit] = None
        self._connect()
    
    def _connect(self):
        """Initialize Reddit connection"""
        try:
            self.reddit = praw.Reddit(
                client_id=self.config.reddit_client_id,
                client_secret=self.config.reddit_client_secret,
                username=self.config.reddit_username,
                password=self.config.reddit_password,
                user_agent=self.config.reddit_user_agent
            )
            
            # Test connection and validate credentials
            self._validate_credentials()
            
        except Exception as e:
            logger.error(f"Failed to connect to Reddit: {e}")
            raise
    
    def _validate_credentials(self):
        """Validate Reddit API credentials by testing basic operations"""
        try:
            # Test basic authentication
            user = self.reddit.user.me()
            if not user:
                raise ValueError("Unable to authenticate - check username and password")
            
            logger.info(f"✓ Connected to Reddit as: {user.name}")
            
            # Test API access
            try:
                # Try to access a basic endpoint
                list(self.reddit.subreddit("test").new(limit=1))
                logger.info("✓ Reddit API access validated")
            except Exception as api_error:
                logger.warning(f"Reddit API access test failed: {api_error}")
                # Don't fail completely, might be temporary
            
            # Validate bot account status
            if user.is_suspended:
                raise ValueError(f"Bot account {user.name} is suspended")
            
            # Check account age (optional warning)
            if hasattr(user, 'created_utc') and user.created_utc:
                import time
                account_age_days = (time.time() - user.created_utc) / 86400
                if account_age_days < 1:
                    logger.warning("⚠ Bot account is very new - may face additional restrictions")
                
            logger.info("✓ Credentials validation complete")
            
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            raise ValueError(f"Reddit credentials validation failed: {e}")
    
    def get_reddit_instance(self) -> praw.Reddit:
        """Get the Reddit API instance"""
        if not self.reddit:
            raise ValueError("Reddit connection not established")
        return self.reddit
