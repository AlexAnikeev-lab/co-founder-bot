"""
Настройка логирования
"""

import logging
import sys
from config import Config


def setup_logging() -> None:
    """Настройка системы логирования"""
    config = Config()
    
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
