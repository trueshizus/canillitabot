import logging
from src.core.config import Config
from src.clients.reddit import RedditClient
from src.extractors.article import ArticleExtractor
from src.core.database import Database
from src.clients.gemini import GeminiClient
from src.extractors.x import XContentExtractor
from src.shared.queue import QueueManager
from src.core.monitoring import initialize_monitoring
from src.services.health import HealthServer, HealthChecker
from src.core.processor import ContentProcessor
from src.core.lifecycle import BotLifecycle
from src.core.cycle import ProcessingCycle
from src.core.submission import SubmissionHandler

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
        
        # Initialize content processor
        self.processor = ContentProcessor(
            config=self.config,
            database=self.database,
            reddit_client=self.reddit_client,
            article_extractor=self.article_extractor,
            gemini_client=self.gemini_client,
            x_extractor=self.x_extractor
        )
        
        # Initialize submission handler
        self.submission_handler = SubmissionHandler(self)
        
        # Initialize processing cycle
        self.cycle = ProcessingCycle(self)
        
        # Initialize lifecycle manager
        self.lifecycle = BotLifecycle(self)

    def start(self):
        """Start the bot"""
        self.lifecycle.start()

    def stop(self):
        """Stop the bot"""
        self.lifecycle.stop()


def main():
    """Main entry point when running as module"""
    import logging
    from src.shared.utils import setup_logging
    
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
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot crashed: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()