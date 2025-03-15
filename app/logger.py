import sys
from datetime import datetime

from loguru import logger as _logger

from app.config import PROJECT_ROOT


# Default log level for console output
_print_level = "INFO"


def define_log_level(print_level="INFO", logfile_level="DEBUG", name: str = None):
    """
    Configure and initialize the logging system with customizable levels.
    
    This function sets up the Loguru logger with two outputs:
    1. Console output (stderr) with the specified print_level
    2. File output with the specified logfile_level, stored in the logs directory
    
    The log file is named with a timestamp and optional prefix for easy identification.
    
    Args:
        print_level: Log level for console output (default: "INFO")
        logfile_level: Log level for file output (default: "DEBUG")
        name: Optional prefix for the log file name
        
    Returns:
        Logger: Configured Loguru logger instance
    """
    global _print_level
    _print_level = print_level

    # Generate a timestamp for the log file name
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y%m%d%H%M%S")
    
    # Create log file name with optional prefix
    log_name = (
        f"{name}_{formatted_date}" if name else formatted_date
    )  # name a log with prefix name

    # Remove any existing handlers
    _logger.remove()
    
    # Add console handler with specified level
    _logger.add(sys.stderr, level=print_level)
    
    # Add file handler with specified level
    _logger.add(PROJECT_ROOT / f"logs/{log_name}.log", level=logfile_level)
    
    return _logger


# Initialize the default logger
logger = define_log_level()


# Example usage of the logger
if __name__ == "__main__":
    # Demonstrate different log levels
    logger.info("Starting application")    # General information
    logger.debug("Debug message")          # Detailed debugging information
    logger.warning("Warning message")      # Warning situations
    logger.error("Error message")          # Error situations
    logger.critical("Critical message")    # Critical situations

    # Demonstrate exception logging
    try:
        raise ValueError("Test error")
    except Exception as e:
        # Log exception with traceback
        logger.exception(f"An error occurred: {e}")
