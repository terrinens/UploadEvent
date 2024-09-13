import logging
import os

from logging import INFO, DEBUG


def create_log_dir():
    if os.name == 'nt':
        logs_dir = os.path.abspath('C:\\uec_logs')
    else:
        logs_dir = os.path.abspath('/uec_logs')
        
    if not os.path.exists(logs_dir):
        os.mkdir(logs_dir)

    return logs_dir


def create_logger(log_name, log_file_name, file_level: int = DEBUG, console_level: int = INFO):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    console_handler.setLevel(console_level)

    logs_dir = create_log_dir()

    file_handler = logging.FileHandler(os.path.join(logs_dir, log_file_name))
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level)

    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.addHandler(file_handler)
    log.addHandler(console_handler)

    return log
