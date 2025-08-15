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
        """Post a comment on a submission (backwards compatibility)"""
        return self.post_comments(submission, [content])
    
    def post_comments(self, submission: Submission, comments: list[str]) -> bool:
        """Post comment(s) on a submission, with replies for long articles"""
        try:
            # Check if we already commented
            submission.comments.replace_more(limit=0)
            for comment in submission.comments:
                if comment.author and comment.author.name == self.config.reddit_username:
                    logger.info(f"Already commented on post {submission.id}")
                    return True
            
            if not comments:
                logger.warning("No comments to post")
                return False
            
            # Post the main comment
            main_comment = submission.reply(comments[0])
            
            # Try to sticky/pin the comment (only works if bot is a moderator)
            try:
                main_comment.mod.distinguish(how='yes', sticky=True)
                logger.info(f"Posted and pinned main comment on post {submission.id}: {submission.title}")
            except Exception as pin_error:
                logger.debug(f"Could not pin comment (not a moderator): {pin_error}")
                logger.info(f"Posted main comment on post {submission.id}: {submission.title}")
            
            # Rate limiting after main comment
            time.sleep(2)
            
            # Post continuation comments as replies to the main comment
            for i, continuation_content in enumerate(comments[1:], 1):
                try:
                    reply = main_comment.reply(continuation_content)
                    logger.info(f"Posted continuation comment {i} on post {submission.id}")
                    
                    # Rate limiting between continuation comments
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Failed to post continuation comment {i} on {submission.id}: {e}")
                    # Continue with remaining parts even if one fails
            
            total_comments = len(comments)
            logger.info(f"Successfully posted {total_comments} comment(s) on post {submission.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post comments on {submission.id}: {e}")
            return False
    
    def format_comment(self, article_content: str, article_url: str, article_title: str = "") -> list[str]:
        """Format article content into Reddit comment(s), splitting if necessary"""
        # Format the main comment with title
        main_comment = self.config.comment_template.format(
            content="",  # We'll add content separately
            url=article_url,
            title=article_title
        )
        
        # Calculate how much space we have for content in the main comment
        main_comment_overhead = len(main_comment)
        available_space = self.config.max_comment_length - main_comment_overhead
        
        # Split content into chunks that fit
        comment_parts = self._split_content_for_comments(article_content, available_space)
        
        # Create the formatted comments
        formatted_comments = []
        
        for i, content_part in enumerate(comment_parts):
            if i == 0:
                # First comment includes the full template with title
                formatted = self.config.comment_template.format(
                    content=content_part,
                    url=article_url,
                    title=article_title
                )
            else:
                # Continuation comments use simpler template
                formatted = self.config.continuation_template.format(
                    content=content_part
                )
            
            formatted_comments.append(formatted)
        
        return formatted_comments
    
    def _split_content_for_comments(self, content: str, first_comment_space: int) -> list[str]:
        """Split content into chunks that fit in Reddit comments"""
        if not content:
            return [""]
        
        parts = []
        remaining_content = content
        
        # First chunk - fits in main comment with template overhead
        if len(remaining_content) <= first_comment_space:
            return [remaining_content]
        
        # Find good breaking point for first chunk
        first_chunk = remaining_content[:first_comment_space]
        break_point = self._find_good_break_point(first_chunk)
        
        if break_point > 0:
            first_chunk = remaining_content[:break_point]
            remaining_content = remaining_content[break_point:].lstrip()
        else:
            remaining_content = remaining_content[first_comment_space:].lstrip()
        
        parts.append(first_chunk)
        
        # Remaining chunks - fit in continuation comments
        continuation_space = self.config.max_comment_length - len(self.config.continuation_template.format(content=""))
        
        while remaining_content:
            if len(remaining_content) <= continuation_space:
                parts.append(remaining_content)
                break
            
            chunk = remaining_content[:continuation_space]
            break_point = self._find_good_break_point(chunk)
            
            if break_point > 0:
                chunk = remaining_content[:break_point]
                remaining_content = remaining_content[break_point:].lstrip()
            else:
                remaining_content = remaining_content[continuation_space:].lstrip()
            
            parts.append(chunk)
        
        return parts
    
    def _find_good_break_point(self, text: str) -> int:
        """Find a good place to break text (end of paragraph, sentence, etc.)"""
        # Prefer breaking at paragraph boundaries
        last_double_newline = text.rfind('\n\n')
        if last_double_newline > len(text) * 0.7:
            return last_double_newline + 2
        
        # Next preference: end of sentence
        sentence_endings = ['. ', '.\n', '! ', '!\n', '? ', '?\n']
        best_break = -1
        
        for ending in sentence_endings:
            pos = text.rfind(ending)
            if pos > len(text) * 0.7 and pos > best_break:
                best_break = pos + len(ending)
        
        if best_break > 0:
            return best_break
        
        # Fallback: break at word boundary
        last_space = text.rfind(' ')
        if last_space > len(text) * 0.8:
            return last_space + 1
        
        return -1  # No good break point found
    
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