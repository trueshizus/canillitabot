import logging
import sys
import os
from config import Config

def setup_logging(config: Config):
    """Setup detailed logging configuration"""
    # Create logs directory
    log_path = config.log_file
    log_dir = '/'.join(log_path.split('/')[:-1])
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format=config.log_format,
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )