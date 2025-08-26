import logging
import logging.handlers
import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
from config import Config

class StructuredLogFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

class PerformanceLogger:
    """Context manager and decorator for performance monitoring"""
    
    def __init__(self, operation_name: str, logger: logging.Logger = None, extra_data: Dict = None):
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger(__name__)
        self.extra_data = extra_data or {}
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(
            f"Starting operation: {self.operation_name}",
            extra={'extra_data': {
                'operation': self.operation_name,
                'status': 'started',
                **self.extra_data
            }}
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        status = 'completed' if exc_type is None else 'failed'
        log_level = logging.INFO if exc_type is None else logging.ERROR
        
        extra_data = {
            'operation': self.operation_name,
            'status': status,
            'duration_seconds': round(duration, 3),
            **self.extra_data
        }
        
        if exc_type:
            extra_data['error_type'] = exc_type.__name__
            extra_data['error_message'] = str(exc_val)
        
        self.logger.log(
            log_level,
            f"Operation {status}: {self.operation_name} ({duration:.3f}s)",
            extra={'extra_data': extra_data}
        )

def performance_monitor(operation_name: str = None, logger: logging.Logger = None, extra_data: Dict = None):
    """Decorator for monitoring function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            perf_logger = PerformanceLogger(op_name, logger, extra_data)
            
            with perf_logger:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

class MetricsCollector:
    """Simple metrics collection for monitoring"""
    
    def __init__(self):
        self.metrics = {}
    
    def increment(self, metric_name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        key = self._get_metric_key(metric_name, labels)
        self.metrics[key] = self.metrics.get(key, 0) + value
    
    def gauge(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        key = self._get_metric_key(metric_name, labels)
        self.metrics[key] = value
    
    def timing(self, metric_name: str, duration: float, labels: Dict[str, str] = None):
        """Record a timing metric"""
        key = self._get_metric_key(metric_name, labels)
        # Store as list to calculate percentiles later
        if key not in self.metrics:
            self.metrics[key] = []
        self.metrics[key].append(duration)
    
    def _get_metric_key(self, metric_name: str, labels: Dict[str, str] = None) -> str:
        """Generate metric key with labels"""
        if not labels:
            return metric_name
        
        label_str = ','.join([f"{k}={v}" for k, v in sorted(labels.items())])
        return f"{metric_name}[{label_str}]"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        return dict(self.metrics)
    
    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()

# Global metrics collector instance
metrics = MetricsCollector()

def setup_logging(config: Config):
    """Setup detailed logging configuration with structured logging and monitoring"""
    # Create logs directory
    log_path = config.log_file
    log_dir = '/'.join(log_path.split('/')[:-1])
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Determine if we should use structured logging
    use_structured = getattr(config, 'structured_logging', True)
    
    # Setup formatters
    if use_structured:
        file_formatter = StructuredLogFormatter()
        console_formatter = logging.Formatter(config.log_format)  # Keep console readable
    else:
        file_formatter = logging.Formatter(config.log_format)
        console_formatter = logging.Formatter(config.log_format)
    
    # Setup handlers
    handlers = []
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    handlers.append(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # Error file handler (separate file for errors)
    error_log_path = log_path.replace('.log', '_errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    handlers.append(error_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add new handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Setup specific logger configurations
    _setup_component_loggers()
    
    # Log startup information
    startup_logger = logging.getLogger('canillitabot.startup')
    startup_logger.info(
        "Logging system initialized",
        extra={'extra_data': {
            'log_level': config.log_level,
            'structured_logging': use_structured,
            'log_file': log_path,
            'error_file': error_log_path
        }}
    )

def _setup_component_loggers():
    """Configure logging levels for specific components"""
    # Set specific levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('prawcore').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('rq.worker').setLevel(logging.INFO)
    
    # Ensure our loggers are properly configured
    logging.getLogger('canillitabot').setLevel(logging.DEBUG)

class ErrorTracker:
    """Track and analyze errors for better monitoring"""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_counts = {}
        self.recent_errors = []
        self.max_recent_errors = 100
    
    def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """Track an error occurrence"""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Count errors by type
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Store recent errors
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': error_message,
            'context': context or {}
        }
        
        self.recent_errors.append(error_info)
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors.pop(0)
        
        # Log the error with structured data
        self.logger.error(
            f"Error tracked: {error_type}",
            extra={'extra_data': error_info},
            exc_info=True
        )
        
        # Update metrics
        metrics.increment('errors_total', labels={'type': error_type})
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of tracked errors"""
        return {
            'error_counts': dict(self.error_counts),
            'total_errors': sum(self.error_counts.values()),
            'recent_errors_count': len(self.recent_errors),
            'recent_errors': self.recent_errors[-10:]  # Last 10 errors
        }

# Global error tracker instance
error_tracker = ErrorTracker()