from ConnectionDB import ConnectionDB


class Price:
    def __init__(self, symbol, timeframe):
        # Private
        self.__symbol = symbol
        self.__timeframe = timeframe

        self._db = None
        self._listData = []
        self._listDataLast = []
        self._open = []
        self._close = []
        self._high = []
        self._down = []

    def _valueHigh(self, limitValue=0, skipValue=0):
        self.__connectionDB()
        self._listData.clear()
        for v in self._db[self.__timeframe].find({},{"high":1}).sort("high", -1).skip(skipValue).limit(limitValue):
            return v


    def _valueLow(self, limitValue=0, skipValue=0):
        self.__connectionDB()
        self._listData.clear()
        for v in self._db[self.__timeframe].find({},{"low":1}).sort("low", -1).skip(skipValue).limit(limitValue):
            return v

    def _prepareListData(self, limitValue=0, skipValue=0):
        self.__connectionDB()
        self._listData.clear()
        for v in self._db[self.__timeframe].find().sort("ctm", -1).skip(skipValue).limit(limitValue):
            self._listData.append(v)

        self._listData.reverse()

    def _prepareListDataLast(self, limitValue=0, skipValue=0, link_id='ctm'):
        self.__connectionDB()
        self._listDataLast.clear()
        for v in self._db[self.__timeframe].find({link_id: {'$exists': False}}).sort("ctm", -1).skip(skipValue).limit(
                limitValue):
            self._listDataLast.append(v)

        self._listDataLast.reverse()

    def countListDataLast(self, limitValue=0, skipValue=0, link_id='ctm'):
        self.__connectionDB()
        self._listDataLast.clear()
        for v in self._db[self.__timeframe].find({link_id: {'$exists': False}}).sort("ctm", -1).skip(skipValue).limit(
                limitValue):
            self._listDataLast.append(v)

        self._listDataLast.reverse()

    def _prepareListEMA(self, limitValue=0, skipValue=0, link_id='ctm'):
        self.__connectionDB()
        self._listDataLast.clear()
        for v in self._db[self.__timeframe].find({link_id: {'$exists': False}}).skip(skipValue).limit(limitValue):
            self._listDataLast.append(v)

    def _prepareListSMMA(self, limitValue=0, skipValue=0, link_id='ctm'):
        self.__connectionDB()
        self._listDataLast.clear()
        for v in self._db[self.__timeframe].find({link_id: {'$exists': False}}).skip(skipValue).limit(limitValue):
            self._listDataLast.append(v)


    def _prepareListCC(self, limitValue=0, skipValue=0):
        #qelect le nombre de bougie à traiter
        self.__connectionDB()
        self._listDataLast.clear()

        v = self._db[self.__timeframe].find({'CC': {'$exists': False}})
        nb = len(list(v))
        #decalage =
        if nb < 35:
            skipValue = nb + 34

        for v in self._db[self.__timeframe].find().sort("ctm", -1).skip(skipValue).limit(limitValue):
            self._listData.append(v)

        self._listData.reverse()


    def _prepareListAW(self, limitValue=0, skipValue=0):
        #select le nombre de bougie à traiter
        self.__connectionDB()
        self._listDataLast.clear()

        v = self._db[self.__timeframe].find({'AW': {'$exists': False}})
        nb = len(list(v))
        if nb < 35:
            skipValue = nb + 34

        for v in self._db[self.__timeframe].find().sort("ctm", -1).skip(skipValue).limit(limitValue):
            self._listData.append(v)

        self._listData.reverse()

    def _sum(self, limit, skip=0, sort=1):
        self.__connectionDB()
        print("===========> _sum:  limit=", limit, "  skip:", skip)
        for v in self._db[self.__timeframe].aggregate([{"$sort":{"ctm":sort}},{ "$skip":skip},{ "$limit":limit},{'$group': {'_id': None, 'sum_close': {'$sum': '$close'}}}]):
            print("boucle:", v)
            return v['sum_close']

    def _avgClose(self, limit, skip=0, sort=1):
        self.__connectionDB()
        for v in self._db[self.__timeframe].aggregate([{ "$sort" : { "ctm" : sort}},{ "$skip":skip},{ "$limit":limit},{'$group': {"_id": "$Branch", 'avg_val': {'$avg': '$close'}}}]):
            return v['avg_val']

    def _numberDocuments(self, skip=0, sort=1):
        self.__connectionDB()
        for v in self._db[self.__timeframe].aggregate([{"$sort": {"ctm": sort}}, {"$skip": skip}, {'$group': {'_id': None, 'sum_val': {'$sum': 1}}}]):
            return v['sum_val']

    def __connectionDB(self):
        self._db = ConnectionDB().getDB(self.__symbol)
