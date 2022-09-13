from Indicators.Price import Price
import pandas as pd
import numpy as np
pd.options.mode.chained_assignment = None  # default='warn'


class Awesome(Price):
    '''

    '''

    def __init__(self, symbol, timeframe, MMS1=5, MMS2=34, shift=0):
        Price.__init__(self, symbol, timeframe)
        self.__symbol = symbol
        self.__timeframe = timeframe
        self.__shift = shift
        self.__MMS1 = MMS1
        self.__MMS2 = MMS2

    async def calculLastCandle(self, howMuch=1,  skipValue=0):
        self._prepareListData(self.__MMS2+howMuch, skipValue)
        await self.__calcul()

    async def calculAllCandles(self):
        self._prepareListData(0, 0)
        await self.__calcul()

    async def __calcul(self):
        #print("calcul AW ", self.__timeframe)
        # print("nombre 1: ",  len(self._listData))
        #
        # self._prepareListEMA(0, self.__MMS2 , "AW")  # toutes les bougies ne possédant pas EMA (HORS LES X PREMIÈRES)
        #
        #
        #
        # print("nombre 2: ",  len(self._listData))
        for i in range(self.__MMS2, len(self._listData)):
            list1 = self._listData.copy()[i - self.__MMS2 + 1: i + 1]
            if "AW" not in list(list1)[-1]:
                pointMedian = 0
                for v in list1:
                    pointMedian = pointMedian + v["pointMedian"]
                MMS2 = round((pointMedian / self.__MMS2), 3)
                pointMedian = 0
                a = np.array(list1)
                new_listData = np.delete(a, range(0, self.__MMS2 - self.__MMS1))
                for v in new_listData:
                    pointMedian = pointMedian + v["pointMedian"]
                MMS1 = round((pointMedian / self.__MMS1), 3)
                ao = round(MMS1 - MMS2, 3)
                # mise à jour du document
                newvalues = {
                    "$set": {
                        "AW": ao
                    }}
                myquery = {"ctm": list(list1)[-1]["ctm"]}
                self._db[self.__timeframe].update_one(myquery, newvalues)
