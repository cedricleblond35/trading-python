from Indicators.Price import Price
import math
import pandas as pd
import numpy as np
pd.options.mode.chained_assignment = None  # default='warn'


class Donchian(Price):
    def __init__(self, symbol, timeframe,duration=20,shift=0):
        '''

        :param symbol: Symbole à calculer (DE30, SILVER ...)
        :param timeframe: M05 M15 H01 ......
        :param periode:
        :param duration: Nombre de bougies à prendre
        :param shift: décalage ds le passer en nombre de bougie, ex shift=1 => on prend la n-1 bougie
        '''
        Price.__init__(self, symbol, timeframe)
        self.__symbol = symbol
        self.__timeframe = timeframe
        self.__shift = shift
        self.__duration = duration
        self._prepareListData(self.__duration)

    # SuperTrend
    def calcul(self):
        df = pd.DataFrame.from_dict(self._listData)
        max = df['high'].max()
        mini = df['low'].min()
        median = (max+mini)/2
        return mini, max, median