import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from core.config import Config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, config: Config):
        self.config = config
        self.db_path = Path(config.database_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database and create tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS processed_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        post_id TEXT UNIQUE NOT NULL,
                        subreddit TEXT NOT NULL,
                        title TEXT NOT NULL,
                        url TEXT NOT NULL,
                        author TEXT,
                        created_utc REAL NOT NULL,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN NOT NULL,
                        error_message TEXT,
                        article_title TEXT,
                        article_content_length INTEGER,
                        extraction_method TEXT
                    )
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_post_id ON processed_posts(post_id)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_posts(processed_at)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_subreddit ON processed_posts(subreddit)
                ''')
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def is_post_processed(self, post_id: str) -> bool:
        """Check if a post has already been processed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT 1 FROM processed_posts WHERE post_id = ?',
                    (post_id,)
                )
                return cursor.fetchone() is not None
                
        except sqlite3.Error as e:
            logger.error(f"Error checking if post {post_id} is processed: {e}")
            return True  # Assume processed to avoid duplicates on error
    
    def record_processed_post(
        self, 
        post_id: str,
        subreddit: str,
        title: str,
        url: str,
        author: str,
        created_utc: float,
        success: bool,
        error_message: Optional[str] = None,
        article_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record a processed post in the database"""
        try:
            article_title = ""
            article_content_length = 0
            extraction_method = ""
            
            if article_data:
                article_title = article_data.get('title', '')[:500]  # Truncate if too long
                article_content_length = len(article_data.get('content', ''))
                extraction_method = article_data.get('extraction_method', '')
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO processed_posts (
                        post_id, subreddit, title, url, author, created_utc,
                        success, error_message, article_title, article_content_length,
                        extraction_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post_id, subreddit, title[:500], url, author, created_utc,
                    success, error_message, article_title, article_content_length,
                    extraction_method
                ))
                conn.commit()
                
                logger.debug(f"Recorded processed post {post_id} (success: {success})")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error recording processed post {post_id}: {e}")
            return False
    
    def get_processing_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get processing statistics for the last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                # Total posts processed
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM processed_posts 
                    WHERE processed_at > ?
                ''', (cutoff_date,))
                total_processed = cursor.fetchone()[0]
                
                # Successful posts
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM processed_posts 
                    WHERE processed_at > ? AND success = 1
                ''', (cutoff_date,))
                successful = cursor.fetchone()[0]
                
                # Posts by subreddit
                cursor = conn.execute('''
                    SELECT subreddit, COUNT(*) as count 
                    FROM processed_posts 
                    WHERE processed_at > ?
                    GROUP BY subreddit
                    ORDER BY count DESC
                ''', (cutoff_date,))
                by_subreddit = dict(cursor.fetchall())
                
                # Common errors
                cursor = conn.execute('''
                    SELECT error_message, COUNT(*) as count
                    FROM processed_posts 
                    WHERE processed_at > ? AND success = 0 AND error_message IS NOT NULL
                    GROUP BY error_message
                    ORDER BY count DESC
                    LIMIT 10
                ''', (cutoff_date,))
                common_errors = dict(cursor.fetchall())
                
                return {
                    'total_processed': total_processed,
                    'successful': successful,
                    'success_rate': successful / total_processed if total_processed > 0 else 0,
                    'by_subreddit': by_subreddit,
                    'common_errors': common_errors,
                    'period_days': days
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}
    
    def get_recent_posts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently processed posts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                
                cursor = conn.execute('''
                    SELECT * FROM processed_posts
                    ORDER BY processed_at DESC
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting recent posts: {e}")
            return []
    
    def cleanup_old_entries(self) -> int:
        """Remove old entries based on configured cleanup days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.cleanup_days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    DELETE FROM processed_posts 
                    WHERE processed_at < ?
                ''', (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old database entries")
                
                return deleted_count
                
        except sqlite3.Error as e:
            logger.error(f"Error cleaning up old entries: {e}")
            return 0
    
    def get_failed_posts(self, days: int = 1) -> List[Dict[str, Any]]:
        """Get posts that failed processing in the last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute('''
                    SELECT * FROM processed_posts
                    WHERE processed_at > ? AND success = 0
                    ORDER BY processed_at DESC
                ''', (cutoff_date,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting failed posts: {e}")
            return []
    
    def vacuum_database(self):
        """Optimize database by running VACUUM"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('VACUUM')
                logger.info("Database vacuumed successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Error vacuuming database: {e}")
    
    def close(self):
        """Close database connections (cleanup method)"""
        # SQLite connections are automatically closed when context managers exit
        logger.debug("Database cleanup completed")