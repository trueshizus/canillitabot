#!/usr/bin/env python3
"""
Manual Post Enqueue Tool for CanillitaBot

Enqueues a specific Reddit post for processing via its URL.
"""

import sys
from pathlib import Path
import re

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from core.config import Config
from clients.reddit import RedditClient
from shared.queue import QueueManager

def enqueue_post(url: str):
    """Fetches a Reddit post and enqueues it for processing."""
    try:
        # Initialize components
        config = Config()
        reddit_client = RedditClient(config)
        queue_manager = QueueManager(config)

        if not queue_manager.is_available():
            print("❌ Queue system is not available. Please check your Redis connection.")
            return False

        # Extract submission ID from URL
        match = re.search(r"/comments/([^/]+)/", url)
        if not match:
            print(f"❌ Invalid Reddit post URL: {url}")
            return False
        submission_id = match.group(1)

        print(f"Fetching submission with ID: {submission_id}")
        submission = reddit_client.get_submission_by_id(submission_id)

        if not submission:
            print(f"❌ Could not fetch submission with ID: {submission_id}")
            return False

        post_url = submission.url
        if submission.is_self:
            print("Post is a self-post, searching for URL in body...")
            # Simple URL extraction from selftext
            url_match = re.search(r'https?://[^\s/$.?#].[^\s]*', submission.selftext)
            if url_match:
                post_url = url_match.group(0)
                print(f"Found URL in self-post body: {post_url}")
            else:
                print("❌ No URL found in self-post body.")
                return False

        submission_data = {
            'id': submission.id,
            'title': submission.title,
            'url': post_url,
            'subreddit': str(submission.subreddit),
            'author': submission.author.name if submission.author else '[deleted]',
            'created_utc': submission.created_utc
        }

        job_id = queue_manager.enqueue_article_processing(submission.id, post_url, submission_data)

        if job_id:
            print(f"✅ Successfully enqueued post {submission.id} directly to articles queue (Job ID: {job_id})")
            return True
        else:
            print(f"❌ Failed to enqueue post {submission.id} to articles queue")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python tools/enqueue_post.py \"<reddit_post_url>\"")
        sys.exit(1)
    
    url = sys.argv[1]
    
    success = enqueue_post(url)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
