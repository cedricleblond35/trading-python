from logging.handlers import RotatingFileHandler
import logging


class Log:
    def __init__(self):
        self.logger = logging.getLogger('mylogger')
        self.__formatLogger()
        self.__level()

    def __formatLogger(self):
        # create a logging format
        handler = logging.FileHandler('mylog.log')
        formatter = logging.Formatter('[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s','%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def __level(self):
        # set logger level
        self.logger.setLevel(logging.WARNING)
        # or you can set one of the following level
        # logger.setLevel(logging.INFO)
        # logger.setLevel(logging.DEBUG)
        # set to true on debug environment only
        DEBUG = True

        if DEBUG:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.CRITICAL)

    def getLogger(self):
        return self.logger
