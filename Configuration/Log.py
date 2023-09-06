import logging

class Log:
    def __init__(self):
        self.logger = logging.getLogger('mylogger')
        handler = logging.FileHandler('mylog.log')
        formatter = logging.Formatter(
            '[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s', '%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def getLogger(self):
        return self.logger
