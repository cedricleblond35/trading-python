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
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

    def getmylogger(name):
        file_formatter = logging.Formatter(
            '%(asctime)s~%(levelname)s~%(message)s~module:%(module)s~function:%(module)s')
        console_formatter = logging.Formatter('%(levelname)s -- %(message)s')

        file_handler = logging.FileHandler("logfile.log")
        file_handler.setLevel(logging.WARN)
        file_handler.setFormatter(file_formatter)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(console_formatter)

        logger = logging.getLogger(name)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)

        return logger

