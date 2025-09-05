"""
Queue workers for processing Reddit posts, articles, and media content.
These workers run in separate processes and handle the actual content processing.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json

# Add src directory to Python path for worker processes
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from src.core.config import Config
from src.core.database import Database
from src.clients.reddit import RedditClient
from src.extractors.article import ArticleExtractor
from src.clients.gemini import GeminiClient
from src.extractors.x import XContentExtractor

# Initialize shared components
config = Config()
database = Database(config)
reddit_client = RedditClient(config)
article_extractor = ArticleExtractor(config)

# Initialize optional components
gemini_client = None
if config.youtube_enabled:
    try:
        gemini_client = GeminiClient()
    except Exception as e:
        logging.warning(f"Failed to initialize Gemini client in worker: {e}")

x_extractor = None
if config.x_twitter_enabled:
    try:
        x_extractor = XContentExtractor()
    except Exception as e:
        logging.warning(f"Failed to initialize X extractor in worker: {e}")

logger = logging.getLogger(__name__)

def process_discovered_post(subreddit: str, submission_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a discovered Reddit post and determine how to handle it.
    This is the first stage of processing that routes posts to appropriate handlers.
    """
    try:
        post_id = submission_data['id']
        url = submission_data.get('url', '')
        title = submission_data.get('title', '')
        
        logger.info(f"Processing discovered post {post_id}: {title[:50]}...")
        
        # Check if already processed
        if database.is_post_processed(post_id):
            logger.debug(f"Post {post_id} already processed, skipping")
            return {"status": "skipped", "reason": "already_processed"}
        
        # Determine content type and route accordingly
        # The URL in submission_data might have been extracted from a self-post
        if reddit_client.is_news_article_url(url):
            # Route to article processing queue
            from src.shared.queue import QueueManager
            queue_manager = QueueManager(config)
            job_id = queue_manager.enqueue_article_processing(post_id, url, submission_data)
            
            return {
                "status": "routed",
                "content_type": "article",
                "job_id": job_id,
                "url": url
            }
        
        elif config.youtube_enabled and reddit_client.is_youtube_video_url(url):
            # Route to YouTube processing queue
            from src.shared.queue import QueueManager
            queue_manager = QueueManager(config)
            job_id = queue_manager.enqueue_youtube_processing(post_id, url, submission_data)
            
            return {
                "status": "routed",
                "content_type": "youtube",
                "job_id": job_id,
                "url": url
            }
        
        elif config.x_twitter_enabled and reddit_client.is_x_twitter_post_url(url):
            # Route to Twitter processing queue
            from src.shared.queue import QueueManager
            queue_manager = QueueManager(config)
            job_id = queue_manager.enqueue_twitter_processing(post_id, url, submission_data)
            
            return {
                "status": "routed",
                "content_type": "twitter",
                "job_id": job_id,
                "url": url
            }
        
        else:
            # Not a supported content type, record and skip
            database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit,
                title=title,
                url=url,
                author=submission_data.get('author', '[deleted]'),
                created_utc=submission_data.get('created_utc', 0),
                success=False,
                error_message="Unsupported content type"
            )
            
            return {
                "status": "skipped",
                "reason": "unsupported_content_type",
                "url": url
            }
    
    except Exception as e:
        logger.error(f"Error processing discovered post {submission_data.get('id', 'unknown')}: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def process_article(post_id: str, url: str, submission_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a news article: extract content and post Reddit comment"""
    try:
        logger.info(f"Processing article {post_id}: {url}")
        
        # Extract article content
        article_data = article_extractor.extract_with_retry(url)
        
        if not article_data:
            # Record failure
            database.record_processed_post(
                post_id=post_id,
                subreddit=submission_data.get('subreddit', ''),
                title=submission_data.get('title', ''),
                url=url,
                author=submission_data.get('author', '[deleted]'),
                created_utc=submission_data.get('created_utc', 0),
                success=False,
                error_message="Article extraction failed"
            )
            
            return {
                "status": "failed",
                "error": "Article extraction failed"
            }
        
        # Create Reddit submission object (needed for commenting)
        try:
            submission = reddit_client.reddit.submission(id=post_id)
            
            # Format and post comment(s)
            formatted_comments = reddit_client.format_comment(
                article_content=article_data['content'],
                article_url=url,
                article_title=article_data['title']
            )
            
            comment_success = reddit_client.post_comments(submission, formatted_comments)
            
            # Join multiple comments with separator for storage
            comment_content_for_db = "\n\n---\n\n".join(formatted_comments) if formatted_comments else None
            
            # Record the result
            database.record_processed_post(
                post_id=post_id,
                subreddit=submission_data.get('subreddit', ''),
                title=submission_data.get('title', ''),
                url=url,
                author=submission_data.get('author', '[deleted]'),
                created_utc=submission_data.get('created_utc', 0),
                success=comment_success,
                error_message="Comment posting failed" if not comment_success else None,
                article_data=article_data,
                comment_content=comment_content_for_db
            )
            
            if comment_success:
                logger.info(f"Successfully processed article {post_id}")
                return {
                    "status": "success",
                    "article_title": article_data['title'],
                    "content_length": len(article_data['content'])
                }
            else:
                logger.warning(f"Article extracted but comment failed for {post_id}")
                return {
                    "status": "partial_success",
                    "error": "Comment posting failed"
                }
        
        except Exception as e:
            logger.error(f"Error posting comment for article {post_id}: {e}")
            
            # Still record the processing attempt
            database.record_processed_post(
                post_id=post_id,
                subreddit=submission_data.get('subreddit', ''),
                title=submission_data.get('title', ''),
                url=url,
                author=submission_data.get('author', '[deleted]'),
                created_utc=submission_data.get('created_utc', 0),
                success=False,
                error_message=f"Comment posting error: {str(e)}",
                article_data=article_data
            )
            
            return {
                "status": "failed",
                "error": f"Comment posting error: {str(e)}"
            }
    
    except Exception as e:
        logger.error(f"Error processing article {post_id}: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def process_youtube_video(post_id: str, url: str, submission_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a YouTube video: extract transcript, summarize, and post comment"""
    try:
        if not gemini_client:
            return {
                "status": "failed",
                "error": "Gemini client not available"
            }
        
        logger.info(f"Processing YouTube video {post_id}: {url}")
        
        # Generate video summary
        video_data = gemini_client.summarize_youtube_video(url)
        
        # Create Reddit submission object
        submission = reddit_client.reddit.submission(id=post_id)
        
        # Format comment using YouTube template
        formatted_comment = config.youtube_summary_template.format(
            title=video_data['title'],
            summary=video_data['summary'],
            url=url
        )
        
        # Post comment
        comment_success = reddit_client.post_comment(submission, formatted_comment)
        
        # Record in database
        database.record_processed_post(
            post_id=post_id,
            subreddit=submission_data.get('subreddit', ''),
            title=submission_data.get('title', ''),
            url=url,
            author=submission_data.get('author', '[deleted]'),
            created_utc=submission_data.get('created_utc', 0),
            success=comment_success,
            error_message=None if comment_success else "Comment posting failed",
            comment_content=formatted_comment if comment_success else None
        )
        
        if comment_success:
            logger.info(f"Successfully processed YouTube video {post_id}")
            return {
                "status": "success",
                "video_title": video_data['title']
            }
        else:
            return {
                "status": "partial_success",
                "error": "Comment posting failed"
            }
    
    except Exception as e:
        logger.error(f"Error processing YouTube video {post_id}: {e}")
        
        # Record failure
        database.record_processed_post(
            post_id=post_id,
            subreddit=submission_data.get('subreddit', ''),
            title=submission_data.get('title', ''),
            url=url,
            author=submission_data.get('author', '[deleted]'),
            created_utc=submission_data.get('created_utc', 0),
            success=False,
            error_message=f"YouTube processing failed: {str(e)}"
        )
        
        return {
            "status": "error",
            "error": str(e)
        }

def process_twitter_post(post_id: str, url: str, submission_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a Twitter/X post: extract content and post comment"""
    try:
        if not x_extractor:
            return {
                "status": "failed",
                "error": "X extractor not available"
            }
        
        logger.info(f"Processing Twitter post {post_id}: {url}")
        
        # Extract tweet content
        tweet_data = x_extractor.extract_tweet_content(url)
        
        if not tweet_data:
            # Record failure
            database.record_processed_post(
                post_id=post_id,
                subreddit=submission_data.get('subreddit', ''),
                title=submission_data.get('title', ''),
                url=url,
                author=submission_data.get('author', '[deleted]'),
                created_utc=submission_data.get('created_utc', 0),
                success=False,
                error_message="X/Twitter content extraction failed"
            )
            
            return {
                "status": "failed",
                "error": "Twitter content extraction failed"
            }
        
        # Create Reddit submission object
        submission = reddit_client.reddit.submission(id=post_id)
        
        # Prepare media note
        media_note = ""
        if tweet_data.get('media_count', 0) > 0:
            media_note = f"📎 *Contiene {tweet_data['media_count']} archivo(s) multimedia*"
        
        # Format comment using X/Twitter template
        formatted_comment = config.x_twitter_comment_template.format(
            author=tweet_data['author'],
            date=tweet_data['date'],
            text=tweet_data['text'],
            media_note=media_note,
            url=url
        )
        
        # Post comment
        comment_success = reddit_client.post_comment(submission, formatted_comment)
        
        # Record in database
        database.record_processed_post(
            post_id=post_id,
            subreddit=submission_data.get('subreddit', ''),
            title=submission_data.get('title', ''),
            url=url,
            author=submission_data.get('author', '[deleted]'),
            created_utc=submission_data.get('created_utc', 0),
            success=comment_success,
            error_message=None if comment_success else "Comment posting failed",
            comment_content=formatted_comment if comment_success else None
        )
        
        if comment_success:
            logger.info(f"Successfully processed Twitter post {post_id}")
            return {
                "status": "success",
                "author": tweet_data['author']
            }
        else:
            return {
                "status": "partial_success",
                "error": "Comment posting failed"
            }
    
    except Exception as e:
        logger.error(f"Error processing Twitter post {post_id}: {e}")
        
        # Record failure
        database.record_processed_post(
            post_id=post_id,
            subreddit=submission_data.get('subreddit', ''),
            title=submission_data.get('title', ''),
            url=url,
            author=submission_data.get('author', '[deleted]'),
            created_utc=submission_data.get('created_utc', 0),
            success=False,
            error_message=f"X/Twitter processing failed: {str(e)}"
        )
        
        return {
            "status": "error",
            "error": str(e)
        }

def retry_failed_job(original_job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Retry a failed job with the original parameters"""
    try:
        job_type = original_job_data.get('job_type')
        
        if job_type == 'article':
            return process_article(
                original_job_data['post_id'],
                original_job_data['url'],
                original_job_data['submission_data']
            )
        elif job_type == 'youtube':
            return process_youtube_video(
                original_job_data['post_id'],
                original_job_data['url'],
                original_job_data['submission_data']
            )
        elif job_type == 'twitter':
            return process_twitter_post(
                original_job_data['post_id'],
                original_job_data['url'],
                original_job_data['submission_data']
            )
        else:
            return {
                "status": "error",
                "error": f"Unknown job type for retry: {job_type}"
            }
    
    except Exception as e:
        logger.error(f"Error retrying job: {e}")
        return {
            "status": "error",
            "error": str(e)
        }