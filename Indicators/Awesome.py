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

    async def calculLastCandle(self, skipValue=0):
        self._prepareListData(self.__MMS2, skipValue)
        await self.__calcul("last")

    async def calculAllCandles(self):
        self._prepareListData(0, 1)
        print("calculAllCandles")
        await self.__calcul("all")

    async def __calcul(self, typeCalcul):
        print("calcul Awesome :", typeCalcul)
        if typeCalcul is "last":
            if "Awesome" not in list(self._listData)[-1]:
                pointMedian = 0
                for v in self._listData:
                    pointMedian = pointMedian + v["pointMedian"]
                MMS2 = round((pointMedian / self.__MMS2), 2)
                # print(f'Moyenne mobile simple MM{self.__MMS2} :', MMS2)

                pointMedian = 0
                a = np.array(self._listData)
                new_listData = np.delete(a, range(0, self.__MMS2 - self.__MMS1))
                for v in new_listData:
                    pointMedian = pointMedian + v["pointMedian"]
                MMS1 = round((pointMedian / self.__MMS1), 2)
                # print(f'Moyenne mobile simple MM{self.__MMS1} :', MMS1)
                ao = round(MMS1 - MMS2, 1)

                # mise à jour du document
                newvalues = {
                    "$set": {
                        "Awesome": ao
                    }}
                myquery = {"ctm": list(self._listData)[-1]["ctm"]}

                self._db[self.__timeframe].update_one(myquery, newvalues)
                return ao
            else:
                return list(self._listData)[-1]["Awesome"]
        elif typeCalcul == "all":
            for i in range(self.__MMS2, len(self._listData)):
                list1 = self._listData.copy()[i - self.__MMS2 + 1: i + 1]
                if "Awesome" not in list(list1)[-1]:
                    pointMedian = 0
                    for v in list1:
                        pointMedian = pointMedian + v["pointMedian"]
                    MMS2 = round((pointMedian / self.__MMS2), 3)
                    # print(f'Moyenne mobile simple MM{self.__MMS2} :', MMS2)

                    pointMedian = 0
                    a = np.array(list1)
                    new_listData = np.delete(a, range(0, self.__MMS2 - self.__MMS1))
                    for v in new_listData:
                        pointMedian = pointMedian + v["pointMedian"]
                    MMS1 = round((pointMedian / self.__MMS1), 3)
                    # print(f'Moyenne mobile simple MM{self.__MMS1} :', MMS1)
                    ao = round(MMS1 - MMS2, 3)

                    print("Awesome ", self.__timeframe," :", list(list1)[-1]["ctmString"])
                    # mise à jour du document
                    newvalues = {
                        "$set": {
                            "Awesome": ao
                        }}
                    myquery = {"ctm": list(list1)[-1]["ctm"]}

                    self._db[self.__timeframe].update_one(myquery, newvalues)
