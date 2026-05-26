import os
from dotenv import load_dotenv
import logging
import colorlog


def get_logger():

    load_dotenv()  # Load .env

    log_level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
    log_level = getattr(logging, log_level_str, logging.DEBUG)

    logger = logging.getLogger(__name__)

    # Check if the logger is already configured
    if not logger.handlers:
        logger.setLevel(
            # logging.DEBUG
            log_level
        )  # Set the desired log level for the entire project

        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)s%(reset)s:%(asctime)s - %(message)s",  # Add %(reset)s to reset color after levelname
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "reset",
                "INFO": "cyan",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )

        # Create a handler for console output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(
            # logging.DEBUG
            log_level
        )  # Set the desired log level for console output
        console_handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(console_handler)

    return logger
