#!/usr/bin/env python3
"""
CanillitaBot Comment Retriever

Utility script to retrieve and analyze comments made by CanillitaBot.
This gives Claude Code the capability to examine the bot's comment history.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from core.config import Config
from clients.reddit import RedditClient

def get_comments(limit=25, subreddit=None, format_output='json'):
    """Get recent CanillitaBot comments"""
    try:
        config = Config()
        reddit_client = RedditClient(config)
        
        print(f"Fetching {limit} recent comments from CanillitaBot...")
        if subreddit:
            print(f"Filtering by subreddit: r/{subreddit}")
        
        comments = reddit_client.get_bot_comments(limit=limit, subreddit=subreddit)
        
        if format_output == 'json':
            return json.dumps(comments, indent=2, default=str)
        elif format_output == 'summary':
            return format_comments_summary(comments)
        else:
            return format_comments_readable(comments)
    
    except Exception as e:
        return f"Error retrieving comments: {e}"

def get_stats(days=7):
    """Get CanillitaBot comment statistics"""
    try:
        config = Config()
        reddit_client = RedditClient(config)
        
        print(f"Calculating comment stats for last {days} days...")
        stats = reddit_client.get_bot_comment_stats(days=days)
        
        return json.dumps(stats, indent=2, default=str)
    
    except Exception as e:
        return f"Error getting stats: {e}"

def get_comment_replies(comment_id):
    """Get replies to a specific CanillitaBot comment"""
    try:
        config = Config()
        reddit_client = RedditClient(config)
        
        print(f"Fetching replies to comment {comment_id}...")
        replies = reddit_client.check_comment_replies(comment_id)
        
        return json.dumps(replies, indent=2, default=str)
    
    except Exception as e:
        return f"Error getting replies: {e}"

def format_comments_readable(comments):
    """Format comments in a human-readable way"""
    if not comments:
        return "No comments found."
    
    output = []
    for comment in comments:
        dt = datetime.fromtimestamp(comment['created_utc'])
        output.append(f"""
Comment ID: {comment['id']}
Subreddit: r/{comment['subreddit']}
Score: {comment['score']}
Date: {dt.strftime('%Y-%m-%d %H:%M:%S')}
Submission: {comment['submission_title'][:100]}{'...' if len(comment['submission_title']) > 100 else ''}
URL: {comment['permalink']}

Body:
{comment['body'][:500]}{'...' if len(comment['body']) > 500 else ''}
{'='*80}
""")
    
    return '\n'.join(output)

def format_comments_summary(comments):
    """Format comments as a summary"""
    if not comments:
        return "No comments found."
    
    total_score = sum(c['score'] for c in comments)
    avg_score = total_score / len(comments) if comments else 0
    subreddits = list(set(c['subreddit'] for c in comments))
    
    summary = f"""
CanillitaBot Comment Summary
============================
Total Comments: {len(comments)}
Average Score: {avg_score:.1f}
Total Score: {total_score}
Subreddits: {', '.join(subreddits)}

Recent Comments:
"""
    
    for i, comment in enumerate(comments[:5], 1):
        dt = datetime.fromtimestamp(comment['created_utc'])
        summary += f"{i}. r/{comment['subreddit']} | Score: {comment['score']} | {dt.strftime('%m/%d %H:%M')}\n"
        summary += f"   {comment['submission_title'][:80]}...\n"
    
    return summary

def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Retrieve CanillitaBot comments')
    parser.add_argument('command', choices=['comments', 'stats', 'replies'], 
                       help='What to retrieve')
    parser.add_argument('--limit', '-l', type=int, default=25,
                       help='Number of comments to fetch (default: 25)')
    parser.add_argument('--subreddit', '-s', type=str,
                       help='Filter by specific subreddit')
    parser.add_argument('--days', '-d', type=int, default=7,
                       help='Days for stats calculation (default: 7)')
    parser.add_argument('--format', '-f', choices=['json', 'readable', 'summary'], 
                       default='readable', help='Output format')
    parser.add_argument('--comment-id', '-c', type=str,
                       help='Comment ID for replies command')
    
    args = parser.parse_args()
    
    if args.command == 'comments':
        result = get_comments(args.limit, args.subreddit, args.format)
    elif args.command == 'stats':
        result = get_stats(args.days)
    elif args.command == 'replies':
        if not args.comment_id:
            print("Error: --comment-id required for replies command")
            sys.exit(1)
        result = get_comment_replies(args.comment_id)
    
    print(result)

if __name__ == '__main__':
    main()