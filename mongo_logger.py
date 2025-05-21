import logging
import io
from datetime import datetime
from pymongo import MongoClient

class IterationLogCaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_buffer = io.StringIO()

    def emit(self, record):
        msg = self.format(record)
        self.log_buffer.write(msg + '\n')

    def get_logs(self):
        return self.log_buffer.getvalue()

    def clear(self):
        self.log_buffer = io.StringIO()
