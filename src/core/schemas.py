"""
Dataclasses for the CanillitaBot configuration.
"""

from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class RedditConfig:
    """Reddit API configuration"""
    client_id: str = ""
    client_secret: str = ""
    username: str = ""
    password: str = ""
    user_agent: str = "CanillitaBot/1.0 (News Bot)"
    subreddits: List[str] = field(default_factory=list)

@dataclass
class DatabaseConfig:
    """Database configuration"""
    path: str = "data/processed_posts.db"
    cleanup_days: int = 30
    backup_enabled: bool = True
    backup_interval_hours: int = 24

@dataclass
class QueueConfig:
    """Redis queue configuration"""
    enabled: bool = False
    redis_url: str = "redis://localhost:6379/0"
    worker_timeout: int = 300
    retry_delays: List[int] = field(default_factory=lambda: [300, 900, 2700])
    max_retries: int = 3

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "logs/canillitabot.log"
    structured: bool = True
    error_tracking: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 5

@dataclass
class ExtractionConfig:
    """Content extraction configuration"""
    timeout: int = 15
    max_retries: int = 3
    user_agent: str = "CanillitaBot/1.0 (News Bot)"
    extraction_user_agent: str = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    max_article_length: int = 50000
    min_article_length: int = 200

@dataclass
class YouTubeConfig:
    """YouTube processing configuration"""
    enabled: bool = False
    summary_template: str = """# 🎥 {title}

**Resumen del video:**
{summary}

---

*[Link al video]({url})*

^(CanillitaBot v1.0 - Resumiendo videos para hacerlos más accesibles.)"""

@dataclass
class TwitterConfig:
    """Twitter/X processing configuration"""
    enabled: bool = False
    comment_template: str = """# 🐦 {author} en X

**{date}**

{text}

{media_note}

---

*[Ver post original]({url})*

^(CanillitaBot v1.0 - Compartiendo contenido de X para hacerlo más accesible.)"""

@dataclass
class BotConfig:
    """Bot behavior configuration"""
    comment_template: str = """# {title}

{content}

---

*[Link a la noticia]({url})*

^(CanillitaBot v1.0 - Compartiendo noticias para hacerlas más accesibles.)"""
    continuation_template: str = "{content}"
    max_comment_length: int = 10000
    check_interval: int = 30
    max_posts_per_check: int = 10

@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration"""
    enabled: bool = True
    health_check_interval: int = 300  # 5 minutes
    metrics_retention_days: int = 7
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'error_rate': 0.5,
        'processing_time': 30.0,
        'queue_size': 100
    })
