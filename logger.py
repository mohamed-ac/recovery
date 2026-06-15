import logging
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH  = os.path.join(BASE_DIR, "app.log")

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    if not logger.handlers:  # évite les doublons
        handler = logging.FileHandler(LOG_PATH)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger
    
    