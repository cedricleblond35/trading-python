from Indicators.Price import Price


class RSI(Price):
    def __init__(self, symbol, timeframe,  periode= 14, duration=20,shift=0):
        Price.__init__(self, symbol, timeframe)
        self.__symbol = symbol
        self.__timeframe = timeframe
        self.__shift = shift
        self.__duration = duration
        self.__periode = periode

        self.__calculRSI_SMA()


    def __calculRSI_EMA(self):
        #https://www.macroption.com/rsi-calculation/

        #print("RSI EMA---------------------------------------------------------------------------")
        self._prepareListData(self.__duration)

        dif = []
        gain = []
        perte = []
        rs = []
        rsi = []


        somme = 0
        nb = 0
        for idx, v in enumerate(self._listData):
            print(v)
            self._close.append((v["open"]+v["close"])/10)
            if len(self._close) > 1:
                print("close actu : ", self._close[idx])
                print("close prese :", self._close[idx-1])
                d = round(self._close[idx]-self._close[idx-1], 2)
                if d >= 0:
                    gain.append(d)
                    perte.append(0)
                else:
                    perte.append(d*-1)
                    gain.append(0)

                #calcul des gains/pertes sur N periodes
                #print("duration :", self.__periode)
                if idx+1 >= self.__periode:
                    print("--*** :", gain[-self.__periode:])
                    print("periode")
                    gainMoy = sum(gain[-self.__periode:]) / self.__periode
                    perteMoy = sum(perte[-self.__periode:]) / self.__periode
                    print("gainMoy :",gainMoy)
                    print("perteM :", perteMoy)
                    rs = gainMoy/perteMoy
                    r = round((100-100/(1+ (gainMoy/perteMoy) )),1)
                    rsi.append(r)


            print("gain :", gain)
            print("perte : ", perte)
            print("rsi :", rsi)
            print("index :", idx)
            c = (v["open"] + v["close"])/10
            print("--------------------------")
            print("close : ",c)
            nb = nb + 1
            somme = somme + (v["open"] + v["close"])
            print("************************************")

#        print(f'RSI Moyenne mobile simple MM{self.__duration} :', round((somme / self.__duration / 10),1))



        pass

        def __calculRSI_SMA(self):
            self._prepareListData(self.__duration)

            dif = []
            gain = []
            perte = []
            rs = []
            rsi = []

            somme = 0
            nb = 0
            for idx, v in enumerate(self._listData):
                self._close.append((v["open"] + v["close"]) / 10)
                if len(self._close) > 1:
                    # print("close actu : ", self._close[idx])
                    # print("close prese :", self._close[idx - 1])
                    d = round(self._close[idx] - self._close[idx - 1], 2)
                    if d >= 0:
                        gain.append(d)
                        perte.append(0)
                    else:
                        perte.append(d * -1)
                        gain.append(0)

                    # calcul des gains/pertes sur N periodes
                    # print("duration :", self.__periode)
                    if idx + 1 >= self.__periode:
                        # print("--*** :", gain[-self.__periode:])
                        # print("periode")
                        gainMoy = sum(gain[-self.__periode:]) / self.__periode
                        perteMoy = sum(perte[-self.__periode:]) / self.__periode
                        # print("gainMoy :", gainMoy)
                        r = round((100 - 100 / (1 + (gainMoy / perteMoy))), 1)
                        rsi.append(r)

                # print("gain :", gain)
                # print("perte : ", perte)
                # print("rsi :", rsi)
                # print("index :", idx)
                # c = (v["open"] + v["close"]) / 10
                # print("--------------------------")
                # print("close : ", c)
                nb = nb + 1
                somme = somme + (v["open"] + v["close"])
                # print("************************************")

            #        print(f'RSI Moyenne mobile simple MM{self.__duration} :', round((somme / self.__duration / 10),1))

            pass
