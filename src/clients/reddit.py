import logging
from typing import Iterator, List, Dict
from praw.models import Submission
from core.config import Config
from clients.internal import RedditConnection, PostMonitor, CommentManager, CommentAnalytics

logger = logging.getLogger(__name__)

class RedditClient:
    """
    Main Reddit client that composes different Reddit functionalities.
    
    This class serves as a facade for the various Reddit operations,
    providing a unified interface while delegating to specialized components.
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize connection component
        self.connection = RedditConnection(config)
        reddit = self.connection.get_reddit_instance()
        
        # Initialize other components with the Reddit instance
        self.monitor = PostMonitor(config, reddit)
        self.comments = CommentManager(config, reddit)
        self.analytics = CommentAnalytics(config, reddit)
    
    # Delegation methods for connection functionality
    @property
    def reddit(self):
        """Get the Reddit API instance (for backwards compatibility)"""
        return self.connection.get_reddit_instance()
    
    # Delegation methods for post monitoring
    def get_new_posts(self, subreddit_name: str, limit: int = 10) -> Iterator[Submission]:
        """Get new posts from a subreddit"""
        return self.monitor.get_new_posts(subreddit_name, limit)
    
    def is_news_article(self, submission: Submission) -> bool:
        """Check if submission contains a news article link"""
        return self.monitor.is_news_article(submission)
    
    def is_youtube_video(self, submission: Submission) -> bool:
        """Check if submission contains a YouTube video link"""
        return self.monitor.is_youtube_video(submission)
    
    def is_x_twitter_post(self, submission: Submission) -> bool:
        """Check if submission contains an X/Twitter post link"""
        return self.monitor.is_x_twitter_post(submission)
    
    def validate_submission(self, submission: Submission) -> bool:
        """Validate if submission should be processed"""
        return self.monitor.validate_submission(submission)
    
    def get_monitored_subreddits(self) -> List[str]:
        """Get list of subreddits to monitor"""
        return self.monitor.get_monitored_subreddits()
    
    def get_submission_by_id(self, submission_id: str) -> Submission:
        """Get a submission by its ID"""
        return self.monitor.get_submission_by_id(submission_id)
    
    # Delegation methods for comment management
    def post_comment(self, submission: Submission, content: str) -> bool:
        """Post a comment on a submission (backwards compatibility)"""
        return self.comments.post_comment(submission, content)
    
    def post_comments(self, submission: Submission, comments: List[str]) -> bool:
        """Post comment(s) on a submission, with replies for long articles"""
        return self.comments.post_comments(submission, comments)
    
    def format_comment(self, article_content: str, article_url: str, article_title: str = "") -> List[str]:
        """Format article content into Reddit comment(s), splitting if necessary"""
        return self.comments.format_comment(article_content, article_url, article_title)
    
    # Delegation methods for analytics
    def get_bot_comments(self, limit: int = 25, subreddit: str = None) -> List[Dict]:
        """Get recent comments made by the bot"""
        return self.analytics.get_bot_comments(limit, subreddit)
    
    def get_bot_comment_stats(self, days: int = 7) -> Dict:
        """Get statistics about bot comments in the last N days"""
        return self.analytics.get_bot_comment_stats(days)
    
    def check_comment_replies(self, comment_id: str) -> List[Dict]:
        """Check replies to a specific bot comment"""
        return self.analytics.check_comment_replies(comment_id)
    
    # URL checking methods for queue workers
    def is_news_article_url(self, url: str) -> bool:
        """Check if URL is a news article (for queue workers)"""
        return self.monitor.is_news_article_url(url)
    
    def is_youtube_video_url(self, url: str) -> bool:
        """Check if URL is a YouTube video (for queue workers)"""
        return self.monitor.is_youtube_video_url(url)
    
    def is_x_twitter_post_url(self, url: str) -> bool:
        """Check if URL is an X/Twitter post (for queue workers)"""
        return self.monitor.is_x_twitter_post_url(url)