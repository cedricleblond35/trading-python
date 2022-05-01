from ConnectionDB import ConnectionDB


class Price:
    def __init__(self, symbol, timeframe):
        #Private
        self.__symbol = symbol
        self.__timeframe = timeframe

        self._db = None
        self._listData  = []
        self._listDataLast  = []
        self._open  = []
        self._close = []
        self._high  = []
        self._down  = []


    def _prepareListData(self, limitValue=0, skipValue =0):
        self.__connectionDB()
        self._listData.clear()
        for v in self._db[self.__timeframe].find().sort("ctm", -1).skip(skipValue).limit(limitValue):
            self._listData.append(v)

        self._listData.reverse()

    def _prepareListDataLast(self, limitValue=0, skipValue=0, link_id='ctm'):
        self.__connectionDB()
        self._listDataLast.clear()
        for v in self._db[self.__timeframe].find({link_id: {'$exists': False}}).sort("ctm", -1).skip(skipValue).limit(limitValue):
            self._listDataLast.append(v)

        self._listDataLast.reverse()

    def countListDataLast(self, limitValue=0, skipValue=0, link_id='ctm'):
        self.__connectionDB()
        self._listDataLast.clear()
        for v in self._db[self.__timeframe].find({link_id: {'$exists': False}}).sort("ctm", -1).skip(skipValue).limit(limitValue):
            self._listDataLast.append(v)

        self._listDataLast.reverse()


    def __connectionDB(self):
        self._db = ConnectionDB().getDB(self.__symbol)