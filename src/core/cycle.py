"""
Processing cycle for the CanillitaBot.
"""

import logging
from core.bot import BotManager
from shared.utils import PerformanceLogger, metrics, error_tracker

logger = logging.getLogger(__name__)

class ProcessingCycle:
    def __init__(self, bot_manager: BotManager):
        self.bot_manager = bot_manager
        self.config = bot_manager.config
        self.reddit_client = bot_manager.reddit_client
        self.database = bot_manager.database
        self.queue_manager = bot_manager.queue_manager
        self.monitor = bot_manager.monitor
        self.submission_handler = bot_manager.submission_handler

    def process_cycle(self):
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
                    if self.submission_handler.process_submission(submission, subreddit_name):
                        successful_count += 1
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing submission {submission.id}: {e}")
                    processed_count += 1
            
        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit_name}: {e}")
        
        return processed_count, successful_count

    def _should_cleanup(self) -> bool:
        """Check if periodic cleanup should run"""
        # Run cleanup once per hour (roughly)
        cycles_per_hour = 3600 // self.config.check_interval
        return hasattr(self.bot_manager, '_cycle_count') and self.bot_manager._cycle_count % cycles_per_hour == 0

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
