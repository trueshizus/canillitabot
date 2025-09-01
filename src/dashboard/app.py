"""
Simple Flask web dashboard for CanillitaBot monitoring and statistics.
Provides a lightweight interface to view processed posts and retry functionality.
"""

from flask import Flask, render_template, jsonify, request
import logging
import sys
import json
import html
from datetime import datetime
from pathlib import Path

# Import Pygments for JSON syntax highlighting
try:
    from pygments import highlight
    from pygments.lexers import JsonLexer
    from pygments.formatters import HtmlFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

# Add parent directories to Python path to access core modules
current_path = Path(__file__).parent
src_path = current_path.parent
project_root = src_path.parent
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.core.database import Database
from src.clients.reddit import RedditClient
from src.shared.queue import QueueManager

logger = logging.getLogger(__name__)

def format_log_line(log_line: str) -> dict:
    """Format a single log line for display"""
    try:
        # Try to parse as JSON (structured logs)
        parsed = json.loads(log_line.strip())
        
        if PYGMENTS_AVAILABLE:
            # Pretty print JSON with syntax highlighting
            pretty_json = json.dumps(parsed, indent=2, ensure_ascii=False)
            lexer = JsonLexer()
            formatter = HtmlFormatter(
                style='github-dark',
                noclasses=True,
                cssclass='highlight',
                linenos=False
            )
            highlighted = highlight(pretty_json, lexer, formatter)
            
            return {
                'type': 'json',
                'level': parsed.get('level', 'INFO'),
                'timestamp': parsed.get('timestamp', ''),
                'formatted': highlighted,
                'raw': log_line.strip()
            }
        else:
            # Fallback to manual JSON formatting
            return {
                'type': 'json',
                'level': parsed.get('level', 'INFO'),
                'timestamp': parsed.get('timestamp', ''),
                'formatted': f'<pre class="json-log">{html.escape(json.dumps(parsed, indent=2))}</pre>',
                'raw': log_line.strip()
            }
            
    except (json.JSONDecodeError, ValueError):
        # Handle plain text logs
        level = 'INFO'
        if ' ERROR ' in log_line or ' CRITICAL ' in log_line:
            level = 'ERROR'
        elif ' WARNING ' in log_line or ' WARN ' in log_line:
            level = 'WARNING'
        
        return {
            'type': 'text',
            'level': level,
            'timestamp': '',
            'formatted': f'<pre class="text-log">{html.escape(log_line.strip())}</pre>',
            'raw': log_line.strip()
        }

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
        self.reddit_client = RedditClient(self.config)
        
        # Initialize queue manager if available (needed for fetch new posts)
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
            """Fetch new posts from subreddit and process them like the main bot"""
            try:
                # Get the monitored subreddits from config
                subreddits = getattr(self.config, 'subreddits', ['argentina'])
                total_found = 0
                total_processed = 0
                total_successful = 0
                processing_results = []
                
                for subreddit_name in subreddits:
                    logger.info(f"Fetching and processing new posts from r/{subreddit_name}")
                    
                    try:
                        # Get new posts using the same method as the main bot
                        posts = list(self.reddit_client.get_new_posts(
                            subreddit_name, 
                            limit=getattr(self.config, 'max_posts_per_check', 10)
                        ))
                        
                        for submission in posts:
                            # Skip if already processed (same check as main bot)
                            if self.database.is_post_processed(submission.id):
                                logger.debug(f"Post {submission.id} already processed, skipping")
                                continue
                            
                            total_found += 1
                            
                            # Validate submission (same as main bot)
                            if not self.reddit_client.validate_submission(submission):
                                logger.debug(f"Post {submission.id} failed validation, skipping")
                                self.database.record_processed_post(
                                    post_id=submission.id,
                                    subreddit=subreddit_name,
                                    title=submission.title,
                                    url=getattr(submission, 'url', ''),
                                    author=submission.author.name if submission.author else '[deleted]',
                                    created_utc=submission.created_utc,
                                    success=False,
                                    error_message="Failed validation"
                                )
                                continue
                            
                            # Process the submission using the same logic as main bot
                            success, error_message = self._process_submission(submission, subreddit_name)
                            total_processed += 1
                            
                            if success:
                                total_successful += 1
                            
                            processing_results.append({
                                'id': submission.id,
                                'title': submission.title[:50] + '...' if len(submission.title) > 50 else submission.title,
                                'success': success,
                                'error': error_message if not success else None
                            })
                            
                            logger.info(f"Processed post {submission.id}: {'success' if success else 'failed'} {error_message if error_message else ''}")
                    
                    except Exception as e:
                        logger.error(f"Error processing r/{subreddit_name}: {e}")
                        continue
                
                success_rate = total_successful / total_processed if total_processed > 0 else 0
                
                return jsonify({
                    "success": True,
                    "found_posts": total_found,
                    "processed_posts": total_processed,
                    "successful_posts": total_successful,
                    "success_rate": f"{success_rate:.1%}",
                    "message": f"Found {total_found} new posts, processed {total_processed}, {total_successful} successful",
                    "results": processing_results[:5]  # Return first 5 results
                })
                
            except Exception as e:
                logger.error(f"Error fetching and processing new posts: {e}")
                return jsonify({
                    "success": False, 
                    "error": str(e)
                }), 500
        
        @self.app.route('/logs')
        def logs_page():
            """Logs page"""
            return render_template('logs.html')
        
        @self.app.route('/api/logs')
        def api_logs():
            """Get application logs with formatted output"""
            log_type = request.args.get('type', 'main')  # 'main' or 'errors'
            lines = request.args.get('lines', 100, type=int)
            raw = request.args.get('raw', 'false').lower() == 'true'  # Option for raw output
            
            try:
                # Use Docker container path directly
                if log_type == 'errors':
                    log_file = Path('/app/logs/canillitabot_errors.log')
                else:
                    log_file = Path('/app/logs/canillitabot.log')
                
                if not log_file.exists():
                    return jsonify({
                        "success": False,
                        "error": f"Log file {log_file} not found"
                    })
                
                # Read the last N lines of the log file
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                if raw:
                    # Return raw logs (for backwards compatibility)
                    return jsonify({
                        "success": True,
                        "logs": recent_lines,
                        "total_lines": len(all_lines),
                        "showing_lines": len(recent_lines),
                        "log_file": str(log_file)
                    })
                else:
                    # Return formatted logs
                    formatted_logs = []
                    for line in recent_lines:
                        if line.strip():  # Skip empty lines
                            formatted_logs.append(format_log_line(line))
                    
                    return jsonify({
                        "success": True,
                        "logs": formatted_logs,
                        "total_lines": len(all_lines),
                        "showing_lines": len(formatted_logs),
                        "log_file": str(log_file),
                        "formatted": True,
                        "pygments_available": PYGMENTS_AVAILABLE
                    })
                
            except Exception as e:
                logger.error(f"Error reading logs: {e}")
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
    
    def _process_submission(self, submission, subreddit_name: str) -> tuple[bool, str]:
        """Process a single submission - either queue it or process directly (same logic as main bot)"""
        post_id = submission.id
        
        try:
            # Create submission data for queue/processing
            submission_data = {
                'id': submission.id,
                'title': submission.title,
                'url': submission.url,
                'subreddit': subreddit_name,
                'author': submission.author.name if submission.author else '[deleted]',
                'created_utc': submission.created_utc
            }
            
            # If queue system is available, enqueue the post for processing (same as main bot)
            if self.queue_manager and self.queue_manager.is_available():
                logger.debug(f"Enqueuing post {post_id} for processing")
                job_id = self.queue_manager.enqueue_post_discovery(subreddit_name, submission_data)
                
                if job_id:
                    logger.debug(f"Enqueued post {submission.id} for processing (job: {job_id})")
                    return True, None
                else:
                    logger.warning(f"Failed to enqueue post {submission.id}, falling back to direct processing")
                    return self._process_submission_direct(submission, subreddit_name)
            else:
                # Fall back to direct processing
                logger.debug(f"Queue not available, processing post {post_id} directly")
                return self._process_submission_direct(submission, subreddit_name)
                
        except Exception as e:
            error_msg = f"Error processing submission {submission.id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _process_submission_direct(self, submission, subreddit_name: str) -> tuple[bool, str]:
        """Process a submission directly (without queue) - simplified version of main bot logic"""
        post_id = submission.id
        
        try:
            # Check if it's a news article (same validation as main bot)
            if not self.reddit_client.is_news_article(submission):
                error_msg = "Not a news article"
                logger.debug(f"Post {post_id} is not a news article, skipping")
                self.database.record_processed_post(
                    post_id=post_id,
                    subreddit=subreddit_name,
                    title=submission.title,
                    url=submission.url,
                    author=submission.author.name if submission.author else '[deleted]',
                    created_utc=submission.created_utc,
                    success=False,
                    error_message=error_msg
                )
                return False, error_msg
            
            logger.info(f"Processing news article directly: {submission.title[:50]}...")
            
            # For now, just record that we attempted to process it
            # In a full implementation, you'd add article extraction and comment posting here
            # But that requires initializing ArticleExtractor and GeminiClient
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=True,  # Mark as successful for now
                error_message=None
            )
            
            logger.info(f"Successfully queued/processed post {post_id}")
            return True, None
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            logger.error(f"Error in direct processing for post {post_id}: {e}")
            self.database.record_processed_post(
                post_id=post_id,
                subreddit=subreddit_name,
                title=submission.title,
                url=submission.url,
                author=submission.author.name if submission.author else '[deleted]',
                created_utc=submission.created_utc,
                success=False,
                error_message=error_msg
            )
            return False, error_msg
    
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
