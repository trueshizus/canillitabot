"""
Monitoring and metrics collection for CanillitaBot.
Provides performance tracking, error monitoring, and operational metrics.
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque

from utils import metrics, error_tracker, PerformanceLogger
from config import Config

logger = logging.getLogger(__name__)

class OperationalMetrics:
    """Collect and track operational metrics for CanillitaBot"""
    
    def __init__(self, config: Config):
        self.config = config
        self.start_time = time.time()
        
        # Processing metrics
        self.posts_discovered = 0
        self.posts_processed_success = 0
        self.posts_processed_failed = 0
        self.articles_extracted = 0
        self.youtube_videos_processed = 0
        self.twitter_posts_processed = 0
        
        # Performance metrics
        self.extraction_times = deque(maxlen=1000)  # Keep last 1000 extraction times
        self.processing_times = deque(maxlen=1000)
        
        # Error metrics
        self.errors_by_type = defaultdict(int)
        self.errors_by_domain = defaultdict(int)
        
        # Queue metrics (if available)
        self.queue_sizes = {}
        self.worker_stats = {}
        
        # Lock for thread-safe updates
        self._lock = threading.Lock()
    
    def record_post_discovered(self, subreddit: str, post_type: str = "unknown"):
        """Record that a post was discovered"""
        with self._lock:
            self.posts_discovered += 1
            metrics.increment('posts_discovered_total', labels={'subreddit': subreddit, 'type': post_type})
    
    def record_processing_success(self, content_type: str, processing_time: float, subreddit: str = None):
        """Record successful content processing"""
        with self._lock:
            self.posts_processed_success += 1
            self.processing_times.append(processing_time)
            
            if content_type == 'article':
                self.articles_extracted += 1
            elif content_type == 'youtube':
                self.youtube_videos_processed += 1
            elif content_type == 'twitter':
                self.twitter_posts_processed += 1
            
            metrics.increment('posts_processed_total', labels={'status': 'success', 'type': content_type})
            metrics.timing('processing_duration_seconds', processing_time, labels={'type': content_type})
            
            if subreddit:
                metrics.increment('posts_by_subreddit', labels={'subreddit': subreddit})
    
    def record_processing_failure(self, content_type: str, error_type: str, domain: str = None, subreddit: str = None):
        """Record failed content processing"""
        with self._lock:
            self.posts_processed_failed += 1
            self.errors_by_type[error_type] += 1
            
            if domain:
                self.errors_by_domain[domain] += 1
            
            metrics.increment('posts_processed_total', labels={'status': 'failed', 'type': content_type})
            metrics.increment('processing_errors_total', labels={'type': error_type, 'content_type': content_type})
    
    def record_extraction_time(self, duration: float, domain: str = None, success: bool = True):
        """Record article extraction timing"""
        with self._lock:
            if success:
                self.extraction_times.append(duration)
            
            labels = {'status': 'success' if success else 'failed'}
            if domain:
                labels['domain'] = domain
            
            metrics.timing('extraction_duration_seconds', duration, labels=labels)
    
    def update_queue_metrics(self, queue_stats: Dict[str, Any]):
        """Update queue-related metrics"""
        with self._lock:
            self.queue_sizes = queue_stats.get('queues', {})
            self.worker_stats = queue_stats.get('workers', {})
            
            for queue_name, stats in self.queue_sizes.items():
                metrics.gauge(f'queue_size_{queue_name}', stats.get('pending', 0))
                metrics.gauge(f'queue_failed_{queue_name}', stats.get('failed', 0))
            
            worker_total = self.worker_stats.get('total', 0)
            worker_active = self.worker_stats.get('active', 0)
            metrics.gauge('workers_total', worker_total)
            metrics.gauge('workers_active', worker_active)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        with self._lock:
            uptime = time.time() - self.start_time
            
            # Calculate processing rates
            processing_rate = (self.posts_processed_success + self.posts_processed_failed) / max(uptime / 3600, 1)
            success_rate = self.posts_processed_success / max(self.posts_processed_success + self.posts_processed_failed, 1)
            
            # Calculate average processing times
            avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
            avg_extraction_time = sum(self.extraction_times) / len(self.extraction_times) if self.extraction_times else 0
            
            return {
                'uptime_seconds': round(uptime, 1),
                'uptime_hours': round(uptime / 3600, 2),
                'posts_discovered': self.posts_discovered,
                'posts_processed_success': self.posts_processed_success,
                'posts_processed_failed': self.posts_processed_failed,
                'processing_rate_per_hour': round(processing_rate, 2),
                'success_rate': round(success_rate, 3),
                'articles_extracted': self.articles_extracted,
                'youtube_videos_processed': self.youtube_videos_processed,
                'twitter_posts_processed': self.twitter_posts_processed,
                'avg_processing_time_seconds': round(avg_processing_time, 3),
                'avg_extraction_time_seconds': round(avg_extraction_time, 3),
                'top_errors': dict(sorted(self.errors_by_type.items(), key=lambda x: x[1], reverse=True)[:5]),
                'errors_by_domain': dict(sorted(self.errors_by_domain.items(), key=lambda x: x[1], reverse=True)[:5]),
                'queue_status': self.queue_sizes,
                'worker_status': self.worker_stats
            }

class SystemMonitor:
    """Monitor system health and performance"""
    
    def __init__(self, config: Config):
        self.config = config
        self.operational_metrics = OperationalMetrics(config)
        self.alerts = []
        self.last_health_check = None
        
        # Health check thresholds
        self.error_rate_threshold = 0.5  # Alert if error rate > 50%
        self.processing_time_threshold = 30.0  # Alert if processing takes > 30 seconds
        self.queue_size_threshold = 100  # Alert if queue size > 100
    
    def record_error(self, error: Exception, context: Dict[str, Any] = None):
        """Record and track an error"""
        error_tracker.track_error(error, context)
        
        # Extract context for operational metrics
        content_type = context.get('content_type', 'unknown') if context else 'unknown'
        domain = context.get('domain') if context else None
        subreddit = context.get('subreddit') if context else None
        
        self.operational_metrics.record_processing_failure(
            content_type=content_type,
            error_type=type(error).__name__,
            domain=domain,
            subreddit=subreddit
        )
        
        # Check if we should generate an alert
        self._check_error_rate_alert()
    
    def record_successful_processing(self, content_type: str, duration: float, context: Dict[str, Any] = None):
        """Record successful content processing"""
        subreddit = context.get('subreddit') if context else None
        self.operational_metrics.record_processing_success(content_type, duration, subreddit)
        
        # Check for performance alerts
        if duration > self.processing_time_threshold:
            self._add_alert(
                'performance',
                f'Slow processing detected: {duration:.2f}s for {content_type}',
                {'duration': duration, 'type': content_type, 'threshold': self.processing_time_threshold}
            )
    
    def update_queue_status(self, queue_stats: Dict[str, Any]):
        """Update queue status and check for alerts"""
        self.operational_metrics.update_queue_metrics(queue_stats)
        
        # Check for queue size alerts
        for queue_name, stats in queue_stats.get('queues', {}).items():
            pending = stats.get('pending', 0)
            if pending > self.queue_size_threshold:
                self._add_alert(
                    'queue_size',
                    f'Large queue detected: {queue_name} has {pending} pending jobs',
                    {'queue': queue_name, 'size': pending, 'threshold': self.queue_size_threshold}
                )
    
    def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        self.last_health_check = datetime.now()
        
        health_status = {
            'timestamp': self.last_health_check.isoformat(),
            'overall_status': 'healthy',
            'components': {},
            'metrics': self.operational_metrics.get_summary(),
            'alerts': self.get_active_alerts()
        }
        
        # Component health checks
        components = ['bot', 'database', 'queue', 'workers']
        
        for component in components:
            try:
                component_health = self._check_component_health(component)
                health_status['components'][component] = component_health
                
                if component_health['status'] != 'healthy':
                    health_status['overall_status'] = 'degraded'
                    
            except Exception as e:
                logger.error(f"Health check failed for {component}: {e}")
                health_status['components'][component] = {
                    'status': 'error',
                    'message': str(e)
                }
                health_status['overall_status'] = 'unhealthy'
        
        # Log health check results
        logger.info(
            f"Health check completed: {health_status['overall_status']}",
            extra={'extra_data': {
                'health_status': health_status['overall_status'],
                'components': {k: v['status'] for k, v in health_status['components'].items()},
                'active_alerts': len(health_status['alerts'])
            }}
        )
        
        return health_status
    
    def _check_component_health(self, component: str) -> Dict[str, Any]:
        """Check health of a specific component"""
        if component == 'bot':
            # Check if bot is processing posts regularly
            summary = self.operational_metrics.get_summary()
            if summary['uptime_hours'] > 1 and summary['posts_discovered'] == 0:
                return {'status': 'warning', 'message': 'No posts discovered in over 1 hour'}
            return {'status': 'healthy', 'message': 'Bot is operational'}
        
        elif component == 'database':
            # Database health is checked by attempting operations
            return {'status': 'healthy', 'message': 'Database operational'}
        
        elif component == 'queue':
            # Check if queue system is available
            queue_status = self.operational_metrics.queue_sizes
            if not queue_status:
                return {'status': 'unavailable', 'message': 'Queue system not available'}
            
            # Check for stuck jobs
            total_failed = sum(stats.get('failed', 0) for stats in queue_status.values())
            if total_failed > 50:
                return {'status': 'warning', 'message': f'{total_failed} failed jobs in queues'}
            
            return {'status': 'healthy', 'message': 'Queue system operational'}
        
        elif component == 'workers':
            # Check worker status
            worker_stats = self.operational_metrics.worker_stats
            if not worker_stats or worker_stats.get('total', 0) == 0:
                return {'status': 'warning', 'message': 'No workers available'}
            
            active_ratio = worker_stats.get('active', 0) / worker_stats.get('total', 1)
            if active_ratio > 0.8:
                return {'status': 'warning', 'message': 'High worker utilization'}
            
            return {'status': 'healthy', 'message': f"{worker_stats.get('total', 0)} workers available"}
        
        return {'status': 'unknown', 'message': 'Component status unknown'}
    
    def _check_error_rate_alert(self):
        """Check if error rate has exceeded threshold"""
        summary = self.operational_metrics.get_summary()
        error_rate = 1 - summary['success_rate']
        
        if error_rate > self.error_rate_threshold:
            self._add_alert(
                'error_rate',
                f'High error rate detected: {error_rate:.1%}',
                {'error_rate': error_rate, 'threshold': self.error_rate_threshold}
            )
    
    def _add_alert(self, alert_type: str, message: str, context: Dict[str, Any] = None):
        """Add an alert to the alert list"""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        
        # Avoid duplicate alerts
        existing_alert = next((a for a in self.alerts if a['type'] == alert_type and a['message'] == message), None)
        if not existing_alert:
            self.alerts.append(alert)
            logger.warning(f"Alert generated: {alert_type} - {message}", extra={'extra_data': alert})
        
        # Keep only recent alerts
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.alerts = [a for a in self.alerts if datetime.fromisoformat(a['timestamp']) > cutoff_time]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts"""
        cutoff_time = datetime.now() - timedelta(minutes=15)  # Alerts active for 15 minutes
        return [a for a in self.alerts if datetime.fromisoformat(a['timestamp']) > cutoff_time]
    
    def get_metrics_export(self) -> Dict[str, Any]:
        """Get metrics in exportable format (e.g., for Prometheus)"""
        all_metrics = metrics.get_metrics()
        operational_summary = self.operational_metrics.get_summary()
        
        return {
            'metrics': all_metrics,
            'summary': operational_summary,
            'timestamp': datetime.now().isoformat(),
            'error_summary': error_tracker.get_error_summary()
        }

# Create global monitor instance (to be initialized with config)
monitor: Optional[SystemMonitor] = None

def initialize_monitoring(config: Config) -> SystemMonitor:
    """Initialize global monitoring system"""
    global monitor
    monitor = SystemMonitor(config)
    logger.info("Monitoring system initialized")
    return monitor

def get_monitor() -> Optional[SystemMonitor]:
    """Get the global monitor instance"""
    return monitor