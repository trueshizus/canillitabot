"""
Simple Flask web dashboard for CanillitaBot monitoring and statistics.
Provides a lightweight interface to view database entries, processing stats, and queue status.
"""

from flask import Flask, render_template, jsonify, request
import logging
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add src directory to Python path
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from config import Config
from database import Database
from queue_manager import QueueManager

logger = logging.getLogger(__name__)

class CanillitaDashboard:
    """Web dashboard for monitoring CanillitaBot"""
    
    def __init__(self, host='0.0.0.0', port=5000, debug=False):
        self.app = Flask(__name__, template_folder='../templates', static_folder='../static')
        self.host = host
        self.port = port
        self.debug = debug
        
        # Initialize components
        self.config = Config()
        self.database = Database(self.config)
        
        # Initialize queue manager if available
        self.queue_manager = None
        try:
            if getattr(self.config, 'queue_enabled', False):
                self.queue_manager = QueueManager(self.config)
                if not self.queue_manager.is_available():
                    self.queue_manager = None
        except Exception as e:
            logger.warning(f"Queue manager not available: {e}")
            self.queue_manager = None
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return render_template('dashboard.html')
        
        @self.app.route('/api/stats')
        def api_stats():
            """Get processing statistics"""
            days = request.args.get('days', 7, type=int)
            stats = self.database.get_processing_stats(days)
            return jsonify(stats)
        
        @self.app.route('/api/posts')
        def api_posts():
            """Get recent posts"""
            limit = request.args.get('limit', 50, type=int)
            posts = self.database.get_recent_posts(limit)
            
            # Convert timestamps to readable format
            for post in posts:
                if post.get('processed_at'):
                    post['processed_at_readable'] = datetime.fromisoformat(
                        post['processed_at'].replace('Z', '+00:00')
                    ).strftime('%Y-%m-%d %H:%M:%S')
                if post.get('created_utc'):
                    post['created_readable'] = datetime.fromtimestamp(
                        post['created_utc']
                    ).strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify(posts)
        
        @self.app.route('/api/failed-posts')
        def api_failed_posts():
            """Get recently failed posts"""
            days = request.args.get('days', 7, type=int)
            failed_posts = self.database.get_failed_posts(days)
            
            # Convert timestamps to readable format
            for post in failed_posts:
                if post.get('processed_at'):
                    post['processed_at_readable'] = datetime.fromisoformat(
                        post['processed_at'].replace('Z', '+00:00')
                    ).strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify(failed_posts)
        
        @self.app.route('/api/domains')
        def api_domains():
            """Get domain statistics"""
            try:
                # Get successful posts by domain from the last 30 days
                cutoff_date = datetime.now() - timedelta(days=30)
                
                with self._get_connection() as conn:
                    cursor = conn.execute('''
                        SELECT 
                            CASE 
                                WHEN url LIKE '%infobae.com%' THEN 'infobae.com'
                                WHEN url LIKE '%clarin.com%' THEN 'clarin.com'
                                WHEN url LIKE '%lanacion.com.ar%' THEN 'lanacion.com.ar'
                                WHEN url LIKE '%pagina12.com.ar%' THEN 'pagina12.com.ar'
                                WHEN url LIKE '%tn.com.ar%' THEN 'tn.com.ar'
                                WHEN url LIKE '%ambito.com%' THEN 'ambito.com'
                                WHEN url LIKE '%youtube.com%' OR url LIKE '%youtu.be%' THEN 'YouTube'
                                WHEN url LIKE '%twitter.com%' OR url LIKE '%x.com%' THEN 'X/Twitter'
                                ELSE 'Other'
                            END as domain,
                            COUNT(*) as total_posts,
                            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_posts,
                            ROUND(
                                (SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 1
                            ) as success_rate
                        FROM processed_posts 
                        WHERE processed_at > ?
                        GROUP BY domain
                        ORDER BY total_posts DESC
                    ''', (cutoff_date,))
                    
                    domains = [dict(row) for row in cursor.fetchall()]
                
                return jsonify(domains)
                
            except Exception as e:
                logger.error(f"Error getting domain stats: {e}")
                return jsonify([])
        
        @self.app.route('/api/queue-status')
        def api_queue_status():
            """Get queue system status"""
            if not self.queue_manager:
                return jsonify({"status": "unavailable", "message": "Queue system not available"})
            
            return jsonify(self.queue_manager.get_queue_stats())
        
        @self.app.route('/api/health')
        def api_health():
            """Health check endpoint"""
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "database": "healthy",
                    "queue": "healthy" if self.queue_manager else "unavailable"
                }
            }
            
            # Test database connection
            try:
                self.database.get_processing_stats(1)
            except Exception as e:
                health_status["components"]["database"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
            
            # Test queue connection
            if self.queue_manager:
                try:
                    self.queue_manager.get_queue_stats()
                except Exception as e:
                    health_status["components"]["queue"] = f"error: {str(e)}"
                    health_status["status"] = "degraded"
            
            return jsonify(health_status)
        
        @self.app.route('/api/config')
        def api_config():
            """Get safe configuration information"""
            safe_config = {
                "subreddits": getattr(self.config, 'subreddits', []),
                "check_interval": getattr(self.config, 'check_interval', 30),
                "youtube_enabled": getattr(self.config, 'youtube_enabled', False),
                "x_twitter_enabled": getattr(self.config, 'x_twitter_enabled', False),
                "queue_enabled": getattr(self.config, 'queue_enabled', False),
                "news_domains": getattr(self.config, 'news_domains', []),
                "blocked_domains": getattr(self.config, 'blocked_domains', [])
            }
            
            return jsonify(safe_config)
    
    def _get_connection(self):
        """Helper method to get database connection (for compatibility)"""
        import sqlite3
        return sqlite3.connect(self.database.db_path)
    
    def run(self):
        """Start the dashboard server"""
        logger.info(f"Starting CanillitaBot Dashboard on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=self.debug)

def main():
    """Main entry point for dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CanillitaBot Web Dashboard')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start dashboard
    dashboard = CanillitaDashboard(
        host=args.host,
        port=args.port,
        debug=args.debug
    )
    
    dashboard.run()

if __name__ == "__main__":
    main()