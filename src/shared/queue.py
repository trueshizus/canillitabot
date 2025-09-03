import logging
import redis
from rq import Queue, Worker, Connection
from rq.job import Retry
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from src.core.config import Config

logger = logging.getLogger(__name__)

class QueueManager:
    """Manages Redis-based task queues for decoupled post processing"""
    
    def __init__(self, config: Config):
        self.config = config
        self.redis_conn = None
        self.queues = {}
        self._connect()
    
    def _connect(self):
        """Connect to Redis server"""
        try:
            redis_url = self.config.queue.redis_url
            self.redis_conn = redis.from_url(redis_url)
            
            # Test connection
            self.redis_conn.ping()
            
            # Initialize queues
            self.queues = {
                'posts': Queue('posts', connection=self.redis_conn),
                'articles': Queue('articles', connection=self.redis_conn),
                'youtube': Queue('youtube', connection=self.redis_conn),
                'twitter': Queue('twitter', connection=self.redis_conn),
                'retry': Queue('retry', connection=self.redis_conn)
            }
            
            logger.info("Connected to Redis and initialized queues")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Fall back to in-memory processing
            self.redis_conn = None
            self.queues = {}
    
    def is_available(self) -> bool:
        """Check if Redis queue system is available"""
        return self.redis_conn is not None and len(self.queues) > 0
    
    def enqueue_post_discovery(self, subreddit: str, submission_data: Dict[str, Any]) -> Optional[str]:
        """Enqueue a discovered post for processing"""
        if not self.is_available():
            return None
        
        try:
            job = self.queues['posts'].enqueue(
                'queue_handlers.process_discovered_post',
                subreddit,
                submission_data,
                job_timeout='5m',
                retry=Retry(max=3, interval=[10, 30, 60])
            )
            
            logger.debug(f"Enqueued post {submission_data.get('id')} for processing")
            return job.id
            
        except Exception as e:
            logger.error(f"Failed to enqueue post: {e}")
            return None
    
    def enqueue_article_processing(self, post_id: str, url: str, submission_data: Dict[str, Any]) -> Optional[str]:
        """Enqueue article extraction and processing"""
        if not self.is_available():
            return None
        
        try:
            job = self.queues['articles'].enqueue(
                'queue_handlers.process_article',
                post_id,
                url,
                submission_data,
                job_timeout='10m',
                retry=Retry(max=3, interval=[60, 180, 360])
            )
            
            logger.debug(f"Enqueued article processing for {url}")
            return job.id
            
        except Exception as e:
            logger.error(f"Failed to enqueue article processing: {e}")
            return None
    
    def enqueue_youtube_processing(self, post_id: str, url: str, submission_data: Dict[str, Any]) -> Optional[str]:
        """Enqueue YouTube video processing"""
        if not self.is_available():
            return None
        
        try:
            job = self.queues['youtube'].enqueue(
                'queue_handlers.process_youtube_video',
                post_id,
                url,
                submission_data,
                job_timeout='15m',
                retry=Retry(max=2, interval=[180, 600])
            )
            
            logger.debug(f"Enqueued YouTube processing for {url}")
            return job.id
            
        except Exception as e:
            logger.error(f"Failed to enqueue YouTube processing: {e}")
            return None
    
    def enqueue_twitter_processing(self, post_id: str, url: str, submission_data: Dict[str, Any]) -> Optional[str]:
        """Enqueue Twitter/X post processing"""
        if not self.is_available():
            return None
        
        try:
            job = self.queues['twitter'].enqueue(
                'queue_handlers.process_twitter_post',
                post_id,
                url,
                submission_data,
                job_timeout='5m',
                retry=Retry(max=3, interval=[10, 30, 60])
            )
            
            logger.debug(f"Enqueued Twitter processing for {url}")
            return job.id
            
        except Exception as e:
            logger.error(f"Failed to enqueue Twitter processing: {e}")
            return None
    
    def enqueue_retry(self, original_job_data: Dict[str, Any], delay_seconds: int = 300) -> Optional[str]:
        """Enqueue a failed job for retry with exponential backoff"""
        if not self.is_available():
            return None
        
        try:
            job = self.queues['retry'].enqueue_in(
                timedelta(seconds=delay_seconds),
                'queue_handlers.retry_failed_job',
                original_job_data,
                job_timeout='10m'
            )
            
            logger.debug(f"Enqueued retry job with {delay_seconds}s delay")
            return job.id
            
        except Exception as e:
            logger.error(f"Failed to enqueue retry: {e}")
            return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about queue states"""
        if not self.is_available():
            return {"status": "unavailable", "error": "Redis not connected"}
        
        try:
            stats = {
                "status": "available",
                "queues": {}
            }
            
            for queue_name, queue in self.queues.items():
                stats["queues"][queue_name] = {
                    "pending": len(queue),
                    "failed": len(queue.failed_job_registry),
                    "scheduled": len(queue.scheduled_job_registry) if hasattr(queue, 'scheduled_job_registry') else 0
                }
            
            # Worker information
            workers = Worker.all(connection=self.redis_conn)
            stats["workers"] = {
                "total": len(workers),
                "active": len([w for w in workers if w.get_state() == 'busy'])
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"status": "error", "error": str(e)}
    
    def clear_queue(self, queue_name: str) -> bool:
        """Clear all jobs from a specific queue (useful for development)"""
        if not self.is_available() or queue_name not in self.queues:
            return False
        
        try:
            queue = self.queues[queue_name]
            queue.empty()
            logger.info(f"Cleared queue: {queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear queue {queue_name}: {e}")
            return False
    
    def clear_all_queues(self) -> bool:
        """Clear all queues (useful for development/testing)"""
        if not self.is_available():
            return False
        
        success = True
        for queue_name in self.queues.keys():
            if not self.clear_queue(queue_name):
                success = False
        
        return success
    
    def get_failed_jobs(self, queue_name: str = None) -> List[Dict[str, Any]]:
        """Get failed jobs for inspection and potential retry"""
        if not self.is_available():
            return []
        
        try:
            failed_jobs = []
            queues_to_check = [queue_name] if queue_name else list(self.queues.keys())
            
            for qname in queues_to_check:
                if qname in self.queues:
                    queue = self.queues[qname]
                    for job in queue.failed_job_registry.get_job_ids():
                        try:
                            job_obj = queue.failed_job_registry.get(job)
                            if job_obj:
                                failed_jobs.append({
                                    'id': job_obj.id,
                                    'queue': qname,
                                    'func_name': job_obj.func_name,
                                    'args': job_obj.args,
                                    'kwargs': job_obj.kwargs,
                                    'created_at': job_obj.created_at.isoformat() if job_obj.created_at else None,
                                    'failed_at': job_obj.failed_at.isoformat() if job_obj.failed_at else None,
                                    'exc_info': job_obj.exc_info
                                })
                        except Exception:
                            # Skip jobs that can't be loaded
                            continue
            
            return failed_jobs
            
        except Exception as e:
            logger.error(f"Failed to get failed jobs: {e}")
            return []
    
    def close(self):
        """Close Redis connection"""
        if self.redis_conn:
            try:
                self.redis_conn.close()
                logger.debug("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")