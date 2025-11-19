from loguru import logger
import sys
import os

def setup_logger(log_level: str = "INFO", log_file: str = "debuggenie.log"):
    """
    Configure the Loguru logger.
    """
    logger.remove() # Remove default handler

    # Add console handler
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # Add file handler
    logger.add(
        log_file,
        rotation="10 MB",
        retention="1 week",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    return logger

# Default logger instance
log = setup_logger(log_level=os.getenv("LOG_LEVEL", "INFO"))
