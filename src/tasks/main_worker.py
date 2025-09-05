#!/usr/bin/env python3
"""
Redis Queue Worker for CanillitaBot
Processes queued jobs for article extraction, YouTube summarization, and Twitter content.
"""

import sys
import os

# Add the project root to Python path to enable imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
import signal
import time
from typing import List
from rq import Worker, Connection
import redis
from src.core.config import Config
from src.shared.utils import setup_logging

logger = logging.getLogger(__name__)

class CanillitaWorker:
    """Worker manager for processing CanillitaBot queues"""
    
    def __init__(self, queues: List[str] = None):
        self.config = Config()
        
        # Setup logging
        setup_logging(self.config)
        
        # Connect to Redis
        self.redis_conn = self._connect_redis()
        
        # Default queues to process
        self.queue_names = queues or ['posts', 'articles', 'youtube', 'twitter', 'retry']
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info(f"Worker initialized for queues: {', '.join(self.queue_names)}")
    
    def _connect_redis(self):
        """Connect to Redis server with retry logic"""
        redis_url = self.config.queue.redis_url
        
        for attempt in range(5):
            try:
                conn = redis.from_url(redis_url)
                conn.ping()  # Test connection
                logger.info(f"Connected to Redis at {redis_url}")
                return conn
            except redis.exceptions.ConnectionError as e:
                logger.warning(f"Redis connection failed (attempt {attempt + 1}/5): {e}")
                if attempt < 4:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error("Failed to connect to Redis after multiple attempts.")
        sys.exit(1)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down worker...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self):
        """Start the worker to process jobs"""
        try:
            with Connection(self.redis_conn):
                worker = Worker(
                    self.queue_names,
                    connection=self.redis_conn,
                    name=f"canillita-worker-{os.getpid()}"
                )
                
                logger.info("Worker started. Waiting for jobs...")
                worker.work(with_scheduler=True)
                
        except Exception as e:
            logger.error(f"Worker error: {e}")
            sys.exit(1)

def main():
    """Main entry point for worker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CanillitaBot Queue Worker')
    parser.add_argument(
        '--queues', 
        nargs='+',
        default=['posts', 'articles', 'youtube', 'twitter', 'retry'],
        help='Queues to process (default: all)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Start worker
    worker = CanillitaWorker(queues=args.queues)
    worker.run()

if __name__ == "__main__":
    main()