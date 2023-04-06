from Indicators.Price import Price
import pandas as pd
import numpy as np
pd.options.mode.chained_assignment = None  # default='warn'


class Supertrend(Price):
    def __init__(self, symbol, timeframe,  periode= 10, multplicateur = 3, arrondi = 2, duration=100,shift=0):
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
        self.__periode = periode
        self.__multplicateur = multplicateur
        self.__arrondi = arrondi

        self.__st = self.__ST()

    # SuperTrend
    def __ST(self):

        # df is the dataframe, n is the period, f is the factor; f=3, n=7 are commonly used.
        f = self.__multplicateur
        n = self.__periode
        self._prepareListData(self.__duration)
        df = pd.DataFrame.from_dict(self._listData)

        # Calculation of ATR
        df['H-L'] = abs(df['high'] - df['low'])
        df['H-PC'] = abs(df['high'] - df['close'].shift(1))
        df['L-PC'] = abs(df['low'] - df['close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df.drop(['H-L', 'H-PC', 'L-PC'], inplace=True, axis=1)
        df['ATR'] = np.nan
        df.loc[self.__periode - 1, 'ATR'] = df['TR'][
                                            :self.__periode - 1].mean()  # .ix is deprecated from pandas version- 0.19
        for i in range(self.__periode, len(df)):
            df['ATR'][i] = (df['ATR'][i - 1] * (self.__periode - 1) + df['TR'][i]) / self.__periode


        # Calculation of SuperTrend
        df['Upper Basic'] = (df['high'] + df['low']) / 2 + (f * df['ATR'])
        df['lower Basic'] = (df['high'] + df['low']) / 2 - (f * df['ATR'])
        df['Upper Band'] = df['Upper Basic']
        df['lower Band'] = df['lower Basic']


        for i in range(n, len(df)):
            if df['close'][i - 1] <= df['Upper Band'][i - 1]:
                df['Upper Band'][i] = min(df['Upper Basic'][i], df['Upper Band'][i - 1])
            else:
                df['Upper Band'][i] = df['Upper Basic'][i]
        for i in range(n, len(df)):
            if df['close'][i - 1] >= df['lower Band'][i - 1]:
                df['lower Band'][i] = max(df['lower Basic'][i], df['lower Band'][i - 1])
            else:
                df['lower Band'][i] = df['lower Basic'][i]

        df['SuperTrend'] = np.nan



        for i in df['SuperTrend']:
            if df['close'][n - 1] <= df['Upper Band'][n - 1]:
                df['SuperTrend'][n - 1] = df['Upper Band'][n - 1]
            elif df['close'][n - 1] > df['Upper Band'][i]:
                df['SuperTrend'][n - 1] = df['lower Band'][n - 1]

        for i in df['SuperTrend']:
            if df['close'][n - 1] <= df['Upper Band'][n - 1]:
                df['SuperTrend'][n - 1] = df['Upper Band'][n - 1]
            elif df['close'][n - 1] > df['Upper Band'][i]:
                df['SuperTrend'][n - 1] = df['lower Band'][n - 1]

        for i in range(n, len(df)):
            if df['SuperTrend'][i - 1] == df['Upper Band'][i - 1] and df['close'][i] <= df['Upper Band'][i]:
                df['SuperTrend'][i] = df['Upper Band'][i]
            elif df['SuperTrend'][i - 1] == df['Upper Band'][i - 1] and df['close'][i] >= df['Upper Band'][i]:
                df['SuperTrend'][i] = df['lower Band'][i]
            elif df['SuperTrend'][i - 1] == df['lower Band'][i - 1] and df['close'][i] >= df['lower Band'][i]:
                df['SuperTrend'][i] = df['lower Band'][i]
            elif df['SuperTrend'][i - 1] == df['lower Band'][i - 1] and df['close'][i] <= df['lower Band'][i]:
                df['SuperTrend'][i] = df['Upper Band'][i]
        # print("SuperTrend:", df)
        # print("SuperTrend 1:", df['SuperTrend'][len(df)-1])
        # print("SuperTrend 2:", df['SuperTrend'][len(df) - 2])
        # print("SuperTrend arrondi:", round(df['SuperTrend'][len(df)-1], 2))
        return round(df['SuperTrend'][len(df)-1], self.__arrondi), round(df['SuperTrend'][len(df)-2], self.__arrondi), round(df['SuperTrend'][len(df)-3], self.__arrondi)

    def getST(self):
        return self.__st
