import os
from datetime import datetime
from enum import Enum

from guvicorn_logger import Logger


class CustomLogger:
    BASE_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "logs"),
    )
    HISTORY_DIR = os.path.join(BASE_DIR, "history")
    ERROR_DIR = os.path.join(BASE_DIR, "error")
    DEBUG_DIR = os.path.join(BASE_DIR, "debug")

    class LogType(Enum):
        HISTORY = "history"
        ERROR = "error"
        DEBUG = "debug"

    def __init__(self):
        self.setup_logging()
        self.logger = Logger().configure()

    # 디렉토리 탐색 및 생성
    def setup_logging(self):
        if not os.path.exists(self.BASE_DIR):
            os.makedirs(self.BASE_DIR)
        if not os.path.exists(self.HISTORY_DIR):
            os.makedirs(self.HISTORY_DIR)
        if not os.path.exists(self.ERROR_DIR):
            os.makedirs(self.ERROR_DIR)
        if not os.path.exists(self.DEBUG_DIR):
            os.makedirs(self.DEBUG_DIR)

    # 파일 생성 및 쓰기
    def write(self, log_type: LogType, message: str):
        file_name, file_path = None, None

        if log_type == self.LogType.HISTORY:
            file_name = datetime.now().strftime("%Y-%m-%d") + ".txt"
            file_path = os.path.join(self.HISTORY_DIR, file_name)
        elif log_type == self.LogType.ERROR:
            file_name = datetime.now().strftime("%Y-%m-%d---%H-%M-%S") + ".txt"
            file_path = os.path.join(self.ERROR_DIR, file_name)
        elif log_type == self.LogType.DEBUG:
            file_name = datetime.now().strftime("%Y-%m-%d") + ".txt"
            file_path = os.path.join(self.DEBUG_DIR, file_name)
        else:
            raise ValueError("Invalid log type")

        with open(file_path, "a") as log_file:
            log_file.write(f"{message}\n")

    def debug(self, message: str, log_to_file: bool = True):
        self.logger.debug(message)
        if log_to_file:
            self.write(self.LogType.DEBUG, message)

    def info(self, message: str, log_to_file: bool = False):
        self.logger.info(message)
        if log_to_file:
            self.write(self.LogType.HISTORY, message)

    def warning(self, message: str, log_to_file: bool = False):
        self.logger.warning(message)
        if log_to_file:
            self.write(self.LogType.HISTORY, message)

    def error(self, message: str, log_to_file: bool = True):
        self.logger.error(message)
        if log_to_file:
            self.write(self.LogType.ERROR, message)

    def fatal(self, message: str, log_to_file: bool = True):
        self.logger.fatal(message)
        if log_to_file:
            self.write(self.LogType.ERROR, message)
