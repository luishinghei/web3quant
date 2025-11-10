import logging
import os
import time
from datetime import datetime, timezone


def init_logger(logger_name: str) -> logging.Logger:
    folder = 'user_data'
    logs_folder = f'{folder}/logs'
    os.makedirs(logs_folder, exist_ok=True)
    
    log_file = f'{logs_folder}/{datetime.now(timezone.utc).strftime("%Y%m%d")}.log'
    
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(name)-9s - %(message)s')
    logging.Formatter.converter = time.gmtime
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
