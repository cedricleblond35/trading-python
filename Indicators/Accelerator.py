from Indicators.Price import Price
import pandas as pd
import numpy as np
pd.options.mode.chained_assignment = None  # default='warn'


class Accelerator(Price):
    def __init__(self, symbol, timeframe, period=5, shift=0):
        Price.__init__(self, symbol, timeframe)
        self.__symbol = symbol
        self.__timeframe = timeframe
        self.__shift = shift
        self.__period = period

    async def calcul(self):
        for i in range(self.__period, len(self._listData)):
            list1 = self._listData.copy()[i - self.__period + 1: i + 1]
            #if "CC" not in list(list1)[-1]:



