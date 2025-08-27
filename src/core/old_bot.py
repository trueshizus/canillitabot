import time
import logging
import signal
from core.config import Config
from clients.reddit import RedditClient
from extractors.article import ArticleExtractor
from core.database import Database
from clients.gemini import GeminiClient
from extractors.x import XContentExtractor
from shared.queue import QueueManager
from core.monitoring import initialize_monitoring
from shared.utils import PerformanceLogger, metrics, error_tracker
from services.health import HealthServer, HealthChecker

logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = Config(config_path)
        self.config.validate()
        
        self.reddit_client = RedditClient(self.config)
        self.article_extractor = ArticleExtractor(self.config)
        self.database = Database(self.config)
        
        # Initialize Gemini client if YouTube is enabled
        self.gemini_client = None
        if self.config.youtube_enabled:
            try:
                self.gemini_client = GeminiClient()
                logger.info("Gemini client initialized for YouTube processing")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                logger.info("YouTube processing will be disabled")
        
        # Initialize X/Twitter extractor if enabled
        self.x_extractor = None
        if self.config.x_twitter_enabled:
            try:
                self.x_extractor = XContentExtractor()
                logger.info("X/Twitter extractor initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize X/Twitter extractor: {e}")
                logger.info("X/Twitter processing will be disabled")
        
        # Initialize queue manager if enabled
        self.queue_manager = None
        if getattr(self.config, 'queue_enabled', False):
            try:
                self.queue_manager = QueueManager(self.config)
                if self.queue_manager.is_available():
                    logger.info("Queue system initialized - posts will be processed asynchronously")
                else:
                    logger.warning("Queue system not available - falling back to direct processing")
                    self.queue_manager = None
            except Exception as e:
                logger.warning(f"Failed to initialize queue system: {e}")
                logger.info("Falling back to direct processing")
                self.queue_manager = None
        
        # Initialize monitoring system
        self.monitor = initialize_monitoring(self.config)
        
        # Initialize health checking
        self.health_checker = HealthChecker(bot_manager=self, database=self.database)
        self.health_server = HealthServer(port=8080, health_checker=self.health_checker)
        
        self.running = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum} ({'SIGINT' if signum == 2 else 'SIGTERM'}), initiating graceful shutdown...")
            self.shutdown_gracefully()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """Start the bot"""
        logger.info("Starting CanillitaBot - Reddit Argentina News Bot")
        logger.info(f"Monitoring subreddits: {', '.join(self.config.subreddits)}")
        logger.info(f"Check interval: {self.config.check_interval} seconds")
        
        # Start health server
        try:
            self.health_server.start()
            logger.info(f"Health check available at http://localhost:8080/health")
        except Exception as e:
            logger.warning(f"Could not start health server: {e}")
        
        self.running = True
        
        try:
            logger.info("Bot startup complete, entering main processing loop")
            while self.running:
                # Update health checker activity
                self.health_checker.update_activity()
                
                self._process_cycle()
                
                # Sleep with periodic wake-ups to check for shutdown
                self._interruptible_sleep(self.config.check_interval)
                
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            error_tracker.track_error(e, {'operation': 'main_loop'})
            raise
        finally:
            self._cleanup()
    
    def stop(self):
        """Stop the bot immediately"""
        self.running = False
    
    def shutdown_gracefully(self):
        """Gracefully shutdown the bot with proper cleanup"""
        logger.info("Initiating graceful shutdown...")
        
        # Mark health checker as shutting down
        self.health_checker.mark_shutdown()
        
        # Stop accepting new work
        self.running = False
        
        # Allow current cycle to complete naturally
        logger.info("Waiting for current processing cycle to complete...")
    
    def _interruptible_sleep(self, duration: int):
        """Sleep that can be interrupted for faster shutdown"""
        sleep_interval = min(1, duration)  # Sleep in 1-second intervals
        total_slept = 0
        
        while total_slept < duration and self.running:
            time.sleep(sleep_interval)
            total_slept += sleep_interval
    
    def _process_cycle(self):
        """Process one cycle of checking subreddits"""
        with PerformanceLogger("processing_cycle", logger):
            logger.debug("Starting processing cycle")
            
            total_processed = 0
            total_successful = 0
            
            for subreddit_name in self.config.subreddits:
                try:
                    with PerformanceLogger(f"process_subreddit_{subreddit_name}", logger):
                        processed, successful = self._process_subreddit(subreddit_name)
                        total_processed += processed
                        total_successful += successful
                    
                except Exception as e:
                    logger.error(f"Error processing subreddit r/{subreddit_name}: {e}")
                    error_tracker.track_error(e, {'subreddit': subreddit_name, 'operation': 'process_subreddit'})
            
            if total_processed > 0:
                logger.info(f"Cycle complete: {total_successful}/{total_processed} posts processed successfully")
                metrics.gauge('cycle_posts_processed', total_processed)
                metrics.gauge('cycle_success_rate', total_successful / total_processed)
            
            # Update queue metrics if available
            if self.queue_manager and self.queue_manager.is_available():
                try:
                    queue_stats = self.queue_manager.get_queue_stats()
                    self.monitor.update_queue_status(queue_stats)
                except Exception as e:
                    logger.debug(f"Could not update queue metrics: {e}")
            
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
            return self._process_submission_direct(submission, subreddit_name)
    
    def _enqueue_submission(self, submission, subreddit_name: str) -> bool:
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
                return self._process_submission_direct(submission, subreddit_name)
                
        except Exception as e:
            logger.error(f"Error enqueuing submission {submission.id}: {e}")
            error_tracker.track_error(e, {
                'operation': 'enqueue_submission',
                'post_id': submission.id,
                'subreddit': subreddit_name
            })
            logger.info("Falling back to direct processing")
            return self._process_submission_direct(submission, subreddit_name)
    
    def _determine_content_type(self, submission) -> str:
        """Determine the content type of a submission"""
        if self.reddit_client.is_news_article(submission):
            return 'article'
        elif self.reddit_client.is_youtube_video(submission):
            return 'youtube'
        elif self.reddit_client.is_x_twitter_post(submission):
            return 'twitter'
        else:
            return 'unknown'
    
    def _process_submission_direct(self, submission, subreddit_name: str) -> bool:
        """Process a submission directly (without queue)"""
        post_id = submission.id
        
        # Check if it's a news article
        if not self.reddit_client.is_news_article(submission):
            # Check if it's a YouTube video (if enabled)
            if self.config.youtube_enabled and self.gemini_client and self.reddit_client.is_youtube_video(submission):
                logger.info(f"Processing YouTube video: {submission.title[:50]}...")
                return self._process_youtube_video(submission, subreddit_name)
            
            # Check if it's an X/Twitter post (if enabled)
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
    
    def _process_youtube_video(self, submission, subreddit_name: str) -> bool:
        """Process a YouTube video submission"""
        post_id = submission.id
        
        try:
            # Generate video summary and get title using Gemini
            video_data = self.gemini_client.summarize_youtube_video(submission.url)
            
            # Format comment using YouTube template with actual video title
            formatted_comment = self.config.youtube_summary_template.format(
                title=video_data['title'],
                summary=video_data['summary'],
                url=submission.url
            )
            
            # Post comment
            comment_success = self.reddit_client.post_comment(submission, formatted_comment)
            
            # Record in database
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=comment_success,
                error_message=None if comment_success else "Comment posting failed"
            )
            
            if comment_success:
                logger.info(f"Successfully processed and commented on YouTube video {post_id}")
            else:
                logger.warning(f"Video summarized but comment failed for post {post_id}")
            
            return comment_success
            
        except Exception as e:
            logger.error(f"Error processing YouTube video {post_id}: {e}")
            
            # Record failure in database
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
    
    def _process_x_twitter_post(self, submission, subreddit_name: str) -> bool:
        """Process an X/Twitter post submission"""
        post_id = submission.id
        
        try:
            # Extract tweet content
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
            
            # Prepare media note
            media_note = ""
            if tweet_data.get('media_count', 0) > 0:
                media_note = f"📎 *Contiene {tweet_data['media_count']} archivo(s) multimedia*"
            
            # Format comment using X/Twitter template
            formatted_comment = self.config.x_twitter_comment_template.format(
                author=tweet_data['author'],
                date=tweet_data['date'],
                text=tweet_data['text'],
                media_note=media_note,
                url=submission.url
            )
            
            # Post comment
            comment_success = self.reddit_client.post_comment(submission, formatted_comment)
            
            # Record in database
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=comment_success,
                error_message=None if comment_success else "Comment posting failed"
            )
            
            if comment_success:
                logger.info(f"Successfully processed and commented on X/Twitter post {post_id}")
            else:
                logger.warning(f"X/Twitter content extracted but comment failed for post {post_id}")
            
            return comment_success
            
        except Exception as e:
            logger.error(f"Error processing X/Twitter post {post_id}: {e}")
            
            # Record failure in database
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
            
            # Perform health check
            health_status = self.monitor.perform_health_check()
            
            # Log operational metrics summary
            metrics_summary = self.monitor.operational_metrics.get_summary()
            logger.info(
                "Operational metrics summary",
                extra={'extra_data': {
                    'uptime_hours': metrics_summary['uptime_hours'],
                    'posts_processed_success': metrics_summary['posts_processed_success'],
                    'posts_processed_failed': metrics_summary['posts_processed_failed'],
                    'success_rate': metrics_summary['success_rate'],
                    'avg_processing_time': metrics_summary['avg_processing_time_seconds'],
                    'health_status': health_status['overall_status']
                }}
            )
            
        except Exception as e:
            logger.error(f"Error during periodic cleanup: {e}")
            error_tracker.track_error(e, {'operation': 'periodic_cleanup'})
    
    def _cleanup(self):
        """Cleanup resources on shutdown"""
        logger.info("Cleaning up resources...")
        
        cleanup_tasks = [
            ('health_server', lambda: self.health_server.stop() if self.health_server else None),
            ('database', lambda: self.database.close() if hasattr(self, 'database') else None),
            ('queue_manager', lambda: self.queue_manager.close() if hasattr(self, 'queue_manager') and self.queue_manager else None)
        ]
        
        for name, cleanup_func in cleanup_tasks:
            try:
                cleanup_func()
                logger.debug(f"✓ Cleaned up {name}")
            except Exception as e:
                logger.error(f"Error cleaning up {name}: {e}")
        
        logger.info("CanillitaBot shutdown complete")