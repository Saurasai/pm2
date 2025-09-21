import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create rotating file handler (max 5MB, keep 3 backups)
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Prevent duplicate logging
    logger.propagate = False