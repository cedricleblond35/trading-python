from Indicators.Price import Price

class Heikin(Price):
    def __init__(self, symbol, timeframe, period=1, shift=0):
        Price.__init__(self, symbol, timeframe)
        self.__symbol = symbol
        self.__timeframe = timeframe
        self.__shift = shift
        self.__period = period

        self._prepareListData(1, 1)

    async def calculLastCandle(self, skipValue=0):
        self._prepareListData(10, skipValue)
        await self.__calcul("last")

    def calcul(self, typeCalcul):
        print("calcul Heikin :", typeCalcul)
        # if typeCalcul is "last":
        #     if "HA_Open" not in list(self._listData)[-1]:
        #         pass
        # elif typeCalcul == "all":
        #     pass

        i = 0
        OpenPrevious = 0
        ClosePrevious = 0

        for v in self._db[self.__timeframe].find().sort("ctm", 1):
            print(v)
            if i > 0 :
                HA_Open = (OpenPrevious + ClosePrevious) / 2
                HA_Close = (v['open'] + v['high'] + v['low'] + v['close']) / 4
                HA_Hight = v['high']
                HA_Low = v['low']
                newvalues = {
                    "$set": {
                        "HA_Open": round(HA_Open, 2),
                        "HA_Close": round(HA_Close, 2),
                        "HA_Hight": round(HA_Hight, 2),
                        "HA_Low": round(HA_Low, 2)
                    }}
                myquery = {"ctm": v["ctm"]}
                OpenPrevious = v['open']
                ClosePrevious = v['close']
                self._db[self.__timeframe].update_one(myquery, newvalues)
            else:
                OpenPrevious = v['HA_Open']
                ClosePrevious = v['HA_Close']
            i = i+1

        print("---------------- Heikin ------------------------")
        pass
        #return mini, max, median