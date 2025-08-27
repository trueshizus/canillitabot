"""
Submission handling for the CanillitaBot.
"""

import logging
from praw.models import Submission
from core.bot import BotManager
from shared.utils import error_tracker

logger = logging.getLogger(__name__)

class SubmissionHandler:
    def __init__(self, bot_manager: BotManager):
        self.bot_manager = bot_manager
        self.config = bot_manager.config
        self.database = bot_manager.database
        self.reddit_client = bot_manager.reddit_client
        self.queue_manager = bot_manager.queue_manager
        self.processor = bot_manager.processor
        self.monitor = bot_manager.monitor

    def process_submission(self, submission: Submission, subreddit_name: str) -> bool:
        """Process a single submission - either queue it or process directly"""
        post_id = submission.id
        
        # Skip if already processed
        if self.database.is_post_processed(post_id):
            logger.debug(f"Post {post_id} already processed, skipping")
            return True
        
        # Validate submission
        if not self.reddit_client.validate_submission(submission):
            logger.debug(f"Post {post_id} failed validation, skipping")
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=getattr(submission, 'url', ''),
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=False,
                error_message="Failed validation"
            )
            return False
        
        # If queue system is available, enqueue the post for processing
        if self.queue_manager and self.queue_manager.is_available():
            return self._enqueue_submission(submission, subreddit_name)
        else:
            # Fall back to direct processing
            return self.processor.process_submission(submission, subreddit_name)

    def _enqueue_submission(self, submission: Submission, subreddit_name: str) -> bool:
        """Enqueue a submission for asynchronous processing"""
        try:
            submission_data = {
                'id': submission.id,
                'title': submission.title,
                'url': submission.url,
                'subreddit': subreddit_name,
                'author': submission.author.name if submission.author else '[deleted]',
                'created_utc': submission.created_utc
            }
            
            # Record post discovery
            content_type = self._determine_content_type(submission)
            self.monitor.operational_metrics.record_post_discovered(subreddit_name, content_type)
            
            job_id = self.queue_manager.enqueue_post_discovery(subreddit_name, submission_data)
            
            if job_id:
                logger.debug(f"Enqueued post {submission.id} for processing (job: {job_id})")
                return True
            else:
                logger.warning(f"Failed to enqueue post {submission.id}, falling back to direct processing")
                return self.processor.process_submission(submission, subreddit_name)
                
        except Exception as e:
            logger.error(f"Error enqueuing submission {submission.id}: {e}")
            error_tracker.track_error(e, {
                'operation': 'enqueue_submission',
                'post_id': submission.id,
                'subreddit': subreddit_name
            })
            logger.info("Falling back to direct processing")
            return self.processor.process_submission(submission, subreddit_name)

    def _determine_content_type(self, submission: Submission) -> str:
        """Determine the content type of a submission"""
        if self.reddit_client.is_news_article(submission):
            return 'article'
        elif self.reddit_client.is_youtube_video(submission):
            return 'youtube'
        elif self.reddit_client.is_x_twitter_post(submission):
            return 'twitter'
        else:
            return 'unknown'
