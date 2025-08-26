"""
Simple health check HTTP server for CanillitaBot.
"""

import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, health_checker=None, **kwargs):
        self.health_checker = health_checker
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/health':
            try:
                if self.health_checker and self.health_checker.is_healthy():
                    self._send_json(200, {'status': 'healthy', 'timestamp': datetime.now().isoformat()})
                else:
                    self._send_json(503, {'status': 'unhealthy', 'timestamp': datetime.now().isoformat()})
            except Exception as e:
                self._send_json(503, {'status': 'error', 'error': str(e)})
        else:
            self._send_json(404, {'error': 'Not Found'})
    
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress request logs

class HealthChecker:
    def __init__(self, bot_manager=None, database=None):
        self.bot_manager = bot_manager
        self.database = database
        self.start_time = time.time()
        self.last_activity = time.time()
        self._shutting_down = False
    
    def update_activity(self):
        self.last_activity = time.time()
    
    def mark_shutdown(self):
        self._shutting_down = True
    
    def is_healthy(self):
        if self._shutting_down:
            return False
        
        # Check database
        try:
            if self.database:
                self.database.is_post_processed("health_test")
        except Exception:
            return False
        
        # Check if bot is running
        if self.bot_manager and hasattr(self.bot_manager, 'running'):
            return self.bot_manager.running
        
        return True

class HealthServer:
    def __init__(self, port=8080, health_checker=None):
        self.port = port
        self.health_checker = health_checker
        self.server = None
        self.thread = None
        self._running = False
    
    def start(self):
        if self._running:
            return
        
        def handler(*args, **kwargs):
            return HealthCheckHandler(*args, health_checker=self.health_checker, **kwargs)
        
        self.server = HTTPServer(('0.0.0.0', self.port), handler)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self._running = True
        logger.info(f"Health server started on port {self.port}")
    
    def _run(self):
        while self._running:
            self.server.handle_request()
    
    def stop(self):
        if not self._running:
            return
        
        self._running = False
        if self.server:
            self.server.server_close()
        logger.info("Health server stopped")