"""
Reddit package for CanillitaBot

This package provides Reddit API functionality split into focused components:
- connection: Reddit API connection and authentication
- monitor: Post monitoring and filtering
- comments: Comment posting and formatting
- analytics: Comment analytics and statistics
"""

from .connection import RedditConnection
from .monitor import PostMonitor
from .comments import CommentManager
from .analytics import CommentAnalytics

__all__ = [
    'RedditConnection',
    'PostMonitor', 
    'CommentManager',
    'CommentAnalytics'
]
