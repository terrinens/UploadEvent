import logging
import os

from logging import INFO, DEBUG


def create_log_dir():
    if not os.path.exists("./logs"):
        os.mkdir("./logs")


def create_logger(log_name, log_file_name, file_level: int = DEBUG, console_level: int = INFO):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    console_handler.setLevel(console_level)

    create_log_dir()

    file_handler = logging.FileHandler(os.path.join("./logs", log_file_name))
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level)

    log = logging.getLogger(log_name)
    log.setLevel(logging.DEBUG)
    log.addHandler(file_handler)
    log.addHandler(console_handler)

    return log
