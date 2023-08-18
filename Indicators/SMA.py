from Indicators.Price import Price
from Configuration.Log import Log


class MM(Price):
    def __init__(self, symbol, timeframe, duration):
        Price.__init__(self, symbol, timeframe)
        """
        constructor
        :param duration: 50
        :param indice: DE30
        :param period: H1
        """
        self.__timeframe = timeframe
        self.__duration = duration
        l = Log()
        self.logger = l.getLogger()

    #La première valeur de cette moyenne mobile lissée est calculée par analogie avec la moyenne mobile simple (SMA).
    # SUM1 = SUM(CLOSE, N)
    # SMMA1 = SUM1/N
    #
    # La deuxième moyenne mobile et les moyennes mobiles ultérieures sont calculées selon la formule suivante:
    # SMMA(i) = (SUM1 - SMMA1 + CLOSE(i)) / N
    # SUM — somme;
    # SUM1 — somme des prix de clôture de N périodes, calculée à partir de la barre précédente;
    # SMMA(i - 1) — moyenne mobile lissée de la barre précédente;
    # SMMA(i) — moyenne mobile lissée de la barre actuelle (sauf la première);
    # CLOSE(i)— prix actuel de clôture;
    # N — période — période de lissage.
    async def SMMA(self, duration, arrondi):
        try:
            name = "SMMA" + str(duration)
            nameSMA = "SMA" + str(duration)
            self._prepareListData()  # toutes les bougies
            self._prepareListSMMA(0, duration, name)  # toutes les bougies ne possédant pas EMA (HORS LES X PREMIÈRES)
            if len(self._listDataLast) > 1:
                if len(self._listData) - len(self._listDataLast) == duration:
                    # rien de rempli
                    SMMAPrecedent = 0
                    start = duration
                else:
                    # Des ema existant, on configure le EMAPrecedent et le start correctement
                    # la 1ere ligne contient le sma ou ema precedent pour le calcul
                    start = len(self._listData) - len(self._listDataLast)
                    idLastEma = start - 1
                    if self._listData[idLastEma].get(name):
                        SMMAPrecedent = self._listData[idLastEma][name]
                    else:

                        self.logger.info("nettoyage :", self._listData[idLastEma])
                        self._db[self.__timeframe].delete_one({ "_id": self._listData[idLastEma].get('_id') })
                        self._prepareListData()  # toutes les bougies
                        self._prepareListEMA(0, duration, name)
                        start = len(self._listData) - len(self._listDataLast)
                        idLastEma = start - 1
                        if self._listData[idLastEma].get(name):
                            SMMAPrecedent = self._listData[idLastEma][name]
                            self.logger.info("nettoyage reussi")
                        else:
                            self.logger.info("nettoyage echec")
                            return

                list = self._listData[start:len(self._listData) - 1]
                for i in range(0, len(list)):
                    if SMMAPrecedent > 0:
                        # SMMA(i) = (SUM1 - SMMA1 + CLOSE(i)) / N
                        smma = ((SMMAPrecedent*duration) - SMMAPrecedent + list[i]["close"])/duration
                        newvalues = {
                            "$set": {
                                name: round(smma, arrondi)
                            }}
                        myquery = {"ctm": list[i]["ctm"]}
                        self._db[self.__timeframe].update_one(myquery, newvalues)
                        SMMAPrecedent = smma
                    elif nameSMA in list[i]:
                        # c est la première moyenne, il est la SMA on cette valeur comme point de depart
                        newvalues = {
                            "$set": {
                                name: list[i][nameSMA]
                            }}
                        myquery = {"ctm": list[i]["ctm"]}
                        self._db[self.__timeframe].update_one(myquery, newvalues)
                        SMMAPrecedent = list[i][nameSMA]
                    else:
                        # c est la première moyenne, il n est pas de SMA on calcule le moyenne SMA comme point de depart
                        mm = round(self._avgClose(duration), arrondi)
                        newvalues = {
                            "$set": {
                                name: mm
                            }}
                        myquery = {"ctm": list[i]["ctm"]}
                        self._db[self.__timeframe].update_one(myquery, newvalues)
                        SMMAPrecedent = mm

                    start = start + 1

        except Exception as exc:
            self.logger.warning(exc)

    async def calculSMA(self, duration, arrondi):
        try:
            self._prepareListData(self.__duration)
            nb = 0
            name = "SMA" + str(duration)
            self._prepareListDataLast(0, 0, name)
            if (len(self._listData) - len(self._listDataLast)) == 0:
                start = 0
            else:
                start = len(self._listData) - len(self._listDataLast) - duration

            list = self._listData[start:len(self._listData) - 1]
            for v in list:
                nb = nb + 1  # numero necessaire pour debuter la moyenne  , ex : sma25 debute à partir de 26
                if duration <= nb <= len(self._listData):
                    somme = 0.00
                    list1 = list.copy()[nb - duration: nb]
                    b = 0
                    for v1 in list1:
                        b = b + 1
                        somme = round(somme + v1["close"], 2)

                    sma = round((somme / duration), arrondi)
                    # if "sma" not in list(list1)[-1]:
                    newvalues = {
                        "$set": {
                            name: sma
                        }}

                    myquery = {"ctm": v["ctm"]}
                    self._db[self.__timeframe].update_one(myquery, newvalues)
        except Exception as exc:
            self.logger.warning(exc)

    async def EMA(self, duration, arrondi):
        """
        EMA = (CLOSE (i) * P) + (EMA (i - 1) * (1 - P))
        (prix de clôture – EMA du jour précédent) × constante pondérant la moyenne mobile exponentielle en décimale + EMA du jour précédent

        CLOSE (i) – prix de clôture de la période actuelle ;
        EMA (i - 1) – valeur de la Moyenne Mobile de la période précédente ;
        P – pourcentage d'utilisation de la valeur du prix.
        α = 2 / (n + 1)
        :return:
        """
        try:
            name = "EMA" + str(duration)
            nameSMA = "SMA" + str(duration)
            α = round(2 / (duration + 1), 5)
            self._prepareListData()                         #toutes les bougies
            self._prepareListEMA(0, duration, name)         #toutes les bougies ne possédant pas EMA (HORS LES X PREMIÈRES)
            if len(self._listDataLast) > 1:
                #1 ou plusieurs bougies sont à traiter
                # configurer le start et EMAPrecedent
                if len(self._listData) - len(self._listDataLast) == duration:
                    # rien de rempli
                    EMAPrecedent = 0
                    start = duration
                else:
                    # Des ema existant, on configure le EMAPrecedent et le start correctement
                    # la 1ere ligne contient le sma ou ema precedent pour le calcul
                    start = len(self._listData) - len(self._listDataLast)
                    idLastEma = start - 1
                    if self._listData[idLastEma].get(name):
                        EMAPrecedent = self._listData[idLastEma][name]
                    else:
                        self.logger.info("nettoyage :", self._listData[idLastEma])
                        self._db[self.__timeframe].delete_one({ "_id": self._listData[idLastEma].get('_id') })
                        self._prepareListData()  # toutes les bougies
                        self._prepareListEMA(0, duration, name)
                        start = len(self._listData) - len(self._listDataLast)
                        idLastEma = start - 1
                        if self._listData[idLastEma].get(name):
                            EMAPrecedent = self._listData[idLastEma][name]
                            self.logger.info("nettoyage reussi")
                        else:
                            self.logger.info("nettoyage echec")
                            return

                list = self._listData[start:len(self._listData) - 1]
                for i in range(0, len(list)):
                    if EMAPrecedent > 0:
                        close = list[i]["close"]
                        ema = round((close * α) + (EMAPrecedent * (1 - α)), arrondi)

                        newvalues = {
                            "$set": {
                                name: round(ema, arrondi)
                            }}
                        myquery = {"ctm": list[i]["ctm"]}
                        self._db[self.__timeframe].update_one(myquery, newvalues)

                        EMAPrecedent = ema
                    elif nameSMA in list[i]:
                        newvalues = {
                            "$set": {
                                name: list[i][nameSMA]
                            }}
                        myquery = {"ctm": list[i]["ctm"]}
                        self._db[self.__timeframe].update_one(myquery, newvalues)
                        EMAPrecedent = list[i][nameSMA]
                    else:
                        mm = round(self._avgClose(duration), arrondi)
                        newvalues = {
                            "$set": {
                                name: mm
                            }}
                        myquery = {"ctm": list[i]["ctm"]}
                        self._db[self.__timeframe].update_one(myquery, newvalues)
                        EMAPrecedent = mm
        except Exception as exc:
            self.logger.warning(exc)
