import time
import logging
import signal
import sys
from typing import Optional
from config import Config
from reddit_client import RedditClient
from article_extractor import ArticleExtractor
from database import Database

logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = Config(config_path)
        self.config.validate()
        
        self.reddit_client = RedditClient(self.config)
        self.article_extractor = ArticleExtractor(self.config)
        self.database = Database(self.config)
        
        self.running = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """Start the bot"""
        logger.info("Starting CanillitaBot - Reddit Argentina News Bot")
        logger.info(f"Monitoring subreddits: {', '.join(self.config.subreddits)}")
        logger.info(f"Check interval: {self.config.check_interval} seconds")
        
        self.running = True
        
        try:
            while self.running:
                self._process_cycle()
                time.sleep(self.config.check_interval)
                
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            self._cleanup()
    
    def stop(self):
        """Stop the bot"""
        self.running = False
    
    def _process_cycle(self):
        """Process one cycle of checking subreddits"""
        logger.debug("Starting processing cycle")
        
        total_processed = 0
        total_successful = 0
        
        for subreddit_name in self.config.subreddits:
            try:
                processed, successful = self._process_subreddit(subreddit_name)
                total_processed += processed
                total_successful += successful
                
            except Exception as e:
                logger.error(f"Error processing subreddit r/{subreddit_name}: {e}")
        
        if total_processed > 0:
            logger.info(f"Cycle complete: {total_successful}/{total_processed} posts processed successfully")
        
        # Periodic cleanup
        if self._should_cleanup():
            self._periodic_cleanup()
    
    def _process_subreddit(self, subreddit_name: str) -> tuple[int, int]:
        """Process posts from a single subreddit"""
        logger.debug(f"Processing r/{subreddit_name}")
        
        processed_count = 0
        successful_count = 0
        
        try:
            posts = list(self.reddit_client.get_new_posts(
                subreddit_name, 
                limit=self.config.max_posts_per_check
            ))
            
            for submission in posts:
                try:
                    if self._process_submission(submission, subreddit_name):
                        successful_count += 1
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing submission {submission.id}: {e}")
                    processed_count += 1
            
        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit_name}: {e}")
        
        return processed_count, successful_count
    
    def _process_submission(self, submission, subreddit_name: str) -> bool:
        """Process a single submission"""
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
        
        # Check if it's a news article
        if not self.reddit_client.is_news_article(submission):
            logger.debug(f"Post {post_id} is not a news article, skipping")
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=False,
                error_message="Not a news article"
            )
            return False
        
        logger.info(f"Processing news article: {submission.title[:50]}...")
        
        # Extract article content
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
        
        # Format and post comment(s)
        formatted_comments = self.reddit_client.format_comment(
            article_content=article_data['content'],
            article_url=submission.url,
            article_title=article_data['title']
        )
        
        comment_success = self.reddit_client.post_comments(submission, formatted_comments)
        
        # Record the result
        self.database.record_processed_post(
            post_id=post_id,
            subreddit=subreddit_name,
            title=submission.title,
            url=submission.url,
            author=submission.author.name if submission.author else '[deleted]',
            created_utc=submission.created_utc,
            success=comment_success,
            error_message="Comment posting failed" if not comment_success else None,
            article_data=article_data
        )
        
        if comment_success:
            logger.info(f"Successfully processed and commented on post {post_id}")
        else:
            logger.warning(f"Article extracted but comment failed for post {post_id}")
        
        return comment_success
    
    def _should_cleanup(self) -> bool:
        """Check if periodic cleanup should run"""
        # Run cleanup once per hour (roughly)
        cycles_per_hour = 3600 // self.config.check_interval
        return hasattr(self, '_cycle_count') and self._cycle_count % cycles_per_hour == 0
    
    def _periodic_cleanup(self):
        """Run periodic maintenance tasks"""
        logger.info("Running periodic cleanup")
        
        try:
            # Clean up old database entries
            deleted_count = self.database.cleanup_old_entries()
            
            # Vacuum database occasionally
            if deleted_count > 100:
                self.database.vacuum_database()
            
            # Log statistics
            stats = self.database.get_processing_stats(days=1)
            if stats:
                logger.info(f"24h stats: {stats['successful']}/{stats['total_processed']} successful "
                          f"({stats['success_rate']:.1%} success rate)")
            
        except Exception as e:
            logger.error(f"Error during periodic cleanup: {e}")
    
    def _cleanup(self):
        """Cleanup resources on shutdown"""
        logger.info("Cleaning up resources")
        try:
            if hasattr(self, 'database'):
                self.database.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("CanillitaBot stopped")

def main():
    """Main entry point"""
    # Setup basic logging first
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize and start bot
        bot = BotManager()
        
        # Setup detailed logging based on config
        setup_logging(bot.config)
        
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)

def setup_logging(config: Config):
    """Setup detailed logging configuration"""
    # Create logs directory
    log_path = config.log_file
    log_dir = '/'.join(log_path.split('/')[:-1])
    if log_dir:
        import os
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format=config.log_format,
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )

if __name__ == "__main__":
    main()