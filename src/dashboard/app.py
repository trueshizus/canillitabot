"""
Simple Flask web dashboard for CanillitaBot monitoring and statistics.
Provides a lightweight interface to view processed posts and retry functionality.
"""

from flask import Flask, render_template, jsonify, request
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directories to Python path to access core modules
current_path = Path(__file__).parent
src_path = current_path.parent
sys.path.insert(0, str(src_path))

from core.config import Config
from core.database import Database

logger = logging.getLogger(__name__)

class CanillitaDashboard:
    """Web dashboard for monitoring CanillitaBot"""
    
    def __init__(self, host='0.0.0.0', port=5000, debug=False):
        self.app = Flask(__name__, 
                        template_folder=str(current_path / 'templates'),
                        static_folder=str(current_path / 'static'))
        self.host = host
        self.port = port
        self.debug = debug
        
        # Initialize components
        self.config = Config()
        self.database = Database(self.config)
        
        # Initialize queue manager if available (needed for fetch new posts)
        self.queue_manager = None
        try:
            from shared.queue import QueueManager
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
        
        @self.app.route('/api/posts')
        def api_posts():
            """Get recent posts with comment data"""
            limit = request.args.get('limit', 50, type=int)
            posts = self.database.get_recent_posts(limit)
            
            # Convert timestamps to readable format and include all data
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
        
        @self.app.route('/api/retry-post/<post_id>', methods=['POST'])
        def api_retry_post(post_id):
            """Retry processing a post"""
            try:
                # Here you would add the post back to the queue or processing system
                # For now, we'll just return a success response
                # In a real implementation, you'd want to:
                # 1. Get the post details from the database
                # 2. Add it back to the processing queue
                # 3. Return appropriate response
                
                logger.info(f"Retry requested for post: {post_id}")
                
                # Mock implementation - you'd implement actual retry logic here
                return jsonify({"success": True, "message": "Post queued for retry"})
                
            except Exception as e:
                logger.error(f"Error retrying post {post_id}: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/fetch-new-posts', methods=['POST'])
        def api_fetch_new_posts():
            """Fetch new posts from subreddit and return info about unprocessed ones"""
            try:
                # Import Reddit client
                from clients.reddit import RedditClient
                
                reddit_client = RedditClient(self.config)
                
                # Get the monitored subreddits from config
                subreddits = getattr(self.config, 'subreddits', ['argentina'])
                found_posts = 0
                new_posts_info = []
                
                for subreddit_name in subreddits:
                    logger.info(f"Fetching new posts from r/{subreddit_name}")
                    
                    # Get the last 10 posts from the subreddit
                    try:
                        subreddit = reddit_client.reddit.subreddit(subreddit_name)
                        posts = list(subreddit.new(limit=10))
                        
                        for post in posts:
                            # Check if we already have this post in the database
                            if not self.database.is_post_processed(post.id):
                                found_posts += 1
                                new_posts_info.append({
                                    'id': post.id,
                                    'title': post.title,
                                    'url': post.url,
                                    'subreddit': subreddit_name,
                                    'created_utc': post.created_utc
                                })
                                logger.info(f"Found unprocessed post: {post.title[:50]}...")
                    
                    except Exception as e:
                        logger.error(f"Error fetching from r/{subreddit_name}: {e}")
                        continue
                
                logger.info(f"Found {found_posts} unprocessed posts")
                
                # Store the found posts in a simple way for now
                # In a full implementation, you'd add these to your processing queue
                # For now, we'll just return the count
                
                return jsonify({
                    "success": True, 
                    "found_posts": found_posts,
                    "message": f"Found {found_posts} new posts that haven't been processed yet",
                    "posts": new_posts_info[:5]  # Return first 5 for reference
                })
                
            except Exception as e:
                logger.error(f"Error fetching new posts: {e}")
                return jsonify({
                    "success": False, 
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/health')
        def api_health():
            """Health check endpoint"""
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
            }
            
            # Test database connection
            try:
                self.database.get_processing_stats(1)
            except Exception as e:
                health_status["status"] = "error"
                health_status["error"] = str(e)
            
            return jsonify(health_status)
    
    def run(self):
        """Start the dashboard server"""
        logger.info(f"Starting CanillitaBot Dashboard on {self.host}:{self.port}")
        # Enable reloader in debug mode for auto-refresh during development
        self.app.run(
            host=self.host, 
            port=self.port, 
            debug=self.debug,
            use_reloader=self.debug,  # Auto-reload when files change
            use_debugger=self.debug
        )

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
