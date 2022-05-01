import json
from pymongo import MongoClient
from Configuration.Config import Config

class Command:
    def __init__(self):
        self.__userId = Config.USER_ID
        self.tick = 0

    # Command templates
    def baseCommand(self, commandName, arguments=None):
        if arguments == None:
            arguments = dict()
        return dict([('command', commandName), ('arguments', arguments)])

    def loginCommand(self, appName=''):
        return self.baseCommand('login', dict(userId=Config.USER_ID, password=Config.PASSWORD, appName=appName))

    # example function for processing ticks from Streaming socket
    def procTickExample(self, msg):
        dataDownload = json.loads(json.dumps(msg))
        tick = dataDownload['data']
        connection = MongoClient('localhost', 27017)
        db = connection["STREAMING"]

        myquery = {"symbol": tick['symbol']}
        newvalues = {
            "symbol": tick['symbol'],
            "ask": tick['ask'],
            "bid": tick['bid'],
            "askVolume": tick['askVolume'],
            "timestamp": tick['timestamp'],
            "spread": tick['spreadRaw']
        }
        db["Tick"].update(myquery, newvalues, True)

    # example function for processing trades from Streaming socket
    def procTradeExample(self, msg):
        # ("procTradeExample: ", msg)
        pass

    # example function for processing trades from Streaming socket
    def procBalanceExample(self, msg):
        dataDownload = json.loads(json.dumps(msg))
        # print("------********************** BALANCE *************************************************---------->Balance :",     dataDownload)
        value = dataDownload['data']
        # print("procBalanceExample :", value)

        connection = MongoClient('localhost', 27017)
        db = connection["STREAMING"]
        myquery = {"_id": self.__userId}
        newvalues = {
            "_id": self.__userId,
            "balance": value['balance'],
            "margin": value['margin'],
            "equityFX": value['equityFX'],
            "equity": value['equity'],
            "marginLevel": value['marginLevel'],
            "marginFree": value['marginFree']
        }
        db["Balance"].update(myquery, newvalues, True)

    # example function for processing trades from Streaming socket
    def procTradeStatusExample(self, msg):
        # print("TRADE STATUS: ", msg)
        pass

    # example function for processing trades from Streaming socket
    def procProfitExample(self, msg):
        global PROFIT
        dataDownload = json.loads(json.dumps(msg))
        PROFIT = dataDownload['data']
        # print(PROFIT)

        # TICK = dataDownload['data']
        print("---------------->profit ordre :", dataDownload['data'])

    # example function for processing news from Streaming socket
    def procNewsExample(self, msg):
        # print("NEWS: ", msg)
        pass
