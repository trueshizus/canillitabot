import time
import logging
from typing import List
from praw.models import Submission
from src.core.config import Config

logger = logging.getLogger(__name__)

class CommentManager:
    """Handles posting and formatting of Reddit comments"""
    
    def __init__(self, config: Config, reddit):
        self.config = config
        self.reddit = reddit
    
    def post_comment(self, submission: Submission, content: str) -> bool:
        """Post a comment on a submission (backwards compatibility)"""
        return self.post_comments(submission, [content])
    
    def post_comments(self, submission: Submission, comments: List[str]) -> bool:
        """Post comment(s) on a submission, with replies for long articles"""
        try:
            # Check if we already commented
            submission.comments.replace_more(limit=0)
            for comment in submission.comments:
                if comment.author and comment.author.name == self.config.reddit_username:
                    logger.info(f"Already commented on post {submission.id}")
                    return True
            
            if not comments:
                logger.warning("No comments to post")
                return False
            
            # Post the main comment
            main_comment = submission.reply(comments[0])
            
            # Try to sticky/pin the comment (only works if bot is a moderator)
            try:
                main_comment.mod.distinguish(how='yes', sticky=True)
                logger.info(f"Posted and pinned main comment on post {submission.id}: {submission.title}")
            except Exception as pin_error:
                logger.debug(f"Could not pin comment (not a moderator): {pin_error}")
                logger.info(f"Posted main comment on post {submission.id}: {submission.title}")
            
            # Rate limiting after main comment
            time.sleep(2)
            
            # Post continuation comments as replies to the main comment
            for i, continuation_content in enumerate(comments[1:], 1):
                try:
                    reply = main_comment.reply(continuation_content)
                    logger.info(f"Posted continuation comment {i} on post {submission.id}")
                    
                    # Rate limiting between continuation comments
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Failed to post continuation comment {i} on {submission.id}: {e}")
                    # Continue with remaining parts even if one fails
            
            total_comments = len(comments)
            logger.info(f"Successfully posted {total_comments} comment(s) on post {submission.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post comments on {submission.id}: {e}")
            return False
    
    def format_comment(self, article_content: str, article_url: str, article_title: str = "") -> List[str]:
        """Format article content into Reddit comment(s), splitting if necessary"""
        # Format the main comment with title
        main_comment = self.config.comment_template.format(
            content="",  # We'll add content separately
            url=article_url,
            title=article_title
        )
        
        # Calculate how much space we have for content in the main comment
        main_comment_overhead = len(main_comment)
        available_space = self.config.max_comment_length - main_comment_overhead
        
        # Split content into chunks that fit
        comment_parts = self._split_content_for_comments(article_content, available_space)
        
        # Create the formatted comments
        formatted_comments = []
        
        for i, content_part in enumerate(comment_parts):
            if i == 0:
                # First comment includes the full template with title
                formatted = self.config.comment_template.format(
                    content=content_part,
                    url=article_url,
                    title=article_title
                )
            else:
                # Continuation comments use simpler template
                formatted = self.config.continuation_template.format(
                    content=content_part
                )
            
            formatted_comments.append(formatted)
        
        return formatted_comments
    
    def _split_content_for_comments(self, content: str, first_comment_space: int) -> List[str]:
        """Split content into chunks that fit in Reddit comments"""
        if not content:
            return [""]
        
        parts = []
        remaining_content = content
        
        # First chunk - fits in main comment with template overhead
        if len(remaining_content) <= first_comment_space:
            return [remaining_content]
        
        # Find good breaking point for first chunk
        first_chunk = remaining_content[:first_comment_space]
        break_point = self._find_good_break_point(first_chunk)
        
        if break_point > 0:
            first_chunk = remaining_content[:break_point]
            remaining_content = remaining_content[break_point:].lstrip()
        else:
            remaining_content = remaining_content[first_comment_space:].lstrip()
        
        parts.append(first_chunk)
        
        # Remaining chunks - fit in continuation comments
        continuation_space = self.config.max_comment_length - len(self.config.continuation_template.format(content=""))
        
        while remaining_content:
            if len(remaining_content) <= continuation_space:
                parts.append(remaining_content)
                break
            
            chunk = remaining_content[:continuation_space]
            break_point = self._find_good_break_point(chunk)
            
            if break_point > 0:
                chunk = remaining_content[:break_point]
                remaining_content = remaining_content[break_point:].lstrip()
            else:
                remaining_content = remaining_content[continuation_space:].lstrip()
            
            parts.append(chunk)
        
        return parts
    
    def _find_good_break_point(self, text: str) -> int:
        """Find a good place to break text (end of paragraph, sentence, etc.)"""
        # Prefer breaking at paragraph boundaries
        last_double_newline = text.rfind('\n\n')
        if last_double_newline > len(text) * 0.7:
            return last_double_newline + 2
        
        # Next preference: end of sentence
        sentence_endings = ['. ', '.\n', '! ', '!\n', '? ', '?\n']
        best_break = -1
        
        for ending in sentence_endings:
            pos = text.rfind(ending)
            if pos > len(text) * 0.7 and pos > best_break:
                best_break = pos + len(ending)
        
        if best_break > 0:
            return best_break
        
        # Fallback: break at word boundary
        last_space = text.rfind(' ')
        if last_space > len(text) * 0.8:
            return last_space + 1
        
        return -1  # No good break point found
