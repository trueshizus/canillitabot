"""
Content processing logic for the CanillitaBot.
"""

import logging
from typing import Dict, Any
from praw.models import Submission
from src.core.config import Config
from src.core.database import Database
from src.clients.reddit import RedditClient
from src.extractors.article import ArticleExtractor
from src.clients.gemini import GeminiClient
from src.extractors.x import XContentExtractor

logger = logging.getLogger(__name__)

class ContentProcessor:
    def __init__(self, config: Config, database: Database, reddit_client: RedditClient,
                 article_extractor: ArticleExtractor, gemini_client: GeminiClient,
                 x_extractor: XContentExtractor):
        self.config = config
        self.database = database
        self.reddit_client = reddit_client
        self.article_extractor = article_extractor
        self.gemini_client = gemini_client
        self.x_extractor = x_extractor

    def process_submission(self, submission: Submission, subreddit_name: str) -> bool:
        """Processes a single submission."""
        post_id = submission.id

        if not self.reddit_client.is_news_article(submission):
            if self.config.youtube_enabled and self.gemini_client and self.reddit_client.is_youtube_video(submission):
                logger.info(f"Processing YouTube video: {submission.title[:50]}...")
                return self._process_youtube_video(submission, subreddit_name)
            
            if self.config.x_twitter_enabled and self.x_extractor and self.reddit_client.is_x_twitter_post(submission):
                logger.info(f"Processing X/Twitter post: {submission.title[:50]}...")
                return self._process_x_twitter_post(submission, subreddit_name)
            
            logger.debug(f"Post {post_id} is not a news article, YouTube video, or X/Twitter post, skipping")
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=False,
                error_message="Not a news article, YouTube video, or X/Twitter post"
            )
            return False
        
        logger.info(f"Processing news article: {submission.title[:50]}...")
        
        article_data = self.article_extractor.extract_with_retry(submission.url)
        
        if not article_data:
            logger.warning(f"Failed to extract content from {submission.url}")
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=False,
                error_message="Article extraction failed"
            )
            return False
        
        formatted_comments = self.reddit_client.format_comment(
            article_content=article_data['content'],
            article_url=submission.url,
            article_title=article_data['title']
        )
        
        comment_success = self.reddit_client.post_comments(submission, formatted_comments)
        
        # Join multiple comments with separator for storage
        comment_content_for_db = "\n\n---\n\n".join(formatted_comments) if formatted_comments else None
        
        self.database.record_processed_post(
            post_id=post_id,
            subreddit=subreddit_name,
            title=submission.title,
            url=submission.url,
            author=submission.author.name if submission.author else '[deleted]',
            created_utc=submission.created_utc,
            success=comment_success,
            error_message="Comment posting failed" if not comment_success else None,
            article_data=article_data,
            comment_content=comment_content_for_db
        )
        
        if comment_success:
            logger.info(f"Successfully processed and commented on post {post_id}")
        else:
            logger.warning(f"Article extracted but comment failed for post {post_id}")
        
        return comment_success

    def _process_youtube_video(self, submission: Submission, subreddit_name: str) -> bool:
        """Processes a YouTube video submission."""
        post_id = submission.id
        
        try:
            video_data = self.gemini_client.summarize_youtube_video(submission.url)
            
            formatted_comment = self.config.youtube_summary_template.format(
                title=video_data['title'],
                summary=video_data['summary'],
                url=submission.url
            )
            
            comment_success = self.reddit_client.post_comment(submission, formatted_comment)
            
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=comment_success,
                error_message=None if comment_success else "Comment posting failed",
                comment_content=formatted_comment if comment_success else None
            )
            
            if comment_success:
                logger.info(f"Successfully processed and commented on YouTube video {post_id}")
            else:
                logger.warning(f"Video summarized but comment failed for post {post_id}")
            
            return comment_success
            
        except Exception as e:
            logger.error(f"Error processing YouTube video {post_id}: {e}")
            
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=False,
                error_message=f"YouTube processing failed: {str(e)}"
            )
            
            return False

    def _process_x_twitter_post(self, submission: Submission, subreddit_name: str) -> bool:
        """Processes an X/Twitter post submission."""
        post_id = submission.id
        
        try:
            tweet_data = self.x_extractor.extract_tweet_content(submission.url)
            
            if not tweet_data:
                logger.warning(f"Failed to extract X/Twitter content from {submission.url}")
                self.database.record_processed_post(
                    post_id=post_id,
                    subreddit=subreddit_name,
                    title=submission.title,
                    url=submission.url,
                    author=submission.author.name if submission.author else '[deleted]',
                    created_utc=submission.created_utc,
                    success=False,
                    error_message="X/Twitter content extraction failed"
                )
                return False
            
            media_note = ""
            if tweet_data.get('media_count', 0) > 0:
                media_note = f"📎 *Contiene {tweet_data['media_count']} archivo(s) multimedia*"
            
            formatted_comment = self.config.x_twitter_comment_template.format(
                author=tweet_data['author'],
                date=tweet_data['date'],
                text=tweet_data['text'],
                media_note=media_note,
                url=submission.url
            )
            
            comment_success = self.reddit_client.post_comment(submission, formatted_comment)
            
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=comment_success,
                error_message=None if comment_success else "Comment posting failed",
                comment_content=formatted_comment if comment_success else None
            )
            
            if comment_success:
                logger.info(f"Successfully processed and commented on X/Twitter post {post_id}")
            else:
                logger.warning(f"X/Twitter content extracted but comment failed for post {post_id}")
            
            return comment_success
            
        except Exception as e:
            logger.error(f"Error processing X/Twitter post {post_id}: {e}")
            
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=False,
                error_message=f"X/Twitter processing failed: {str(e)}"
            )
            
            return False
