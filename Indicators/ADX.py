from Indicators.Price import Price
import pandas as pd
import numpy as np


class ADX(Price):
    def __init__(self, symbol, timeframe, periode=14):
        Price.__init__(self, symbol, timeframe)
        self.__symbol = symbol
        self.__timeframe = timeframe
        self.__periode = periode

        self.__adx = self.__calculATR()

    def getATR(self):
        return self.__adx

    def __calculATR(self):
        # https://www.macroption.com/rsi-calculation/


        #print("RSI EMA---------------------------------------------------------------------------")
        self._prepareListData(self.__duration)
        df = pd.DataFrame.from_dict(self._listData)
        atr = 'ATR_' + str(self.__periode)

        # Compute true range only if it is not computed and stored earlier in the df
        if not atr in df.columns:
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

            return round(df['ATR'][len(df) - 1], 2)
