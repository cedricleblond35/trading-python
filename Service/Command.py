import json
from pymongo import MongoClient
from Configuration.Config import Config


class Command:
    def __init__(self):
        self.__userId = Config.USER_ID
        self.tick = None
        self.balance = 0
        self.profit = None
        self.news = None
        self.trade = None
        self.tradeStatus = None
        self.candles = None

        # Command templates

    def baseCommand(self, commandName, arguments=None):
        if arguments is None:
            arguments = dict()
        return dict([('command', commandName), ('arguments', arguments)])

    def loginCommand(self, appName=''):
        return self.baseCommand('login', dict(userId=Config.USER_ID, password=Config.PASSWORD, appName=appName))

    # example function for processing ticks from Streaming socket
    def procTickExample(self, msg):
        #print("tick: ", msg)
        dataDownload = json.loads(json.dumps(msg))
        self.tick = dataDownload['data']

    def procTradeExample(self, msg):
        dataDownload = json.loads(json.dumps(msg))
        self.trade = dataDownload['data']

    def procBalanceExample(self, msg):
        dataDownload = json.loads(json.dumps(msg))
        self.balance = dataDownload['data']

    def procTradeStatusExample(self, msg):
        dataDownload = json.loads(json.dumps(msg))
        self.tradeStatus = dataDownload['data']

    def procProfitExample(self, msg):
        dataDownload = json.loads(json.dumps(msg))
        self.profit = dataDownload['data']

    def procNewsExample(self, msg):
        print("************* NEWS: ", msg)
        dataDownload = json.loads(json.dumps(msg))
        self.news = dataDownload['data']

    def procCandles(self, msg):
        print("==================================== candles: ", msg)
        dataDownload = json.loads(json.dumps(msg))
        self.candles = dataDownload['data']

    def getTick(self):
        return self.tick

    def getBalance(self):
        return self.balance

    def getProfit(self):
        return self.profit

    def getNews(self):
        return self.news

    def getTrade(self):
        return self.trade

    def getTradeStatus(self):
        return self.tradeStatus

    def getCandles(self):
        return self.candles
