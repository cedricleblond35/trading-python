from Configuration.Config import Config
from threading import Thread
from Service.JsonSocket import JsonSocket


class APIStreamClient(JsonSocket):

    def __init__(self,
                 address=Config.DEFAULT_XAPI_ADDRESS, port=Config.DEFUALT_XAPI_STREAMING_PORT, encrypt=True, ssId=None,
                 tickFun=None,
                 tradeFun=None,
                 balanceFun=None,
                 tradeStatusFun=None,
                 profitFun=None,
                 newsFun=None
                 ):
        super(APIStreamClient, self).__init__(address, port, encrypt)
        self._ssId = ssId

        self._tickFun = tickFun
        self._tradeFun = tradeFun
        self._balanceFun = balanceFun
        self._tradeStatusFun = tradeStatusFun
        self._profitFun = profitFun
        self._newsFun = newsFun

        if (not self.connect()):
            raise Exception("Cannot connect to streaming on " + address + ":" + str(port) + " after " + str(
                Config.API_MAX_CONN_TRIES) + " retries")

        self._running = True
        self._t = Thread(target=self._readStream, args=())
        self._t.setDaemon(True)
        self._t.start()

    def _readStream(self):
        while (self._running):
            msg = self._readObj()
            # logger.info("Stream received: " + str(msg))
            if (msg["command"] == 'tickPrices'):
                self._tickFun(msg)
            elif (msg["command"] == 'trade'):
                self._tradeFun(msg)
            elif (msg["command"] == "balance"):
                self._balanceFun(msg)
            elif (msg["command"] == "tradeStatus"):
                self._tradeStatusFun(msg)
            elif (msg["command"] == "profit"):
                self._profitFun(msg)
            elif (msg["command"] == "news"):
                self._newsFun(msg)

    def disconnect(self):
        self._running = False
        self._t.join()
        self.close()

    def execute(self, dictionary):
        self._sendObj(dictionary)

    def getCandles(self, symbol):
        self.execute(dict(command='getCandles', symbol=symbol, streamSessionId=self._ssId))

    def subscribePrice(self, symbol):
        print("subscribePrice")
        self.execute(dict(command='getTickPrices', symbol=symbol, level=0, streamSessionId=self._ssId))

    def subscribePrices(self, symbols):
        for symbolX in symbols:
            self.subscribePrice(symbolX)

    def subscribeTrades(self):
        self.execute(dict(command='getTrades', streamSessionId=self._ssId))

    def subscribeBalance(self):
        self.execute(dict(command='getBalance', streamSessionId=self._ssId))

    def subscribeTradeStatus(self):
        self.execute(dict(command='getTradeStatus', streamSessionId=self._ssId))

    def subscribeProfits(self):
        self.execute(dict(command='getProfits', streamSessionId=self._ssId))

    def subscribeNews(self):
        print("subscribe News")
        self.execute(dict(command='getNews', streamSessionId=self._ssId))

    def unsubscribePrice(self, symbol):
        self.execute(dict(command='stopTickPrices', symbol=symbol, streamSessionId=self._ssId))

    def unsubscribePrices(self, symbols):
        for symbolX in symbols:
            self.unsubscribePrice(symbolX)

    def unsubscribeTrades(self):
        self.execute(dict(command='stopTrades', streamSessionId=self._ssId))

    def unsubscribeBalance(self):
        self.execute(dict(command='stopBalance', streamSessionId=self._ssId))

    def unsubscribeTradeStatus(self):
        self.execute(dict(command='stopTradeStatus', streamSessionId=self._ssId))

    def unsubscribeProfits(self):
        self.execute(dict(command='stopProfits', streamSessionId=self._ssId))

    def unsubscribeNews(self):
        self.execute(dict(command='stopNews', streamSessionId=self._ssId))
