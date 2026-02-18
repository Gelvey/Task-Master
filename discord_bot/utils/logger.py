"""
Logging configuration
"""
import logging
import sys
from config.settings import Settings


def setup_logging():
    """Setup logging configuration"""
    log_level = getattr(logging, Settings.LOG_LEVEL.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # File handler
    file_handler = logging.FileHandler(Settings.LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce discord.py logging verbosity
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)

    logging.info(f"Logging configured at {Settings.LOG_LEVEL} level")
