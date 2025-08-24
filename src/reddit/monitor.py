import time
import logging
from typing import Iterator, List
from praw.models import Submission
from config import Config

logger = logging.getLogger(__name__)

class PostMonitor:
    """Handles monitoring and filtering of Reddit posts"""
    
    def __init__(self, config: Config, reddit):
        self.config = config
        self.reddit = reddit
    
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
