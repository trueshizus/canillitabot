"""
Bot lifecycle management for CanillitaBot.
"""

import time
import logging
import signal
from core.bot import BotManager

logger = logging.getLogger(__name__)

class BotLifecycle:
    def __init__(self, bot_manager: BotManager):
        self.bot_manager = bot_manager
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
        logger.info(f"Monitoring subreddits: {', '.join(self.bot_manager.config.subreddits)}")
        logger.info(f"Check interval: {self.bot_manager.config.check_interval} seconds")
        
        # Start health server
        try:
            self.bot_manager.health_server.start()
            logger.info(f"Health check available at http://localhost:8080/health")
        except Exception as e:
            logger.warning(f"Could not start health server: {e}")
        
        self.running = True
        
        try:
            logger.info("Bot startup complete, entering main processing loop")
            while self.running:
                # Update health checker activity
                self.bot_manager.health_checker.update_activity()
                
                self.bot_manager.cycle.process_cycle()
                
                # Sleep with periodic wake-ups to check for shutdown
                self._interruptible_sleep(self.bot_manager.config.check_interval)
                
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            self.bot_manager.error_tracker.track_error(e, {'operation': 'main_loop'})
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
        self.bot_manager.health_checker.mark_shutdown()
        
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

    def _cleanup(self):
        """Cleanup resources on shutdown"""
        logger.info("Cleaning up resources...")
        
        cleanup_tasks = [
            ('health_server', lambda: self.bot_manager.health_server.stop() if self.bot_manager.health_server else None),
            ('database', lambda: self.bot_manager.database.close() if hasattr(self.bot_manager, 'database') else None),
            ('queue_manager', lambda: self.bot_manager.queue_manager.close() if hasattr(self.bot_manager, 'queue_manager') and self.bot_manager.queue_manager else None)
        ]
        
        for name, cleanup_func in cleanup_tasks:
            try:
                cleanup_func()
                logger.debug(f"✓ Cleaned up {name}")
            except Exception as e:
                logger.error(f"Error cleaning up {name}: {e}")
        
        logger.info("CanillitaBot shutdown complete")
