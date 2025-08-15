import praw
import time
import logging
from typing import Iterator, Optional, List
from praw.models import Submission
from config import Config

logger = logging.getLogger(__name__)

class RedditClient:
    def __init__(self, config: Config):
        self.config = config
        self.reddit = None
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
    
    def get_new_posts(self, subreddit_name: str, limit: int = 10) -> Iterator[Submission]:
        """Get new posts from a subreddit"""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Get new submissions
            for submission in subreddit.new(limit=limit):
                yield submission
                
        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit_name}: {e}")
            return
    
    def is_news_article(self, submission: Submission) -> bool:
        """Check if submission contains a news article link"""
        if not submission.url:
            return False
        
        # Skip self posts
        if submission.is_self:
            return False
        
        # Check if URL domain is in news domains
        for domain in self.config.news_domains:
            if domain in submission.url.lower():
                # Make sure it's not in blocked domains
                for blocked in self.config.blocked_domains:
                    if blocked in submission.url.lower():
                        return False
                return True
        
        return False
    
    def post_comment(self, submission: Submission, content: str) -> bool:
        """Post a comment on a submission"""
        try:
            # Check if we already commented
            submission.comments.replace_more(limit=0)
            for comment in submission.comments:
                if comment.author and comment.author.name == self.config.reddit_username:
                    logger.info(f"Already commented on post {submission.id}")
                    return True
            
            # Post comment
            comment = submission.reply(content)
            logger.info(f"Posted comment on post {submission.id}: {submission.title}")
            
            # Rate limiting
            time.sleep(2)  # Be respectful to Reddit API
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to post comment on {submission.id}: {e}")
            return False
    
    def format_comment(self, article_content: str, article_url: str, article_title: str = "") -> str:
        """Format article content into a Reddit comment"""
        # Truncate content if too long
        if len(article_content) > self.config.max_article_length:
            article_content = article_content[:self.config.max_article_length] + "..."
        
        # Format using template
        formatted = self.config.comment_template.format(
            content=article_content,
            url=article_url,
            title=article_title
        )
        
        return formatted
    
    def validate_submission(self, submission: Submission) -> bool:
        """Validate if submission should be processed"""
        # Skip if too old (older than 1 hour)
        submission_age = time.time() - submission.created_utc
        if submission_age > 3600:  # 1 hour
            return False
        
        # Skip if deleted or removed
        if submission.removed_by_category or submission.author is None:
            return False
        
        # Skip if locked
        if submission.locked:
            return False
        
        return True
    
    def get_monitored_subreddits(self) -> List[str]:
        """Get list of subreddits to monitor"""
        return self.config.subreddits