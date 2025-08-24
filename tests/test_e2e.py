import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import unittest
from unittest.mock import MagicMock, patch
import pytest
from src.bot import BotManager

@pytest.fixture
def bot_manager():
    with patch('src.bot.Config') as MockConfig, \
         patch('src.bot.RedditClient') as MockRedditClient, \
         patch('src.bot.ArticleExtractor') as MockArticleExtractor, \
         patch('src.bot.Database') as MockDatabase:

        # Configure mocks
        mock_config = MockConfig.return_value
        mock_config.subreddits = ['testsubreddit']
        mock_config.max_posts_per_check = 10
        
        mock_reddit_client = MockRedditClient.return_value
        mock_article_extractor = MockArticleExtractor.return_value
        mock_database = MockDatabase.return_value

        # Create BotManager instance
        manager = BotManager()
        manager.config = mock_config
        manager.reddit_client = mock_reddit_client
        manager.article_extractor = mock_article_extractor
        manager.database = mock_database
        
        yield manager

def test_e2e_successful_post(bot_manager: BotManager):
    # Arrange
    mock_submission = MagicMock()
    mock_submission.id = 'test_id'
    mock_submission.title = 'Test Title'
    mock_submission.url = 'http://example.com/article'
    mock_submission.author.name = 'test_author'
    mock_submission.created_utc = 1678886400

    bot_manager.reddit_client.get_new_posts.return_value = [mock_submission]
    bot_manager.database.is_post_processed.return_value = False
    bot_manager.reddit_client.validate_submission.return_value = True
    bot_manager.reddit_client.is_news_article.return_value = True
    bot_manager.article_extractor.extract_with_retry.return_value = {
        'title': 'Test Article Title',
        'content': 'This is the article content.'
    }
    bot_manager.reddit_client.format_comment.return_value = ["Formatted comment"]
    bot_manager.reddit_client.post_comments.return_value = True

    # Act
    bot_manager._process_subreddit('testsubreddit')

    # Assert
    bot_manager.database.is_post_processed.assert_called_once_with('test_id')
    bot_manager.reddit_client.validate_submission.assert_called_once_with(mock_submission)
    bot_manager.reddit_client.is_news_article.assert_called_once_with(mock_submission)
    bot_manager.article_extractor.extract_with_retry.assert_called_once_with('http://example.com/article')
    bot_manager.reddit_client.format_comment.assert_called_once()
    bot_manager.reddit_client.post_comments.assert_called_once_with(mock_submission, ["Formatted comment"])
    bot_manager.database.record_processed_post.assert_called_once()
