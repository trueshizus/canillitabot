import time
import logging
from typing import List, Dict
from collections import defaultdict
from src.core.config import Config

logger = logging.getLogger(__name__)

class CommentAnalytics:
    """Handles analytics and statistics for Reddit comments"""
    
    def __init__(self, config: Config, reddit):
        self.config = config
        self.reddit = reddit
    
    def get_bot_comments(self, limit: int = 25, subreddit: str = None) -> List[Dict]:
        """Get recent comments made by the bot"""
        try:
            user = self.reddit.user.me()
            comments = []
            
            for comment in user.comments.new(limit=limit):
                # Filter by subreddit if specified
                if subreddit and comment.subreddit.display_name.lower() != subreddit.lower():
                    continue
                
                comment_data = {
                    'id': comment.id,
                    'body': comment.body,
                    'score': comment.score,
                    'created_utc': comment.created_utc,
                    'subreddit': comment.subreddit.display_name,
                    'permalink': f"https://reddit.com{comment.permalink}",
                    'submission_title': comment.submission.title if comment.submission else '',
                    'submission_url': comment.submission.url if comment.submission else '',
                    'submission_id': comment.submission.id if comment.submission else '',
                    'is_edited': comment.edited != False,
                    'gilded': comment.gilded,
                    'controversiality': comment.controversiality
                }
                comments.append(comment_data)
            
            return comments
            
        except Exception as e:
            logger.error(f"Error fetching bot comments: {e}")
            return []
    
    def get_bot_comment_stats(self, days: int = 7) -> Dict:
        """Get statistics about bot comments in the last N days"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            user = self.reddit.user.me()
            
            stats = {
                'total_comments': 0,
                'by_subreddit': defaultdict(int),
                'average_score': 0,
                'total_score': 0,
                'controversial_count': 0,
                'gilded_count': 0,
                'edited_count': 0,
                'recent_comments': []
            }
            
            scores = []
            
            for comment in user.comments.new(limit=100):  # Check more comments for stats
                if comment.created_utc < cutoff_time:
                    break
                
                stats['total_comments'] += 1
                stats['by_subreddit'][comment.subreddit.display_name] += 1
                stats['total_score'] += comment.score
                scores.append(comment.score)
                
                if comment.controversiality > 0:
                    stats['controversial_count'] += 1
                if comment.gilded > 0:
                    stats['gilded_count'] += 1
                if comment.edited:
                    stats['edited_count'] += 1
                
                # Keep recent comments for reference
                if len(stats['recent_comments']) < 10:
                    stats['recent_comments'].append({
                        'id': comment.id,
                        'subreddit': comment.subreddit.display_name,
                        'score': comment.score,
                        'created_utc': comment.created_utc,
                        'permalink': f"https://reddit.com{comment.permalink}"
                    })
            
            stats['average_score'] = sum(scores) / len(scores) if scores else 0
            stats['by_subreddit'] = dict(stats['by_subreddit'])  # Convert back to regular dict
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting bot comment stats: {e}")
            return {}
    
    def check_comment_replies(self, comment_id: str) -> List[Dict]:
        """Check replies to a specific bot comment"""
        try:
            comment = self.reddit.comment(comment_id)
            comment.refresh()
            
            replies = []
            for reply in comment.replies:
                if hasattr(reply, 'author') and reply.author:
                    reply_data = {
                        'id': reply.id,
                        'author': reply.author.name,
                        'body': reply.body,
                        'score': reply.score,
                        'created_utc': reply.created_utc,
                        'permalink': f"https://reddit.com{reply.permalink}"
                    }
                    replies.append(reply_data)
            
            return replies
            
        except Exception as e:
            logger.error(f"Error checking replies for comment {comment_id}: {e}")
            return []
