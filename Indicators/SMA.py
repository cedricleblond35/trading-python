from Indicators.Price import Price
import os
import sys
import logging

# logger properties
logger = logging.getLogger("jsonSocket")
FORMAT = '[%(asctime)-15s][%(funcName)s:%(lineno)d] %(message)s'
logging.basicConfig(format=FORMAT)

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

    def calculSMA(self, duration):
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

                    sma = round((somme / duration), 2)
                    # if "sma" not in list(list1)[-1]:
                    newvalues = {
                        "$set": {
                            name: sma
                        }}

                    myquery = {"ctm": v["ctm"]}
                    self._db[self.__timeframe].update_one(myquery, newvalues)
        except Exception as exc:
            print("le programe a déclenché une erreur")
            print("exception de mtype ", exc.__class__)
            print("message", exc)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

        # return sma

    async def EMA(self, duration):
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
            print("calcul ", name)
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
                        logger.info("nettoyage :", self._listData[idLastEma])
                        self._db[self.__timeframe].delete_one({ "_id": self._listData[idLastEma].get('_id') })
                        self._prepareListData()  # toutes les bougies
                        self._prepareListEMA(0, duration, name)
                        start = len(self._listData) - len(self._listDataLast)
                        idLastEma = start - 1
                        if self._listData[idLastEma].get(name):
                            EMAPrecedent = self._listData[idLastEma][name]
                            logger.info("nettoyage reussi")
                        else:
                            logger.info("nettoyage echec")
                            return


                list = self._listData[start:len(self._listData) - 1]
                print("nombre :", len(list))
                for i in range(0, len(list)):
                    if EMAPrecedent > 0:
                        close = list[i]["close"]
                        ema = round((close * α) + (EMAPrecedent * (1 - α)), 2)

                        newvalues = {
                            "$set": {
                                name: round(ema, 2)
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
                        mm = round(self._avgClose(duration), 2)
                        newvalues = {
                            "$set": {
                                name: mm
                            }}
                        myquery = {"ctm": list[i]["ctm"]}
                        self._db[self.__timeframe].update_one(myquery, newvalues)
                        EMAPrecedent = mm
            print("calcul ", name)
        except Exception as exc:
            print("le programe a déclenché une erreur SMA.py")
            print("exception de mtype ", exc.__class__)
            print("message", exc)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
