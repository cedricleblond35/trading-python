from Indicators.Price import Price
from Indicators.SMA import MM

class CCI(Price):
    def __init__(self, symbol, timeframe,  periode= 14):
        Price.__init__(self, symbol, timeframe)
        self.__symbol = symbol
        self.__timeframe = timeframe
        self.__periode = periode
        self._prepareListData(self.__periode)



    def calculCCI(self):
        #https://www.macroption.com/rsi-calculation/

        moyMobil = MM(self.__symbol, "M01", self.__periode)
        sma = moyMobil.calculSMA()
        valeur = []

        print("-------- CCI -------------------------------------------------------------------")
        print("sma :", sma)
        for idx, v in enumerate(self._listData):
            print("v :",v)
            c = round( 1 / 3 * (v["high"] + v["low"] + v["close"]),3)
            print("calcul :",c)
            print(type(c))
            valeur.append(c)
        print("valeur :", valeur)
        vMoy = sum(valeur[-self.__periode:]) / self.__periode

        print('sma :', sma)
        print('vMoy :', vMoy)
        DM = 1/self.__periode * abs( vMoy- sma)

        print('DM :', DM)
        print('DM :',DM )
        cci = (vMoy-sma)/DM*0.015
        print("cci :", cci)
        pass
