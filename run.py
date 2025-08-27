#!/usr/bin/env python3
"""
Simple runner script for CanillitaBot - Reddit Argentina News Bot
"""

import sys
import logging
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.core.bot import BotManager
from src.shared.utils import setup_logging

def main():
    """Main entry point"""
    # Setup basic logging first
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize and start bot
        bot = BotManager()
        
        # Setup detailed logging based on config
        setup_logging(bot.config)
        
        bot.start()
        
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()