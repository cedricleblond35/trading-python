from Indicators.Price import Price


class Pivot(Price):
    '''
    Pivot point (PP) = (High + Low + Close) / 3
    First resistance (R1) = (2 x PP) – Low
    First support (S1) = (2 x PP) – High
    Second resistance (R2) = PP + (High – Low)
    Second support (S2) = PP – (High – Low)
    Third resistance (R3) = High + 2(PP – Low)
    Third support (S3) = Low – 2(High – PP)
    '''

    def __init__(self, symbol, timeframe, period=1, shift=0):
        Price.__init__(self, symbol, timeframe)
        self.__symbol = symbol
        self.__timeframe = timeframe
        self.__shift = shift
        self.__period = period

        self._prepareListData(1, 1)

    async def calculPivotClassic(self):
        i = 0
        H = 0
        L = 0
        C = 0

        for v in self._db[self.__timeframe].find().sort("ctm", 1):
            if i > 0:
                PP = (H + L + C) / 3
                S1 = (PP * 2) - H
                S2 = PP - (H - L)
                S3 = PP - (H - L) * 2

                R1 = (PP * 2) - L
                R2 = PP + (H - L)
                R3 = PP + (H - L) * 2
                newvalues = {
                    "$set": {
                        "PClass_PP": round(PP, 1),
                        "PClass_r1": round(R1, 1),
                        "PClass_r2": round(R2, 1),
                        "PClass_r3": round(R3, 1),
                        "PClass_s1": round(S1, 1),
                        "PClass_s2": round(S2, 1),
                        "PClass_s3": round(S3, 1)
                    }}
                myquery = {"ctm": v["ctm"]}

                self._db[self.__timeframe].update_one(myquery, newvalues)
                H = v['high']
                L = v['low']
                C = v['close']
            else:
                H = v['high']
                L = v['low']
                C = v['close']
            i = i + 1

        return round(PP, 1), round(R1, 1), round(R2, 1), round(R3, 1), round(S1, 1), round(S2, 1), round(S3, 1)

    async def fibonacci(self):
        try:
            i = 0
            H = 0
            L = 0
            C = 0
            for v in self._db[self.__timeframe].find().sort("ctm", 1):
                if i > 0:
                    PP = (H + L + C) / 3
                    S1 = PP - 0.382 * (H - L)
                    S2 = PP - 0.618 * (H - L)
                    S3 = PP - 1.000 * (H - L)
                    R1 = PP + 0.382 * (H - L)
                    R2 = PP + 0.618 * (H - L)
                    R3 = PP + 1.000 * (H - L)

                    newvalues = {
                        "$set": {
                            "PFibo_PP": round(PP, 1),
                            "PFibo_r1": round(R1, 1),
                            "PFibo_r2": round(R2, 1),
                            "PFibo_r3": round(R3, 1),
                            "PFibo_s1": round(S1, 1),
                            "PFibo_s2": round(S2, 1),
                            "PFibo_s3": round(S3, 1)
                        }}
                    myquery = {"ctm": v["ctm"]}

                    self._db[self.__timeframe].update_one(myquery, newvalues)
                    H = v['high']
                    L = v['low']
                    C = v['close']
                else:
                    H = v['high']
                    L = v['low']
                    C = v['close']
                i = i + 1
        except Exception as exc:
            print("le programme a déclenché une erreur pour le Pivot Fibo")
            print("exception de type ", exc.__class__)
            print("message", exc)
            pass

        # print("calcul pivot Fibo  fini ")
        return round(PP, 1), round(R1, 1), round(R2, 1), round(R3, 1), round(S1, 1), round(S2, 1), round(S3, 1)

    async def woodie(self):
        try:
            i = 0
            H = 0
            L = 0
            C = 0
            for v in self._db[self.__timeframe].find().sort("ctm", 1):
                if i > 0:
                    PP = (H + L + 2 * C) / 4
                    R1 = (2 * PP) - L
                    R2 = PP + (H - L)
                    S1 = (2 * PP) - H
                    S2 = PP - (H - L)

                    newvalues = {
                        "$set": {
                            "PWoodie_PP": round(PP, 1),
                            "PWoodie_r1": round(R1, 1),
                            "PWoodie_r2": round(R2, 1),
                            "PWoodie_s1": round(S1, 1),
                            "PWoodie_s2": round(S2, 1)
                        }}
                    myquery = {"ctm": v["ctm"]}
                    self._db[self.__timeframe].update_one(myquery, newvalues)
                    H = v['high']
                    L = v['low']
                    C = v['close']
                else:
                    H = v['high']
                    L = v['low']
                    C = v['close']
                i = i + 1

        except Exception as exc:
            print("le programme a déclenché une erreur pour le Pivot calculPivotWoodie")
            print("exception de type ", exc.__class__)
            print("message", exc)
            pass
        return round(PP, 1), round(R1, 1), round(R2, 1), round(S1, 1), round(S2, 1)

    async def camarilla(self):
        # Resistance 4 or R4 = (H - L)X1.1 / 2 + C
        # Resistance 3 or R3 = (H - L)X1.1 / 4 + C
        # Resistance 2 or R2 = (H - L)X1.1 / 6 + C
        # Resistance 1 or R1 = (H - L)X1.1 / 12 + C
        # PIVOT POINT = (H + L + C) / 3
        # Support 1 or S1 = C - (H - L)X1.1 / 12
        # Support 2 or S2 = C - (H - L)X1.1 / 6
        # Support 3 or S3 = C - (H - L)X1.1 / 4
        # Support 4 or S4 = C - (H - L)X1.1 / 2
        # Here O, H, L, and C represent the open, high, low and close value of the previous trading day.

        i = 0
        H = 0
        L = 0
        C = 0

        for v in self._db[self.__timeframe].find().sort("ctm", 1):
            if i > 0:
                PP = (H + L + C) / 3
                S1 = C - (H - L) * 1.1 / 12
                S2 = C - (H - L) * 1.1 / 6
                S3 = C - (H - L) * 1.1 / 4
                S4 = C - (H - L) * 1.1 / 2

                R4 = (H - L) * 1.1 / 2 + C
                R3 = (H - L) * 1.1 / 4 + C
                R2 = (H - L) * 1.1 / 6 + C
                R1 = (H - L) * 1.1 / 12 + C

                newvalues = {
                    "$set": {
                        "PCamarilla_PP": round(PP, 1),
                        "PCamarilla_r1": round(R1, 1),
                        "PCamarilla_r2": round(R2, 1),
                        "PCamarilla_r3": round(R3, 1),
                        "PCamarilla_r4": round(R4, 1),
                        "PCamarilla_s1": round(S1, 1),
                        "PCamarilla_s2": round(S2, 1),
                        "PCamarilla_s3": round(S3, 1),
                        "PCamarilla_s4": round(S4, 1)
                    }}
                myquery = {"ctm": v["ctm"]}

                self._db[self.__timeframe].update_one(myquery, newvalues)
                H = v['high']
                L = v['low']
                C = v['close']
            else:
                H = v['high']
                L = v['low']
                C = v['close']
            i = i + 1

        return round(PP, 1), round(R1, 1), round(R2, 1), round(R3, 1), round(R4, 1), round(S1, 1), round(S2, 1), round(
            S3, 1), round(S4, 1)

    async def demark(self):
        '''
        The DeMark method begins with a different base and differs from the other pivot point calculation styles. Here the pivot points depend on the relation between the close and the open.
        If Close < Open, then X = High(previous day) + [2 x Low(previous day)] + Close(previous day)
        If Close > Open, then X = [2 x High(previous day)] + Low(previous day) + Close(previous day)
        If Close = Open, then X = High(previous day) + Low(previous day) + [2 x Close(previous day)]
        Pivot Point (P) = X/4
        Support 1 (S1) = X/2 – High(previous day)
        Resistance 1 (R1) = X/2 – Low(previous day)
        :return:
        '''
        i = 0
        H = 0
        L = 0
        C = 0
        O = 0

        for v in self._db[self.__timeframe].find().sort("ctm", 1):
            if i > 0:
                if C < O:
                    x = H + (2 * L) + C
                elif C > O:
                    x = (2 * H) + L + C
                else:
                    x = H + L + 2 * C

                S = round((x / 2) - H, 1)
                R = round((x / 2) - L, 1)

                newvalues = {
                    "$set": {
                        "demark_s1": S,
                        "demark_r1": R
                    }}
                myquery = {"ctm": v["ctm"]}
                self._db[self.__timeframe].update_one(myquery, newvalues)
                H = v['high']
                L = v['low']
                C = v['close']
                pass


            else:
                H = v['high']
                L = v['low']
                C = v['close']
                O = v['open']
            i = i + 1

        return R, S
